import os
import sys
import argparse
from pathlib import Path
from arcscfg.utils.workspace_setup import setup_workspace
from arcscfg.utils.workspace_build import build_workspace
from arcscfg.utils.logger import setup_logger
from arcscfg.utils.workspace_validation import verify_ros_setup

def get_workspace_configs(full_paths=False):
    workspaces_dir = Path(__file__).parent / "config/workspaces"
    if full_paths:
        return [f for f in workspaces_dir.glob("*.yaml") if f.is_file()]
    else:
        return [f.name for f in workspaces_dir.glob("*.yaml") if f.is_file()]

def prompt_for_workspace_configs(workspace_configs):
    """Prompt the user to select a workspace configuration."""
    print("Available workspace configs:")
    for i, workspace_config in enumerate(workspace_configs):
        print(f"{i}: {workspace_config}")

    choice = input("Select a workspace config (default: 0): ")
    if choice.strip():
        try:
            index = int(choice)
            if 0 <= index < len(workspace_configs):
                return workspace_configs[index]
        except (ValueError, IndexError):
            pass
    return workspace_configs[0]

def main():
    parser = argparse.ArgumentParser(
        description="ARCS Environment Configurator")
    parser.add_argument("command", choices=["setup", "install", "build"],
                        help="Command to execute")
    parser.add_argument("-w", "--workspace", help="ROS 2 workspace path.")
    parser.add_argument(
        "-wc", "--workspace-config",
        help=f"Workspace config. Select from available configs "
        f"({get_workspace_configs()}) or provide workspace config path.")
    parser.add_argument("-lf", "--log-file",
                        help="Path to log file.", default="arcscfg.log")
    parser.add_argument("-v", "--verbosity",
                        choices=["debug", "info", "warning", "error",
                                 "critical", "silent"],
                        default="info", help="Set the logging verbosity level.")

    args = parser.parse_args()

    # Set up logging
    log_file_path = Path(args.log_file).expanduser().resolve()
    logger = setup_logger(log_file_path, args.verbosity)

    logger.info("Starting arcscfg tool")

    if args.command == "setup":
        workspace_config = None
        if args.workspace_config:
            try:
                # Attempt absolute path
                workspace_config = Path(args.workspace_config).resolve()
                if not workspace_config.is_file():
                    raise ValueError
                logger.debug(
                    f"Using absolute workspace config: {workspace_config}")
            except Exception:
                try:
                    # Attempt relative to config/workspaces
                    workspace_config = (Path(__file__).parent /
                                        "config/workspaces" /
                                        args.workspace_config)
                    if not workspace_config.is_file():
                        raise ValueError
                    logger.debug(
                        f"Using relative workspace config: {workspace_config}")
                except Exception:
                    try:
                        # Attempt adding .yaml extension
                        workspace_config = (Path(__file__).parent /
                                            "config/workspaces" /
                                            f"{args.workspace_config}.yaml")
                        if not workspace_config.is_file():
                            raise ValueError
                        logger.debug(
                            f"Using workspace config with .yaml extension: "
                            f"{workspace_config}")
                    except Exception:
                        workspace_config = None
                        logger.error(
                            "Unable to resolve workspace config argument!")

        if not workspace_config:
            workspace_config = prompt_for_workspace_configs(
                get_workspace_configs(full_paths=True))
            logger.debug(f"Promoted workspace config: {workspace_config}")

        if not args.workspace:
            # Derive workspace name from the YAML file name
            workspace_name = Path(workspace_config).stem + "_ws"
            default_workspace = Path.home() / workspace_name
            workspace = (input(
                f"Enter workspace path (default: {default_workspace}): ") or
                         str(default_workspace))
            logger.debug(f"Derived workspace path: {workspace}")
        else:
            workspace = args.workspace
            logger.debug(f"Using provided workspace path: {workspace}")

        workspace = str(Path(workspace).expanduser())

        setup_workspace(workspace, workspace_config)

        logger.info("Workspace setup completed successfully.")

    elif args.command == "install":
        logger.info("Installing dependencies")
        # Implement dependency installation logic here
        # ...
        logger.info("Dependency installation completed successfully.")

    elif args.command == "build":
        workspace = args.workspace or input("Enter workspace path: ")
        if not workspace:
            logger.error("Workspace path not provided for build command.")
            sys.exit(1)

        workspace = str(Path(workspace).expanduser())
        logger.info(f"Building workspace at '{workspace}'")
        build_workspace(workspace)
        logger.info("Workspace build completed successfully.")

    logger.info("arcscfg tool finished execution.")

if __name__ == "__main__":
    main()
