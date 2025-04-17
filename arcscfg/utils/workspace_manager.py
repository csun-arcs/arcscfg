import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import yaml

from arcscfg.utils.logger import Logger
from arcscfg.utils.shell import Shell
from arcscfg.utils.user_prompter import UserPrompter
from arcscfg.utils.script_executor import ScriptExecutor


class WorkspaceManager:
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        workspace_config: Optional[str] = None,
        underlay_path: Optional[str] = None,
        build_script_path: Optional[str] = None,
        symlink_install: Optional[bool] = False,
        assume: Optional[str] = None,
        logger: Optional[Logger] = None,
        dependency_file_names: Optional[List[str]] = None,
        recursive_search: bool = False,
        max_retries: int = 2,
        user_prompter: Optional[UserPrompter] = None,
    ):
        self.logger = logger or Logger()
        self.assume = assume
        self.user_prompter = user_prompter or UserPrompter(assume=assume)

        self.workspace_path = (
            Path(workspace_path).expanduser().resolve() if workspace_path else None
        )
        self.workspace_config = workspace_config
        self.underlay_path = (
            Path(underlay_path).expanduser().resolve() if underlay_path else None
        )
        self.build_script_path = build_script_path
        self.symlink_install = symlink_install

        # Initialize dependency file names
        self.dependency_file_names = (
            dependency_file_names
            if dependency_file_names
            else ["dependencies.repos", "dependencies.rosinstall"]
        )
        self.recursive_search = recursive_search
        self.max_retries = max_retries

    def _discover_dependency_files(self) -> List[Path]:
        """Discover all dependency files within each cloned repository in the workspace."""
        if not self.workspace_path:
            self.logger.error("Workspace path is not set.")
            raise ValueError("Workspace path is not set.")

        src_dir = self.workspace_path / "src"
        if not src_dir.exists():
            self.logger.error(
                f"'src' directory does not exist in workspace: {self.workspace_path}"
            )
            raise ValueError(
                f"'src' directory does not exist in workspace: {self.workspace_path}"
            )

        dependency_files = []
        # Iterate through each package in src
        for package in src_dir.iterdir():
            if package.is_dir():
                for file_name in self.dependency_file_names:
                    if self.recursive_search:
                        found = list(package.rglob(file_name))
                    else:
                        found = (
                            [package / file_name]
                            if (package / file_name).is_file()
                            else []
                        )
                        found = [p for p in found if p.is_file()]

                    dependency_files.extend(found)
                    self.logger.debug(
                        f"Found {len(found)} '{file_name}' files in '{package}'."
                    )

        # Remove duplicates
        dependency_files = list(set(dependency_files))
        self.logger.info(f"Total dependency files discovered: {len(dependency_files)}")
        for dep_file in dependency_files:
            self.logger.debug(f"Discovered dependency file: {dep_file}")

        return dependency_files

    def setup_workspace(self):
        """Set up the workspace by cloning repositories according to the workspace_config and dependency files."""
        try:
            if not self.workspace_path:
                raise ValueError("Workspace path is not set.")

            # Validate workspace path
            workspace = self._validate_workspace_path(
                self.workspace_path, allow_create=True
            )

            # Load and validate workspace configuration
            if not self.workspace_config:
                raise ValueError("Workspace configuration is not set.")
            with self.workspace_config.open("r") as f:
                try:
                    config = yaml.safe_load(f)
                    self.logger.debug(
                        f"Loaded workspace config from {self.workspace_config}"
                    )
                except yaml.YAMLError as e:
                    self.logger.error(
                        f"YAML parsing error in {self.workspace_config}: {e}"
                    )
                    raise

            self._validate_workspace_config(config)

            # Validate/create src directory
            self._validate_src_directory(workspace, allow_create=True)

            self.logger.info(
                f"Setting up workspace at '{workspace}' using config '{self.workspace_config}'"
            )

            # Clone main workspace repositories
            self.clone_repositories(workspace, self.workspace_config)

            # Multi-pass discovery additional dependency files
            previous_dependency_files = []
            dependency_files = self._discover_dependency_files()
            while dependency_files != previous_dependency_files:
                # Clone repositories from each dependency file
                for dep_file in dependency_files:
                    self.clone_repositories(workspace, dep_file)
                previous_dependency_files = dependency_files
                dependency_files = self._discover_dependency_files()

            self.logger.info(f"Workspace setup at '{workspace}' using config '{self.workspace_config}' completed successfully.")

        except Exception as e:
            self.logger.error(f"Error setting up workspace: {e}")
            sys.exit(1)

    def update_workspace(self):
        """Update workspace by pulling repositories therein."""
        try:
            if not self.workspace_path:
                raise ValueError("Workspace path is not set.")

            # Validate workspace path
            workspace = self._validate_workspace_path(self.workspace_path)

            # Validate src directory
            self._validate_src_directory(workspace)

            self.logger.info(f"Updating workspace at '{workspace}'")

            # Pull repositories
            self.pull_repositories(workspace)

            # Multi-pass discovery additional dependency files
            previous_dependency_files = []
            dependency_files = self._discover_dependency_files()
            while dependency_files != previous_dependency_files:
                # Clone repositories from each dependency file
                for dep_file in dependency_files:
                    self.clone_repositories(workspace, dep_file)
                previous_dependency_files = dependency_files
                dependency_files = self._discover_dependency_files()

            self.logger.info(f"Workspace setup at '{workspace}' using config '{self.workspace_config}' completed successfully.")

        except Exception as e:
            self.logger.error(f"Error updating workspace: {e}")
            sys.exit(1)

    def build_workspace(self):
        """Build the workspace."""
        try:
            # Validate workspace path
            workspace = self._validate_workspace_path(self.workspace_path)
            self.logger.debug(f"Validated workspace path for build: {workspace}")

            # Validate src directory
            self._validate_src_directory(workspace)

            # TODO: Add underlay validation
            underlay = self.underlay_path

            # TODO: Add build script validation
            build_script = self.build_script_path

            symlink_install_arg = "--symlink-install" if self.symlink_install else ""

            # Proceed with build
            self.logger.info(f"Building workspace at '{workspace}' using build script {build_script}...")
            executor = ScriptExecutor(build_script, self.logger, self.user_prompter,
                                      context={"ARCSCFG_UNDERLAY": str(underlay),
                                               "ARCSCFG_WORKSPACE": str(workspace),
                                               "ARCSCFG_SYMLINK_INSTALL_ARG": str(symlink_install_arg)})
            try:
                executor.execute()
            except Exception as e:
                self.logger.error(f"Workspace build at '{workspace}' failed: {e}")
                sys.exit(1)
            self.logger.info(f"Workspace build of '{workspace}' completed successfully.")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error building workspace: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            sys.exit(1)

    def _validate_workspace_path(
        self, workspace_path: Path, allow_create: bool = False
    ) -> Path:
        """Validate a ROS 2 workspace path."""
        if workspace_path.exists():
            if not os.access(workspace_path, os.W_OK):
                raise PermissionError(f"No write permission for {workspace_path}")
        elif allow_create:
            # Attempt to create the workspace directory
            try:
                workspace_path.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created workspace directory: {workspace_path}")
                self._validate_src_directory(workspace_path, allow_create=True)
            except Exception as e:
                raise PermissionError(
                    f"Cannot create workspace directory: {workspace_path}"
                ) from e
        else:
            raise ValueError("Workspace path does not exist.")
        self.logger.debug(f"Workspace path validated: {workspace_path}")
        return workspace_path

    def _validate_workspace_config(self, config: dict) -> dict:
        """Validate workspace configuration structure."""
        if not isinstance(config, dict):
            raise ValueError(
                "Invalid workspace configuration format; expected a dictionary."
            )
        if "repositories" not in config:
            raise ValueError("No 'repositories' specified in configuration.")
        if not isinstance(config["repositories"], dict):
            raise ValueError(
                "'repositories' should be a dictionary of repository configurations."
            )
        for repo_name, repo_cfg in config["repositories"].items():
            if not isinstance(repo_cfg, dict):
                raise ValueError(
                    "Each repository configuration should be a dictionary."
                )
            if (
                "type" not in repo_cfg
                or "url" not in repo_cfg
                or "version" not in repo_cfg
            ):
                raise ValueError(
                    "Each repository must have 'type', 'url' and 'version' fields."
                )
        self.logger.debug("Workspace configuration validated successfully.")
        return config

    def _validate_src_directory(
        self, workspace_path: Path, allow_create: bool = False
    ) -> Path:
        """Validate that the workspace has a 'src' directory."""
        src_dir = workspace_path / "src"
        if not src_dir.exists():
            if allow_create:
                src_dir.mkdir(parents=True)
                self.logger.debug(f"Created 'src' directory at {src_dir}")
            else:
                raise ValueError(f"'{src_dir}' does not exist.")
        elif not src_dir.is_dir():
            raise ValueError(f"'{src_dir}' exists but is not a directory")
        else:
            self.logger.debug(f"'src' directory validated at {src_dir}")
        return src_dir

    @staticmethod
    def infer_default_workspace_path(workspace_config: Path) -> Path:
        """
        Infer a default workspace path based on the workspace config.

        For example, if the config is 'cohort.yaml', suggest '~/cohort_ws'.
        """
        config_name = workspace_config.stem
        suggested_name = f"{config_name}_ws"
        default_workspace = Path.home() / suggested_name
        return default_workspace

    def get_workspace_setup_file(self, workspace_path: Path) -> Optional[Path]:
        """
        Determine the appropriate setup file based on the user's shell for a
        given workspace.

        Args:
            workspace_path (Path): The path to the workspace or underlay.

        Returns:
            Optional[Path]: Path to the setup file if found, else None.
        """
        # Get user's current shell
        shell = os.environ.get("SHELL", "/bin/bash").lower()

        # Map shells to their setup files
        setup_files = {"zsh": "setup.zsh", "bash": "setup.bash", "sh": "setup.sh"}

        # Extract shell name (e.g., 'bash' from '/bin/bash')
        shell_name = Path(shell).name
        # Default to bash if unknown
        setup_file_name = setup_files.get(shell_name, "setup.bash")

        self.logger.debug(
            f"Detected shell: {shell_name}, looking for '{setup_file_name}'"
        )

        # Possible setup file locations
        possible_paths = [
            # For system installs like /opt/ros/jazzy/setup.bash
            workspace_path / setup_file_name,
            # For colcon workspaces
            workspace_path / "install" / setup_file_name,
            # For catkin workspaces
            workspace_path / "devel" / setup_file_name,
        ]

        # Try each possible path
        for path in possible_paths:
            if path.exists():
                self.logger.debug(f"Found setup file: {path}")
                return path

        self.logger.warning(
            f"No setup file found for shell '{shell_name}' "
            f"in workspace '{workspace_path}'."
        )
        return None

    def get_last_underlay_from_setup(self, setup_bash_path: Path) -> Optional[Path]:
        """
        Parse the setup.bash file to extract the last underlay in the build
        chain (the second-last COLCON_CURRENT_PREFIX entry in the setup file).

        Args:
            setup_bash_path (Path): Path to the setup.bash file.

        Returns:
            Optional[Path]: The inferred underlay path if found, else None.
        """
        if not setup_bash_path.exists():
            self.logger.debug(f"Setup file does not exist: {setup_bash_path}")
            return None

        colcon_prefix_pattern = re.compile(r'^COLCON_CURRENT_PREFIX="(.+)"$')
        prefixes = []

        try:
            with setup_bash_path.open("r") as file:
                for line in file:
                    match = colcon_prefix_pattern.match(line.strip())
                    if match:
                        prefixes.append(match.group(1))

            if len(prefixes) >= 2:
                default_underlay = prefixes[-2]
                self.logger.debug(
                    f"Inferred default underlay before stripping: {default_underlay}"
                )

                # Strip '/install' or '/devel' only if present at the end
                if default_underlay.endswith(("/install", "/devel")):
                    stripped_underlay = Path(default_underlay).parent
                    default_underlay_str = str(stripped_underlay)
                    self.logger.debug(
                        f"Inferred default underlay after stripping: {default_underlay_str}"
                    )
                else:
                    # Retain the original path if no stripping is needed
                    default_underlay_str = default_underlay
                    self.logger.debug(
                        f"Inferred default underlay without stripping: {default_underlay_str}"
                    )

                return Path(default_underlay_str)
            else:
                self.logger.warning("Not enough COLCON_CURRENT_PREFIX entries found.")
                return None

        except Exception as e:
            self.logger.error(f"Error parsing setup.bash: {e}")
            return None

    def clone_repositories(self, workspace: Path, repos_file: Path):
        """Clone repos defined in the repositories config file to the ROS 2 workspace."""
        try:
            self.logger.info(f"Cloning repositories from '{repos_file}' into '{workspace}/src'...")
            Shell.run_command(
                ["vcs", "import", "--input", str(repos_file), "src"],
                cwd=str(workspace),
                verbose=True,
                max_retries=self.max_retries,
            )
            self.logger.info(
                f"Repositories cloned successfully from '{repos_file}' into '{workspace}/src'."
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to clone repositories from '{repos_file} into '{workspace}/src': {e}"
            )
            sys.exit(1)

    def pull_repositories(self, workspace: Path):
        try:
            self.logger.info(f"Pulling repositories in '{workspace}/src'...")
            Shell.run_command(
                ["vcs", "pull", "src"],
                cwd=str(workspace),
                verbose=True,
                max_retries=self.max_retries,
            )
            self.logger.info(f"Repositories pulled successfully in '{workspace}/src'.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to pull repositories in '{workspace}/src': {e}")
            sys.exit(1)

    def _find_available_workspaces(
            self,
            home_dir: Path = Path.home(),
            naming_patterns: List[str] = ["*_ws", "ros2_*"]) -> List[Path]:
        """Find available ROS 2 workspaces in the home directory."""
        workspaces = []
        setup_files = [
            "install/setup.bash",
            "install/setup.zsh",
            "install/setup.sh",
            "devel/setup.bash",
            "devel/setup.zsh",
            "devel/setup.sh",
        ]

        for naming_pattern in naming_patterns:
            self.logger.debug(
                f"Searching for available workspaces in {home_dir} "
                f"with pattern '{naming_pattern}'"
            )
            for dir in home_dir.glob(naming_pattern):
                if dir.is_dir():
                    src_dir = dir / "src"
                    if src_dir.exists() and src_dir.is_dir():
                        workspaces.append(dir)
                        self.logger.debug(f"Found workspace with 'src' directory: {dir}")
                        continue
                    for setup_file in setup_files:
                        setup_path = dir / setup_file
                        if setup_path.exists():
                            workspaces.append(dir)
                            self.logger.debug(f"Found workspace: {dir}")
                            break

        self.logger.debug(f"Total workspaces found: {len(workspaces)}")
        return workspaces

    def _find_ros2_underlays(self, search_dirs: List[Path] = None) -> List[Path]:
        """Search for ROS 2 installs and workspaces."""
        if search_dirs is None:
            search_dirs = [Path("/opt/ros")]

        underlays = []
        setup_files = ["setup.bash", "setup.zsh", "setup.sh"]

        for search_dir in search_dirs:
            if not search_dir.exists():
                self.logger.debug(f"Search directory does not exist: {search_dir}")
                continue

            self.logger.debug(f"Searching in directory: {search_dir}")
            for subdir in search_dir.iterdir():
                if subdir.is_dir():
                    for setup_file in setup_files:
                        setup_path = subdir / setup_file
                        if setup_path.exists():
                            underlays.append(subdir)
                            self.logger.debug(f"Found underlay: {subdir}")
                            break
                    else:
                        for install_type in ["install", "devel"]:
                            install_dir = subdir / install_type
                            if install_dir.exists() and install_dir.is_dir():
                                for setup_file in setup_files:
                                    setup_path = install_dir / setup_file
                                    if setup_path.exists():
                                        underlays.append(subdir)
                                        self.logger.debug(
                                            f"Found underlay in "
                                            f"{install_type}: {subdir}"
                                        )
                                        break
                                else:
                                    continue
                                break

        self.logger.debug(f"Total underlays found: {len(underlays)}")
        return underlays

    def _prompt_for_workspace(
        self,
        default_workspace: Path = None,
        allow_available: bool = True,
        allow_create: bool = True,
    ) -> Path:
        """Prompt the user to select or create a workspace."""
        if self.assume == "yes" or self.assume == "default":
            if allow_available:
                workspaces = self._find_available_workspaces()
                if workspaces:
                    selected_workspace = workspaces[0]
                    self.logger.debug(
                        f"Assuming default workspace: {selected_workspace}"
                    )
                    return selected_workspace
            if allow_create and default_workspace:
                workspace = Path(default_workspace).expanduser().resolve()
                self.logger.debug(f"Assuming default workspace path: {workspace}")
                return workspace
            else:
                self.logger.error(
                    "No workspaces available and " "cannot create a new one by default."
                )
                sys.exit(1)

        if allow_available:
            workspaces = self._find_available_workspaces()
            options = [f"{ws.stem} ('{ws}')" for ws in workspaces]
            options.append(
                "Create a new workspace"
                if allow_create
                else "Enter an existing workspace path"
            )

            selection = self.user_prompter.prompt_selection(
                message="Available ROS 2 workspaces:", options=options, default=1
            )

            if selection < len(workspaces):
                selected_workspace = workspaces[selection]
                self.logger.debug(
                    f"User selected existing workspace: {selected_workspace}"
                )
                return selected_workspace
            elif allow_create and selection == len(workspaces):
                # Prompt for new workspace path
                workspace_input = self.user_prompter.prompt_input(
                    "Enter the full path for the new workspace",
                    default=str(default_workspace) if default_workspace else "",
                )
                workspace = Path(workspace_input).expanduser().resolve()
                if not workspace.exists():
                    try:
                        workspace.mkdir(parents=True, exist_ok=True)
                        self.logger.debug(f"Created new workspace: {workspace}")
                    except Exception as e:
                        self.logger.error(f"Cannot create workspace directory: {e}")
                        sys.exit(1)
                else:
                    self.logger.debug(f"Selected existing workspace: {workspace}")
                return workspace
            else:
                self.logger.error("Invalid workspace selection.")
                sys.exit(1)
        else:
            # Directly prompt for workspace path
            workspace_input = self.user_prompter.prompt_input(
                "Enter the full path for the workspace",
                default=str(default_workspace) if default_workspace else "",
            )
            workspace = Path(workspace_input).expanduser().resolve()
            if not workspace.exists():
                try:
                    workspace.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Created new workspace: {workspace}")
                except Exception as e:
                    self.logger.error(f"Cannot create workspace directory: {e}")
                    sys.exit(1)
            else:
                self.logger.debug(f"Selected existing workspace: {workspace}")
            return workspace

    def _prompt_for_underlay(
        self,
        underlays: List[Path],
        default_underlay: Optional[Path] = None,
    ) -> Optional[Path]:
        """Prompt the user to select an underlay or enter a custom path."""
        if self.assume == "yes" or self.assume == "default":
            if default_underlay:
                self.logger.debug(
                    f"Assuming provided default underlay: {default_underlay}"
                )
                return default_underlay
            elif underlays:
                selected_underlay = underlays[0]
                self.logger.debug(f"Assuming default underlay: {selected_underlay}")
                return selected_underlay
            else:
                self.logger.warning("No underlays available to select by default.")
                return None

        if not underlays:
            self.logger.warning("No underlays found. Proceeding without underlays.")
            return None

        # Prepare options with "(last used underlay)" label
        options = []
        for underlay in underlays:
            if default_underlay and underlay == default_underlay:
                option_str = f"{underlay.stem} ('{underlay}') (last used underlay)"
            else:
                option_str = f"{underlay.stem} ('{underlay}')"
            options.append(option_str)

        # Append the option for custom underlay path
        options.append("Enter a custom underlay path")

        # Determine default option index
        if default_underlay and default_underlay in underlays:
            default_option = underlays.index(default_underlay) + 1  # 1-based index
        elif default_underlay and default_underlay not in underlays:
            # If the last used underlay isn't in the current list, append it
            underlays.append(default_underlay)
            options.insert(-1, f"{default_underlay} (last used underlay)")
            default_option = len(underlays)
        else:
            default_option = len(underlays) + 1  # Default to 'Enter a custom path'

        selection = self.user_prompter.prompt_selection(
            message="Available ROS 2 underlays:",
            options=options,
            default=default_option
        )

        if selection < len(underlays):
            selected_underlay = underlays[selection]
            self.logger.debug(f"User selected underlay: {selected_underlay}")
            return selected_underlay
        elif selection == len(underlays):
            # Handle custom path input
            custom_path = self.user_prompter.prompt_input(
                "Enter the path to the custom underlay"
            )
            custom_underlay = Path(custom_path).expanduser().resolve()
            if not custom_underlay.exists():
                self.logger.error(
                    f"Provided underlay path does not exist: {custom_underlay}"
                )
                sys.exit(1)
            setup_file = self.get_workspace_setup_file(custom_underlay)
            if not setup_file or not setup_file.exists():
                self.logger.error(
                    f"No setup file found in the custom underlay: {custom_underlay}"
                )
                print("No valid setup file found in the provided underlay path.")
                sys.exit(1)
            self.logger.debug(f"User entered custom underlay: {custom_underlay}")
            return custom_underlay
        else:
            self.logger.error("Invalid underlay selection.")
            sys.exit(1)

    def _verify_ros_setup(self) -> bool:
        """Verify that ROS 2 environment variables are set correctly."""
        required_vars = [
            "ROS_DISTRO",
            "ROS_VERSION",
            "AMENT_PREFIX_PATH",
            "CMAKE_PREFIX_PATH",
            "COLCON_PREFIX_PATH",
        ]

        missing_vars = [var for var in required_vars if var not in os.environ]

        if missing_vars:
            self.logger.warning("Some ROS 2 environment variables are missing:")
            for var in missing_vars:
                self.logger.warning(f"  - {var}")
            return False
        return True

    def get_or_prompt_workspace_config(
        self,
        available_configs: Optional[List[Path]] = None,
        default_config: Optional[Path] = None,
    ) -> Path:
        """
        Get the workspace configuration path from arguments or prompt the user.
        """
        workspace_config = None
        if self.workspace_config:
            try:
                # Attempt absolute path
                workspace_config = Path(self.workspace_config).resolve()
                self.logger.debug(
                    f"Attempting to resolve absolute workspace config path: {workspace_config}"
                )
                if not workspace_config.is_file():
                    raise ValueError
            except Exception:
                try:
                    # Attempt relative to config/workspaces
                    workspace_config = (
                        Path(__file__).parent.parent
                        / "config"
                        / "workspaces"
                        / self.workspace_config
                    ).resolve()
                    self.logger.debug(
                        f"Attempting to resolve relative workspace config: {workspace_config}"
                    )
                    if not workspace_config.is_file():
                        raise ValueError
                except Exception:
                    try:
                        # Attempt adding .yaml extension
                        workspace_config = (
                            Path(__file__).parent.parent
                            / "config"
                            / "workspaces"
                            / f"{self.workspace_config}.yaml"
                        ).resolve()
                        self.logger.debug(
                            f"Attempting to resolve workspace config path with .yaml extension: {workspace_config}"
                        )
                        if not workspace_config.is_file():
                            raise ValueError
                    except Exception:
                        workspace_config = None
                        self.logger.error(
                            "Unable to resolve workspace config argument!"
                        )

        if not workspace_config:
            if available_configs is None:
                available_configs = self._get_available_workspace_configs()

            workspace_config = self._prompt_for_workspace_config(available_configs, default_config)
            self.logger.debug(f"Selected workspace config: {workspace_config}")

        return workspace_config

    def get_or_prompt_workspace_path(
        self,
        default_workspace: Optional[Path] = None,
        allow_available: bool = True,
        allow_create: bool = True,
    ) -> Path:
        """
        Get the workspace path, or prompt the user to select or create one.
        """
        if self.workspace_path:
            workspace_path = self.workspace_path
            self.logger.debug(f"Using provided workspace path: {workspace_path}")
            return workspace_path

        return self._prompt_for_workspace(
            default_workspace=default_workspace,
            allow_available=allow_available,
            allow_create=allow_create,
        )

    def get_or_prompt_underlay_path(
        self,
        default_underlay: Optional[Path] = None,
        search_dirs: Optional[List[Path]] = None,
    ) -> Optional[Path]:
        """
        Get the underlay path, or prompt the user to select one.
        """
        if self.underlay_path:
            underlay_path = self.underlay_path
            self.logger.debug(f"Using provided underlay path: {underlay_path}")
            return underlay_path

        if search_dirs is None:
            search_dirs = [Path("/opt/ros"), Path.home()]

        underlays = self._find_ros2_underlays(search_dirs)

        return self._prompt_for_underlay(underlays, default_underlay=default_underlay)

    def get_or_prompt_build_script_path(
        self,
        default_build_script: Optional[Path] = None,
    ) -> Path:
        """
        Get the build script path, or prompt the user to select one.
        """
        if self.build_script_path:
            build_scripts = self._get_available_build_scripts()

            build_script_path = None
            for build_script in build_scripts:
                if str(self.build_script_path) in str(build_script):
                    build_script_path = build_script
                    break

            if not build_script_path:
                self.logger.error(f"Failed to match provided build script path: {build_script_path}")
                sys.exit(1)
            else:
                self.logger.debug(f"Using provided build script path: {build_script_path}")
                return Path(build_script_path).expanduser().resolve()

        return self._prompt_for_build_script(
            scripts=None,
            default_script=default_build_script,
        )

    def _get_available_workspace_configs(self) -> List[Path]:
        """
        Retrieve available workspace configuration files.
        """
        workspaces_dir = Path(__file__).parent.parent / "config" / "workspaces"
        workspace_configs = list(workspaces_dir.glob("*.yaml"))
        self.logger.debug(f"Found workspace configs: {workspace_configs}")
        return workspace_configs

    def _prompt_for_workspace_config(
        self, workspace_configs: List[Path], default_config: Optional[Path] = None
    ) -> Path:
        """
        Prompt the user to select a workspace configuration from the available options.
        """
        if self.assume == "yes" or self.assume == "default":
            selected_config = default_config or (workspace_configs[0] if workspace_configs else None)
            if selected_config:
                self.logger.debug(
                    f"Assuming default workspace config: {selected_config}"
                )
                return selected_config
            else:
                self.logger.error(
                    "No workspace configurations available to select by default."
                )
                sys.exit(1)

        options = [f"{config.stem} ('{config}')" for config in workspace_configs]
        options.append("Enter a custom workspace config file path")

        selection = self.user_prompter.prompt_selection(
            message="Available workspace configurations:",
            options=options,
            default=1,  # First option as default
        )

        if selection < len(workspace_configs):
            selected_config = workspace_configs[selection]
            self.logger.debug(f"User selected workspace config: {selected_config}")
            return selected_config

        # Handle custom path input
        custom_config = self.user_prompter.prompt_input(
            "Enter the path to the custom workspace config"
        )
        custom_config_path = Path(custom_config).expanduser().resolve()

        if not custom_config_path.is_file():
            self.logger.error(
                f"Custom workspace config does not exist: {custom_config_path}"
            )
            sys.exit(1)

        self.logger.debug(f"User provided custom workspace config: {custom_config_path}")
        return custom_config_path

    def _get_available_build_scripts(self) -> List[Path]:
        """Get available ROS 2 workspace build scripts"""
        scripts_dir = Path(__file__).parent.parent / 'config' / 'scripts'
        pattern = f"build_*.yaml"
        return list(scripts_dir.glob(pattern))

    def _prompt_for_build_script(self,
            scripts: Optional[List[Path]],
            default_script: Optional[Path]) -> Path:
        """Prompt user for ROS 2 workspace build script given list of script paths"""
        if not scripts:
            scripts = self._get_available_build_scripts()

        options = [f"{script.name}" for script in scripts]

        if not default_script:
            default_script_index = options.index("build_workspace.yaml") + 1
        else:
            default_script_index = scripts.index(default_script) + 1

        selection = self.user_prompter.prompt_selection(
            message="Select a build script:",
            options=options,
            default=default_script_index,
        )
        return scripts[selection]
