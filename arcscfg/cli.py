import sys
import argparse
from pathlib import Path
from typing import List
from arcscfg.utils.workspace_setup import setup_workspace
from arcscfg.utils.workspace_build import build_workspace
from arcscfg.utils.logger import Logger
from arcscfg.utils.workspace_validation import find_available_workspaces

from arcscfg.utils.workspace_validation import (
    validate_workspace_path,
    validate_src_directory,
)

# Initialize logger variable globally
logger = None

def get_workspace_configs() -> List[Path]:
    workspaces_dir = Path(__file__).parent / "config/workspaces"
    return [f.resolve() for f in workspaces_dir.glob("*.yaml") if f.is_file()]

def prompt_for_workspace_configs(
        workspace_configs: List[Path], assume_yes: bool) -> Path:
    """Prompt the user to select a workspace configuration.

    Args:
        workspace_configs (List[Path]): List of available workspace
    configuration files.
        assume_yes (bool): If True, automatically select the default option.

    Returns:
        Path: Selected workspace configuration file path.
    """
    if assume_yes:
        selected_config = workspace_configs[0] if workspace_configs else None
        if selected_config:
            logger.debug(
                f"Assuming default workspace config: {selected_config}")
            return selected_config
        else:
            logger.error(
                "No workspace configurations available to select by default.")
            sys.exit(1)

    print("\nAvailable workspace configs:")
    for i, workspace_config in enumerate(workspace_configs, start=1):
        print(f"{i}: {workspace_config.name}")

    print(f"{len(workspace_configs)+1}: Enter a custom workspace config path")

    while True:
        try:
            choice = input("Select a workspace config (default: 1): ").strip()
        except EOFError:
            choice = "1"

        if not choice:
            choice_num = 1
        else:
            try:
                choice_num = int(choice)
            except ValueError:
                print("Invalid input. Please enter a number corresponding to "
                      "the options.")
                continue

        if 1 <= choice_num <= len(workspace_configs):
            selected_config = workspace_configs[choice_num - 1]
            logger.debug(f"User selected workspace config: {selected_config}")
            return selected_config
        elif choice_num == len(workspace_configs) + 1:
            # Allow user to enter a custom path
            custom_config = input(
                "Enter the path to the custom workspace config: ").strip()
            custom_config_path = Path(custom_config).expanduser().resolve()
            if not custom_config_path.is_file():
                logger.error(f"Custom workspace config does not exist: "
                             f"{custom_config_path}")
                print("Please enter a valid existing file path.")
                continue
            logger.debug(f"User entered custom workspace config: "
                         f"{custom_config_path}")
            return custom_config_path
        else:
            print("Invalid selection. Please choose a valid number.")

def infer_default_workspace_path(workspace_config: Path) -> str:
    """
    Infer a default workspace path based on the workspace config.

    For example, if the config is 'cohort.yaml', suggest '~/cohort_ws'.
    """
    config_name = workspace_config.stem
    suggested_name = f"{config_name}_ws"
    default_workspace = Path.home() / suggested_name
    return str(default_workspace)

