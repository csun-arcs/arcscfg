import argparse
import sys
from pathlib import Path

# Import command classes
from arcscfg.commands.build import BuildCommand
from arcscfg.commands.config import ConfigCommand
from arcscfg.commands.install import InstallCommand
from arcscfg.commands.setup import SetupCommand
from arcscfg.commands.update import UpdateCommand
from arcscfg.utils.logger import Logger
from arcscfg.utils.backer_upper import BackerUpper
from arcscfg.utils.user_prompter import UserPrompter


def main():
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description="CSUN ARCS Configurator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Global arguments
    parser.add_argument(
        "-v",
        "--verbosity",
        choices=["debug", "info", "warning", "error", "critical", "silent"],
        default="info",
        help="Set the logging verbosity level.",
    )
    parser.add_argument(
        "-lfp",
        "--log-file-path",
        default=None,
        help=(
            "Path to log file/directory. If None, system default location is "
            "selected."
        ),
    )
    parser.add_argument(
        "-lms",
        "--log-max-size",
        type=int,
        default=5 * 1024 * 1024,  # 5 MB
        help="Maximum log file size (in bytes) before rotation.",
    )
    parser.add_argument(
        "-lbc",
        "--log-backup-count",
        type=int,
        default=5,
        help="Number of backup log files to keep.",
    )
    parser.add_argument(
        "-bd",
        "--backup-dir",
        type=str,
        default=".arcscfg_backups",
        help="Directory name where backups will be stored relative to each file's location.",
    )
    parser.add_argument(
        "-bkc",
        "--backup-count",
        type=int,
        default=50,
        help="Number of backup copies to retain per file.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        "--assume-yes",
        action="store_true",
        help="Assume yes for all yes/no prompts and use default options otherwise.",
    )
    parser.add_argument(
        "-d",
        "--default",
        "--assume-default",
        action="store_true",
        help="Assume default option for all prompts (overrides --assume-yes).",
    )
    parser.add_argument(
        "-n",
        "--no",
        "--assume-no",
        action="store_true",
        help=("Assume no for all yes/no prompts and use default options otherwise "
              "(overrides both --assume-yes and --assume-default)."),
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="Commands",
        dest="command",
        description="Available commands",
        help="Additional help",
    )
    subparsers.required = True  # Ensure that a command is provided

    ### 1. Install Command ###
    install_parser = subparsers.add_parser(
        "install",
        description="Install ROS 2, dependencies, etc.",
        help="Install ROS2, dependencies, etc.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Command-specific arguments
    install_parser.add_argument(
        "-ir",
        "--install-ros2",
        action="store_true",
        help="Automate the installation of ROS 2.",
    )
    install_parser.add_argument(
        "-id",
        "--install-deps",
        action="store_true",
        help="Install dependencies.",
    )
    install_parser.add_argument(
        "-rd",
        "--ros-distro",
        choices=[
            "ardent",
            "bouncy",
            "crystal",
            "dashing",
            "eloquent",
            "foxy",
            "galactic",
            "humble",
            "iron",
            "jazzy",
            "rolling",
        ],
        help="ROS 2 distribution to install (e.g., 'iron', 'jazzy').",
    )
    install_parser.add_argument(
        "-rswl",
        "--ros-source-workspace-path",
        default="${HOME}/ros2_jazzy",
        help=(
            "Path a ROS 2 source workspace directory where ROS 2 source"
            "repositories should be cloned to when building ROS 2 from source."
        ),
    )
    install_parser.add_argument(
        "-rsr",
        "--ros-source-ref",
        default="release-jazzy-20240523",
        help=(
            "Branch or tag reference for ROS 2 source repositories.  "
        ),
    )
    install_parser.add_argument(
        "-df",
        "--dependency-file",
        help=(
            "Dependency config file. Select from available configs or "
            "provide dependency config path."
        ),
    )
    install_parser.add_argument(
        "-pim",
        "--pip-install-method",
        choices=["user", "pipx", "venv"],
        default="pipx",
        help=(
            "Method to install pip packages: 'user' installs with '--user', "
            "'pipx' uses pipx, 'venv' uses a virtual environment."
        ),
    )
    install_parser.set_defaults(func=InstallCommand)

    ### 2. Config Command ###
    config_parser = subparsers.add_parser(
        "config",
        description="Configure dotfiles, git hooks, etc.",
        help="Configure dotfiles, git hooks, etc.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Command-specific arguments
    config_parser.add_argument(
        "-w",
        "--workspace",
        help="ROS 2 workspace path.",
    )
    config_parser.set_defaults(func=ConfigCommand)

    ### 3. Setup Command ###
    setup_parser = subparsers.add_parser(
        "setup",
        description="Set up ROS 2 workspaces using workspace configuration files.",
        help="Set up ROS 2 workspaces using workspace configuration files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Command-specific arguments
    setup_parser.add_argument(
        "-wc",
        "--workspace-config",
        help=(
            "Workspace config. Select from available configs or "
            "provide workspace config path."
        ),
    )
    setup_parser.add_argument(
        "-w",
        "--workspace",
        help="ROS 2 workspace path.",
    )
    setup_parser.add_argument(
        "-pdf",
        "--package-dependency-files",
        nargs="*",
        default=["dependencies.repos", "dependencies.rosinstall"],
        help=(
            "Dependency file names to search for within packages."
        ),
    )
    setup_parser.add_argument(
        "-rs",
        "--recursive-search",
        action="store_true",
        help="Enable recursive search for dependency files within all subdirectories of the workspace.",
    )
    setup_parser.add_argument(
        "-mr",
        "--max-retries",
        type=int,
        default=2,
        help="Set the maximum number of times vcs should retry commands on failure.",
    )
    setup_parser.set_defaults(func=SetupCommand)

    ### 4. Build Command ###
    build_parser = subparsers.add_parser(
        "build",
        description="Build ROS 2 workspaces.",
        help="Build ROS 2 workspaces.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Command-specific arguments
    build_parser.add_argument(
        "-w",
        "--workspace",
        help="ROS 2 workspace path.",
    )
    build_parser.add_argument(
        "-u",
        "--underlay",
        help="ROS 2 underlay path to use during build.",
    )
    build_parser.set_defaults(func=BuildCommand)

    ### 5. Update Command ###
    update_parser = subparsers.add_parser(
        "update",
        description="Update ROS 2 workspace repositories.",
        help="Update ROS 2 workspace repositories.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Command-specific arguments
    update_parser.add_argument(
        "-w",
        "--workspace",
        help="ROS 2 workspace path.",
    )
    update_parser.set_defaults(func=UpdateCommand)

    # Parse the arguments
    args = parser.parse_args()

    # Initialize logger
    logger = Logger(
        verbosity=args.verbosity,
        log_file_path=Path(args.log_file_path) if args.log_file_path else None,
        max_bytes=args.log_max_size,
        backup_count=args.log_backup_count,
    )

    # Initialize file backer-upper
    backer_upper = BackerUpper(
        backup_dir=args.backup_dir,
        backup_count=args.backup_count,
        logger=logger,  # Utilize the existing Logger
    )

    # Initialize user prompter
    if args.no:
        setattr(args, "assume", "no")
        user_prompter = UserPrompter(assume="no")
    elif args.default:
        setattr(args, "assume", "default")
        user_prompter = UserPrompter(assume="default")
    elif args.yes:
        setattr(args, "assume", "yes")
        user_prompter = UserPrompter(assume="yes")
    else:
        setattr(args, "assume", None)
        user_prompter = UserPrompter()

    logger.info("Starting arcscfg tool")

    # Instantiate and execute the selected command
    try:
        command_class = args.func
        command_instance = command_class(args, logger, backer_upper, user_prompter)
        command_instance.execute()
    except AttributeError:
        # This should not happen as subparsers are required
        parser.print_help()
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

    logger.info("arcscfg tool finished execution.")


if __name__ == "__main__":
    main()
