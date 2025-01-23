import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import yaml

from .logger import Logger
from .shell import Shell


class WorkspaceManager:
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        workspace_config: Optional[str] = None,
        assume_yes: bool = False,
        logger: Optional[Logger] = None,
    ):
        self.logger = logger or Logger()
        self.assume_yes = assume_yes

        self.workspace_path = (
            Path(workspace_path).expanduser().resolve() if workspace_path else None
        )
        self.workspace_config = (
            Path(workspace_config).expanduser().resolve() if workspace_config else None
        )

    def set_workspace_path(self, workspace_path: Path):
        """
        Set and validate the workspace path.

        Args:
            workspace_path (Path): The new workspace path to set.

        Raises:
            PermissionError: If the workspace path is not writable.
            ValueError: If the workspace path is invalid.
        """
        self.logger.debug(f"Setting workspace path to: {workspace_path}")
        validated_workspace = self.validate_workspace_path(
            workspace_path, allow_create=True
        )
        self.workspace_path = validated_workspace
        self.logger.debug(f"Workspace path set to: {self.workspace_path}")

    def setup_workspace(self):
        """Set up the workspace by cloning repositories according to the
        workspace_config."""
        try:
            if not self.workspace_path:
                raise ValueError(
                    "Workspace path is not set. " "Use `set_workspace_path` first."
                )

            # Validate workspace path
            workspace = self.validate_workspace_path(
                self.workspace_path, allow_create=True
            )

            # Load and validate workspace configuration
            with open(self.workspace_config, "r") as f:
                config = yaml.safe_load(f)
            self.validate_workspace_config(config)

            # Validate/create src directory
            self.validate_src_directory(workspace, allow_create=True)

            self.logger.info(
                f"Setting up workspace at '{workspace}' "
                f"using config '{self.workspace_config}'"
            )

            # Clone repositories
            self.clone_repositories(workspace, self.workspace_config)
        except Exception as e:
            self.logger.error(f"Error setting up workspace: {e}")
            sys.exit(1)

    def update_workspace(self):
        """Update workspace by pulling repositories therein."""
        try:
            if not self.workspace_path:
                raise ValueError(
                    "Workspace path is not set. " "Use `set_workspace_path` first."
                )

            # Validate workspace path
            workspace = self.validate_workspace_path(self.workspace_path)

            # Validate src directory
            self.validate_src_directory(workspace)

            self.logger.info(f"Updating workspace at '{workspace}'")

            # Pull repositories
            self.pull_repositories(workspace)
        except Exception as e:
            self.logger.error(f"Error updating workspace: {e}")
            sys.exit(1)

    def build_workspace(self):
        """Build the workspace."""
        try:
            # Validate workspace path
            workspace = self.validate_workspace_path(self.workspace_path)
            self.logger.debug(f"Validated workspace path for build: {workspace}")

            # Validate src directory
            self.validate_src_directory(workspace)

            # Determine the path to setup.bash
            setup_bash_path = workspace / "install" / "setup.bash"
            default_underlay_path_str = self.parse_setup_bash(setup_bash_path)
            default_underlay = (
                Path(default_underlay_path_str) if default_underlay_path_str else None
            )

            # Find and set up underlays
            underlays = self.find_ros2_underlays([Path("/opt/ros"), Path.home()])

            # Remove duplicates and ensure all underlays are resolved
            underlays = list(set(underlays))

            # Prompt for underlay
            underlay = self.prompt_for_underlay(
                underlays, default_underlay=default_underlay
            )

            if underlay:
                self.logger.info(f"Using underlay: {underlay}")
                setup_file = self.get_workspace_setup_file(underlay)
                if setup_file:
                    self.logger.debug(f"Sourcing setup file: {setup_file}")
                    if Shell.source_file(setup_file):
                        self.logger.info("Successfully sourced setup file.")
                        if not self.verify_ros_setup():
                            self.logger.warning(
                                "ROS environment may not be fully configured."
                            )
                    else:
                        self.logger.warning("Failed to source setup file.")
                else:
                    self.logger.warning(
                        f"Setup file not found for underlay: {underlay}"
                    )

            # Proceed with build
            self.logger.info("Starting workspace build using colcon...")
            Shell.run_command(["colcon", "build"], cwd=str(workspace), verbose=True)
            self.logger.info("Workspace build completed successfully.")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error building workspace: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            sys.exit(1)

    def validate_workspace_path(
        self, workspace_path: Path, allow_create: bool = False
    ) -> Path:
        """Validate that the workspace path is writable."""
        if workspace_path.exists():
            if not os.access(workspace_path, os.W_OK):
                raise PermissionError(f"No write permission for {workspace_path}")
        elif allow_create:
            # Attempt to create the workspace directory
            try:
                workspace_path.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created workspace directory: {workspace_path}")
            except Exception as e:
                raise PermissionError(
                    f"Cannot create workspace directory: {workspace_path}"
                ) from e
        else:
            raise ValueError("Workspace path does not exist.")
        self.logger.debug(f"Workspace path validated: {workspace_path}")
        return workspace_path

    def validate_workspace_config(self, config: dict) -> dict:
        """Validate workspace configuration structure."""
        if not isinstance(config, dict):
            raise ValueError(
                "Invalid workspace configuration format; expected a dictionary."
            )
        if "repositories" not in config:
            raise ValueError("No 'repositories' specified in configuration.")
        if not isinstance(config["repositories"], dict):
            raise ValueError(
                "'repositories' should be a dictionary of " "repository configurations."
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
                    "Each repository must have 'type', 'url' and " "'version' fields."
                )
        self.logger.debug("Workspace configuration validated successfully.")
        return config

    def validate_src_directory(
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

    def parse_setup_bash(self, setup_bash_path: Path) -> Optional[str]:
        """
        Parse the setup.bash file to extract the last underlay in the build
        chain (the second-last COLCON_CURRENT_PREFIX entry in the setup file).

        Args:
            setup_bash_path (Path): Path to the setup.bash file.

        Returns:
            Optional[str]: The inferred underlay path if found, else None.
        """
        if not setup_bash_path.exists():
            self.logger.warning(f"Setup file does not exist: {setup_bash_path}")
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
                    f"Inferred default underlay before stripping: "
                    f"{default_underlay}"
                )

                # Strip '/install' or '/devel' only if present at the end
                if default_underlay.endswith(("/install", "/devel")):
                    stripped_underlay = Path(default_underlay).parent
                    default_underlay_str = str(stripped_underlay)
                    self.logger.debug(
                        f"Inferred default underlay after stripping: "
                        f"{default_underlay_str}"
                    )
                else:
                    # Retain the original path if no stripping is needed
                    default_underlay_str = default_underlay
                    self.logger.debug(
                        f"Inferred default underlay without stripping: "
                        f"{default_underlay_str}"
                    )

                return default_underlay_str
            else:
                self.logger.warning("Not enough COLCON_CURRENT_PREFIX entries found.")
                return None

        except Exception as e:
            self.logger.error(f"Error parsing setup.bash: {e}")
            return None

    def clone_repositories(self, workspace: Path, workspace_config: Path):
        """Clone repos defined in the workspace config file to the ROS 2
        workspace."""
        try:
            self.logger.info("Cloning repositories...")
            Shell.run_command(
                ["vcs", "import", "--input", str(workspace_config), "src"],
                cwd=str(workspace),
                verbose=True,
            )
            self.logger.info("Repositories cloned successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repositories: {e}")
            sys.exit(1)

    def pull_repositories(self, workspace: Path):
        try:
            self.logger.info("Pulling repositories...")
            Shell.run_command(
                ["vcs", "pull", "src"],
                cwd=str(workspace),
                verbose=True,
            )
            self.logger.info("Repositories pulled successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to pull repositories: {e}")
            sys.exit(1)

    def find_available_workspaces(self, home_dir: Path = Path.home()) -> List[Path]:
        """Find available ROS 2 workspaces in the home directory."""
        workspaces = []
        naming_pattern = "*_ws"
        setup_files = [
            "install/setup.bash",
            "install/setup.zsh",
            "install/setup.sh",
            "devel/setup.bash",
            "devel/setup.zsh",
            "devel/setup.sh",
        ]

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

    def find_ros2_underlays(self, search_dirs: List[Path] = None) -> List[Path]:
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

    def prompt_for_workspace(
        self,
        default_workspace: Path = None,
        allow_available: bool = True,
        allow_create: bool = True,
    ) -> Path:
        """Prompt the user to select or create a workspace."""
        if self.assume_yes:
            if allow_available:
                workspaces = self.find_available_workspaces()
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
            workspaces = self.find_available_workspaces()
            print("\nAvailable ROS 2 workspaces in your home directory:")
            for i, workspace in enumerate(workspaces, start=1):
                print(f"{i}: {workspace}")

            if allow_create:
                print(f"{len(workspaces)+1}: Create a new workspace")
            else:
                print(f"{len(workspaces)+1}: Enter an existing workspace path")
            create_option = custom_option = len(workspaces) + 1

            while True:
                try:
                    if allow_create:
                        if default_workspace and default_workspace in workspaces:
                            default_option = workspaces.index(default_workspace) + 1
                            prompt_msg = (
                                f"Select a workspace " f"(default: {default_option}): "
                            )
                        else:
                            default_option = create_option
                            prompt_msg = (
                                f"Select a workspace " f"(default: {default_option}): "
                            )
                    else:
                        default_option = create_option
                        prompt_msg = f"Select a workspace (default: {default_option}): "

                    choice = input(prompt_msg).strip()
                except EOFError:
                    choice = str(default_option)

                if not choice:
                    choice_num = default_option
                else:
                    try:
                        choice_num = int(choice)
                    except ValueError:
                        print(
                            "Invalid input. Please enter a number "
                            "corresponding to the options."
                        )
                        continue

                if allow_available and 1 <= choice_num <= len(workspaces):
                    selected_workspace = workspaces[choice_num - 1]
                    self.logger.debug(
                        f"User selected existing workspace: " f"{selected_workspace}"
                    )
                    return selected_workspace
                elif allow_create and choice_num == create_option:
                    workspace_input = input(
                        f"Enter the full path for the new workspace "
                        f"(default: {default_workspace}): "
                    ).strip()
                    if not workspace_input:
                        workspace_input = str(default_workspace)
                    workspace = Path(workspace_input).expanduser().resolve()
                    if not workspace.exists():
                        try:
                            self.validate_workspace_path(workspace, allow_create=True)
                            self.validate_src_directory(workspace, allow_create=True)
                            workspace.mkdir(parents=True, exist_ok=True)
                            self.logger.debug(f"Created new workspace: {workspace}")
                        except Exception as e:
                            self.logger.error(f"Invalid workspace path: {e}")
                            print(f"Invalid workspace: {e}")
                            continue
                    else:
                        try:
                            self.validate_workspace_path(workspace, allow_create=True)
                            self.validate_src_directory(workspace, allow_create=True)
                            self.logger.debug(
                                f"Selected existing workspace: {workspace}"
                            )
                        except Exception as e:
                            self.logger.error(f"Invalid workspace: {e}")
                            print(f"Invalid workspace: {e}")
                            continue
                    return workspace
                elif (
                    not allow_create
                    and allow_available
                    and 1 <= choice_num <= len(workspaces)
                ):
                    selected_workspace = workspaces[choice_num - 1]
                    self.logger.debug(
                        f"User selected existing workspace: " f"{selected_workspace}"
                    )
                    return selected_workspace
                elif not allow_create and choice_num == custom_option:
                    workspace_input = input(
                        f"Enter the full path to an existing workspace "
                        f"(default: {default_workspace}): "
                    ).strip()
                    if not workspace_input:
                        workspace_input = str(default_workspace)
                    workspace = Path(workspace_input).expanduser().resolve()
                    try:
                        self.validate_workspace_path(workspace)
                        self.validate_src_directory(workspace)
                        self.logger.debug(f"Selected existing workspace: {workspace}")
                    except Exception as e:
                        self.logger.error(f"Invalid workspace: {e}")
                        print(f"Invalid workspace: {e}")
                        continue
                    return workspace
                else:
                    print("Invalid selection. Please choose a valid number.")
        else:
            workspace_input = input(
                f"Enter the full path for the new workspace "
                f"(default: {default_workspace}): "
            ).strip()
            if not workspace_input:
                workspace_input = str(default_workspace)
            workspace = Path(workspace_input).expanduser().resolve()
            if not workspace.exists():
                try:
                    self.validate_workspace_path(workspace, allow_create=True)
                    self.validate_src_directory(workspace, allow_create=True)
                    workspace.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Created new workspace: {workspace}")
                except Exception as e:
                    self.logger.error(f"Invalid workspace path: {e}")
                    print(f"Invalid workspace: {e}")
                    return self.prompt_for_workspace(
                        default_workspace=default_workspace,
                        allow_available=allow_available,
                        allow_create=allow_create,
                    )
            else:
                try:
                    self.validate_workspace_path(workspace)
                    self.validate_src_directory(workspace)
                    self.logger.debug(f"Selected existing workspace: {workspace}")
                except Exception as e:
                    self.logger.error(f"Invalid workspace: {e}")
                    print(f"Invalid workspace: {e}")
                    return self.prompt_for_workspace(
                        default_workspace=default_workspace,
                        allow_available=allow_available,
                        allow_create=allow_create,
                    )
            return workspace

    def prompt_for_underlay(
        self,
        underlays: List[Path],
        default_underlay: Optional[Path] = None,
    ) -> Optional[Path]:
        """Prompt the user to select an underlay or enter a custom path."""
        if self.assume_yes:
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

        print("\nAvailable underlays:")
        default_option = None
        for i, underlay in enumerate(underlays, start=1):
            if default_underlay and underlay == default_underlay:
                print(f"{i}: {underlay} (last used underlay)")
                default_option = i
            else:
                print(f"{i}: {underlay}")

        custom_option_number = len(underlays) + 1
        print(f"{custom_option_number}: Enter a custom underlay path")

        if default_underlay and default_underlay in underlays:
            default_option = underlays.index(default_underlay) + 1
        elif default_underlay and default_underlay not in underlays:
            underlays.append(default_underlay)
            print(f"{len(underlays)}: {default_underlay} (last used underlay)")
            custom_option_number = len(underlays) + 1
            print(f"{custom_option_number}: Enter a custom underlay path")
            default_option = len(underlays)
        else:
            default_option = custom_option_number

        prompt_msg = f"Select an underlay (default: {default_option}): "

        while True:
            try:
                choice = input(prompt_msg).strip()
            except EOFError:
                choice = str(default_option)

            if not choice:
                choice_num = default_option
            else:
                try:
                    choice_num = int(choice)
                except ValueError:
                    print(
                        "Invalid input. Please enter a number "
                        "corresponding to the options."
                    )
                    continue

            if 1 <= choice_num <= len(underlays):
                selected_underlay = underlays[choice_num - 1]
                self.logger.debug(f"User selected underlay: {selected_underlay}")
                return selected_underlay
            elif choice_num == custom_option_number:
                custom_path = input("Enter the path to the custom underlay: ").strip()
                if not custom_path:
                    print("Please enter a valid existing path.")
                    continue
                custom_underlay = Path(custom_path).expanduser().resolve()
                if not custom_underlay.exists():
                    self.logger.error(
                        f"Provided underlay path does not exist: " f"{custom_underlay}"
                    )
                    print(
                        "Provided underlay path does not exist. "
                        "Please enter a valid path."
                    )
                    continue
                setup_file = self.get_workspace_setup_file(custom_underlay)
                if not setup_file or not setup_file.exists():
                    self.logger.error(
                        f"No setup file found in the custom underlay: "
                        f"{custom_underlay}"
                    )
                    print("No valid setup file found in " "the provided underlay path.")
                    continue
                self.logger.debug(
                    f"User entered custom underlay: " f"{custom_underlay}"
                )
                return custom_underlay
            else:
                print("Invalid selection. Please choose a valid number.")

    def verify_ros_setup(self) -> bool:
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