def prompt_for_workspace(
    default_workspace: Path = None,
    allow_available: bool = True,
    allow_create: bool = True,
    assume_yes: bool = False
) -> Path:
    """
    Prompt the user to select an existing workspace or specify a workspace path.

    Args:
        default_workspace (Path, optional): The default workspace path to
    suggest. Defaults to None.
        allow_available (bool, optional): Whether to allow selecting from
    available workspaces. Defaults to True.
        allow_create (bool, optional): Whether to allow creating/selecting a
    new workspace. Defaults to True.
        assume_yes (bool): If True, automatically select the default option.

    Returns:
        Path: The selected or entered workspace path.
    """
    if assume_yes:
        if allow_available:
            workspaces = find_available_workspaces()
            if workspaces:
                selected_workspace = workspaces[0]
                logger.debug(
                    f"Assuming default workspace: {selected_workspace}")
                return selected_workspace
        if allow_create and default_workspace:
            workspace = Path(default_workspace).expanduser().resolve()
            logger.debug(f"Assuming default workspace path: {workspace}")
            return workspace
        else:
            logger.error("No workspaces available and cannot create a new one "
                         "by default.")
            sys.exit(1)

    if allow_available:
        workspaces = find_available_workspaces()
        print("\nAvailable ROS 2 workspaces in your home directory:")
        for i, workspace in enumerate(workspaces, start=1):
            print(f"{i}: {workspace}")

        if allow_create:
            print(f"{len(workspaces)+1}: Create a new workspace")
            create_option = len(workspaces) + 1
        else:
            print(f"{len(workspaces)+1}: Enter an existing workspace path")
            create_option = len(workspaces) + 1

        while True:
            try:
                if allow_create:
                    if default_workspace and default_workspace in workspaces:
                        default_option = workspaces.index(default_workspace) + 1
                        prompt_msg = (f"Select a workspace (default: "
                                      f"{default_option}): ")
                    else:
                        default_option = create_option
                        prompt_msg = (f"Select a workspace (default: "
                                      f"{default_option}): ")
                else:
                    default_option = create_option
                    prompt_msg = (f"Select a workspace (default: "
                                  f"{default_option}): ")

                choice = input(prompt_msg).strip()
            except EOFError:
                choice = str(default_option)

            if not choice:
                choice_num = default_option
            else:
                try:
                    choice_num = int(choice)
                except ValueError:
                    print("Invalid input. Please enter a number corresponding "
                          "to the options.")
                    continue

            if allow_available and 1 <= choice_num <= len(workspaces):
                selected_workspace = workspaces[choice_num - 1]
                logger.debug(
                    f"User selected existing workspace: {selected_workspace}")
                return selected_workspace
            elif allow_create and choice_num == create_option:
                # Allow user to create/select a new workspace
                workspace_input = input(
                    f"Enter the full path for the new workspace (default: "
                    f"{default_workspace}): "
                ).strip()
                if not workspace_input:
                    workspace_input = str(default_workspace)
                workspace = Path(workspace_input).expanduser().resolve()
                if not workspace.exists():
                    # Attempt to create the workspace
                    try:
                        validate_workspace_path(workspace)
                        validate_src_directory(workspace)
                        workspace.mkdir(parents=True, exist_ok=True)
                        logger.debug(f"Created new workspace: {workspace}")
                    except Exception as e:
                        logger.error(f"Invalid workspace path: {e}")
                        print(f"Invalid workspace: {e}")
                        continue
                else:
                    # Workspace exists; confirm it's a valid workspace
                    try:
                        validate_workspace_path(workspace)
                        validate_src_directory(workspace)
                        logger.debug(f"Selected existing workspace: "
                                     f"{workspace}")
                    except Exception as e:
                        logger.error(f"Invalid workspace: {e}")
                        print(f"Invalid workspace: {e}")
                        continue
                return workspace
            elif (not allow_create and allow_available and
                  1 <= choice_num <= len(workspaces)):
                selected_workspace = workspaces[choice_num - 1]
                logger.debug(f"User selected existing workspace: "
                             f"{selected_workspace}")
                return selected_workspace
            else:
                print("Invalid selection. Please choose a valid number.")
    else:
        # Directly prompt for workspace path without listing
        workspace_input = input(
            f"Enter the full path for the new workspace "
            f"(default: {default_workspace}): "
        ).strip()
        if not workspace_input:
            workspace_input = str(default_workspace)
        workspace = Path(workspace_input).expanduser().resolve()
        if not workspace.exists():
            # Attempt to create the workspace
            try:
                validate_workspace_path(workspace)
                validate_src_directory(workspace)
                workspace.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created new workspace: {workspace}")
            except Exception as e:
                logger.error(f"Invalid workspace path: {e}")
                print(f"Invalid workspace: {e}")
                # Prompt again
                return prompt_for_workspace(
                    default_workspace=default_workspace,
                    allow_available=allow_available,
                    allow_create=allow_create,
                    assume_yes=assume_yes
                )
        else:
            # Workspace exists; confirm it's a valid workspace
            try:
                validate_workspace_path(workspace)
                validate_src_directory(workspace)
                logger.debug(f"Selected existing workspace: {workspace}")
            except Exception as e:
                logger.error(f"Invalid workspace: {e}")
                print(f"Invalid workspace: {e}")
                # Prompt again
                return prompt_for_workspace(
                    default_workspace=default_workspace,
                    allow_available=allow_available,
                    allow_create=allow_create,
                    assume_yes=assume_yes
                )
        return workspace

