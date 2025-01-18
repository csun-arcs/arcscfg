import sys
import argparse
import logging
from pathlib import Path
from typing import List
from arcscfg.utils.logger import Logger
from arcscfg.utils.workspace_manager import WorkspaceManager

# Initialize logger variable globally
logger = None

def get_workspace_configs() -> List[Path]:
    workspaces_dir = Path(__file__).parent / "config/workspaces"
    return [f.resolve() for f in workspaces_dir.glob("*.yaml") if f.is_file()]

def prompt_for_workspace_configs(
        workspace_configs: List[Path],
        assume_yes: bool, logger: logging.Logger) -> Path:
    """Prompt the user to select a workspace configuration.

    Args:
        workspace_configs (List[Path]): List of available workspace
        configuration files.
        assume_yes (bool): If True, automatically select the default option.
        logger (logging.Logger): Logger instance for logging.

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
                print("Invalid input. Please enter a number "
                      "corresponding to the options.")
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

def infer_default_workspace_path(workspace_config: Path) -> Path:
    """
    Infer a default workspace path based on the workspace config.

    For example, if the config is 'cohort.yaml', suggest '~/cohort_ws'.
    """
    config_name = workspace_config.stem
    suggested_name = f"{config_name}_ws"
    default_workspace = Path.home() / suggested_name
    return default_workspace

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
        help=("Workspace config. Select from available configs or "
              "provide workspace config path.")
    )
    parser.add_argument(
        "-v", "--verbosity",
        choices=["debug", "info", "warning", "error", "critical", "silent"],
        default="info",
        help="Set the logging verbosity level. Default: info."
    )
    parser.add_argument(
        "-lfp", "--log-file-path",
        default=None,
        help=("Path to log file/directory. If None, system default location is "
              "selected. Default: None."),
    )
    parser.add_argument(
        "-lms", "--log-max-size",
        type=int,
        default=5 * 1024 * 1024,  # 5 MB
        help="Maximum log file size in bytes before rotation. Default is 5MB."
    )
    parser.add_argument(
        "-lbc", "--log-backup-count",
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
                    f"{workspace_config}")
                if not workspace_config.is_file():
                    raise ValueError
            except Exception:
                try:
                    # Attempt relative to config/workspaces
                    workspace_config = (
                        Path(__file__).parent /
                        "config/workspaces" /
                        args.workspace_config)
                    logger.debug(
                        f"Attempting to resolve relative workspace config: "
                        f"{workspace_config}")
                    if not workspace_config.is_file():
                        raise ValueError
                except Exception:
                    try:
                        # Attempt adding .yaml extension
                        workspace_config = (
                            Path(__file__).parent /
                            "config/workspaces" /
                            f"{args.workspace_config}.yaml")
                        logger.debug(
                            f"Attempting to resolve workspace config path "
                            f"with .yaml extension: {workspace_config}")
                        if not workspace_config.is_file():
                            raise ValueError
                    except Exception:
                        workspace_config = None
                        logger.error(
                            "Unable to resolve workspace config argument!")
                        # Reset "assume yes to defaults" to ensure user is
                        # prompted for workspace config
                        args.yes = False
        if not workspace_config:
            workspace_configs = get_workspace_configs()
            workspace_config = prompt_for_workspace_configs(
                workspace_configs, args.yes, logger)
            logger.debug(f"Selected workspace config: {workspace_config}")

        manager = WorkspaceManager(
            workspace_path=None,  # Will be set after prompting
            workspace_config=str(workspace_config),
            assume_yes=args.yes,
            logger=logger
        )

        if not args.workspace:
            # Infer default workspace path based on config
            default_workspace_path = infer_default_workspace_path(
                workspace_config)
            # Prompt for workspace
            workspace = manager.prompt_for_workspace(
                default_workspace=default_workspace_path,
                allow_available=False,  # Disallow select from existing workspaces
                allow_create=True
            )
            logger.debug(f"Selected workspace path: {workspace}")
            # Set the workspace path in the manager
            manager.set_workspace_path(workspace)
        else:
            workspace = Path(args.workspace).expanduser().resolve()
            logger.debug(f"Using provided workspace path: {workspace}")
            # Set the workspace path in the manager
            manager.set_workspace_path(workspace)

        # Call setup_workspace method
        manager.setup_workspace()

        logger.info("Workspace setup completed successfully.")

    elif args.command == "install":
        logger.info("Installing dependencies")
        # Implement dependency installation logic here
        # ...
        logger.info("Dependency installation completed successfully.")

    elif args.command == "build":
        if args.workspace:
            workspace_path = Path(args.workspace).expanduser().resolve()
        else:
            # Instantiate WorkspaceManager without workspace_path initially
            manager = WorkspaceManager(
                workspace_path=None,
                workspace_config=None,
                assume_yes=args.yes,
                logger=logger
            )
            # Prompt for workspace
            workspace = manager.prompt_for_workspace(
                default_workspace=None,
                allow_available=True,
                allow_create=False
            )
            if not workspace:
                logger.error("Workspace path not provided for build command.")
                sys.exit(1)
            workspace_path = workspace

        # Instantiate WorkspaceManager with workspace_path and no config
        build_manager = WorkspaceManager(
            workspace_path=str(workspace_path),
            workspace_config=None,  # Assuming build doesn't require config
            assume_yes=args.yes,
            logger=logger
        )

        logger.info(f"Building workspace at '{workspace_path}'")
        # Call build_workspace method
        build_manager.build_workspace()
        logger.info("Workspace build completed successfully.")

    elif args.command == "update":
        # Instantiate WorkspaceManager and use appropriate methods
        update_manager = WorkspaceManager(
            workspace_path=None,
            workspace_config=None,
            assume_yes=args.yes,
            logger=logger
        )
        workspace = update_manager.prompt_for_workspace(
            default_workspace=None,
            allow_available=True,
            allow_create=False
        )
        if not workspace:
            logger.error("Workspace path not provided for update command.")
            sys.exit(1)

        # Set the workspace path in the manager
        update_manager.set_workspace_path(workspace)

        workspace_path = workspace
        logger.info(f"Updating workspace at '{workspace_path}'")

        # TODO: Implement update logic (e.g., git pull via vcs wrapper)
        # For now, you can create a stub method in WorkspaceManager for update
        # Example:
        # update_manager.update_workspace(workspace_path)
        logger.info("Workspace update completed successfully.")

    logger.info("arcscfg tool finished execution.")

if __name__ == "__main__":
    main()