def main():
    global logger
    parser = argparse.ArgumentParser(
        description="ARCS Environment Configurator"
    )
    parser.add_argument(
        "command", choices=["install", "setup", "build", "update"],
        help="Command to execute"
    )
    parser.add_argument(
        "-w", "--workspace",
        help="ROS 2 workspace path."
    )
    parser.add_argument(
        "-wc", "--workspace-config",
        help=f"Workspace config. Select from available configs "
             f"or provide workspace config path."
    )
    parser.add_argument(
        "-v", "--verbosity",
        choices=["debug", "info", "warning", "error",
                 "critical", "silent"],
        default="info",
        help="Set the logging verbosity level. Default: info."
    )
    parser.add_argument(
        "-lfp", "--log-file-path",
        default=None,
        help=("Path to log file/directory. If None, system default "
              "location is selected. Default: None."),
    )
    parser.add_argument(
        "-lms",
        "--log-max-size",
        type=int,
        default=5 * 1024 * 1024,  # 5 MB
        help="Maximum log file size in bytes before rotation. Default is 5MB."
    )
    parser.add_argument(
        "-lbc",
        "--log-backup-count",
        type=int,
        default=5,
        help="Number of backup log files to keep. Default is 5."
    )
    parser.add_argument(
        "-y", "--yes", "--assume-yes",
        action="store_true",
        help="Assume yes to all prompts and use default options."
    )

    args = parser.parse_args()

    # Set up logging
    logger = Logger(
        verbosity=args.verbosity,
        log_file_path=Path(args.log_file_path) if args.log_file_path else None,
        max_bytes=args.log_max_size,
        backup_count=args.log_backup_count
    )

    logger.info("Starting arcscfg tool")

    if args.command == "setup":
        workspace_config = None
        if args.workspace_config:
            try:
                # Attempt absolute path
                workspace_config = Path(args.workspace_config).resolve()
                logger.debug(
                    f"Attempting to resolve absolute workspace config path: "
                    f"{workspace_config}"
                )
                if not workspace_config.is_file():
                    raise ValueError
            except Exception:
                try:
                    # Attempt relative to config/workspaces
                    workspace_config = (Path(__file__).parent /
                                        "config/workspaces" /
                                        args.workspace_config)
                    logger.debug(
                        f"Attempting to resolve relative workspace config: "
                        f"{workspace_config}"
                    )
                    if not workspace_config.is_file():
                        raise ValueError
                except Exception:
                    try:
                        # Attempt adding .yaml extension
                        workspace_config = (Path(__file__).parent /
                                            "config/workspaces" /
                                            f"{args.workspace_config}.yaml")
                        logger.debug(
                            f"Attempting to resolve workspace config path with "
                            f".yaml extension: {workspace_config}"
                        )
                        if not workspace_config.is_file():
                            raise ValueError
                    except Exception:
                        workspace_config = None
                        logger.error(
                            "Unable to resolve workspace config argument!"
                        )
                        # Reset "assume yes to defaults" to ensure user is
                        # prompted for workspace config
                        args.yes = False
        if not workspace_config:
            workspace_configs = get_workspace_configs()
            workspace_config = prompt_for_workspace_configs(
                workspace_configs, args.yes)
            logger.debug(f"Selected workspace config: {workspace_config}")

        if not args.workspace:
            # Infer default workspace path based on config
            default_workspace_path = infer_default_workspace_path(
                Path(workspace_config))
            workspace = prompt_for_workspace(
                default_workspace=default_workspace_path,
                allow_available=False, # Disallow selecting from existing workspaces
                allow_create=True,
                assume_yes=args.yes
            )
            logger.debug(f"Selected workspace path: {workspace}")
        else:
            workspace = args.workspace
            logger.debug(f"Using provided workspace path: {workspace}")

        workspace = str(Path(workspace).expanduser().resolve())

        setup_workspace(workspace, workspace_config)

        logger.info("Workspace setup completed successfully.")

    elif args.command == "install":
        logger.info("Installing dependencies")
        # Implement dependency installation logic here
        # ...
        logger.info("Dependency installation completed successfully.")

    elif args.command == "build":
        workspace = args.workspace or prompt_for_workspace(
            allow_available=True,
            allow_create=False,
            assume_yes=args.yes
        )
        if not workspace:
            logger.error("Workspace path not provided for build command.")
            sys.exit(1)

        workspace = str(Path(workspace).expanduser().resolve())
        logger.info(f"Building workspace at '{workspace}'")
        build_workspace(workspace, assume_yes=args.yes)
        logger.info("Workspace build completed successfully.")

    elif args.command == "update":
        # Implement the 'update' command to allow updating an existing workspace
        workspace = prompt_for_workspace(
            allow_available=True,
            allow_create=False,
            assume_yes=args.yes
        )
        if not workspace:
            logger.error("Workspace path not provided for update command.")
            sys.exit(1)

        workspace = str(Path(workspace).expanduser().resolve())
        logger.info(f"Updating workspace at '{workspace}'")
        # Implement update logic (e.g., git pull via vcs wrapper)
        # ...
        logger.info("Workspace update completed successfully.")

    logger.info("arcscfg tool finished execution.")

if __name__ == "__main__":
    main()
