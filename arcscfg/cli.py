import argparse
import sys
from pathlib import Path

from arcscfg.commands.build import BuildCommand
from arcscfg.commands.install import InstallCommand
from arcscfg.commands.setup import SetupCommand
from arcscfg.commands.update import UpdateCommand
from arcscfg.utils.logger import Logger


def main():
    parser = argparse.ArgumentParser(description="ARCS Environment Configurator")
    parser.add_argument(
        "command",
        choices=["install", "setup", "build", "update"],
        help="Command to execute",
    )
    parser.add_argument("-w", "--workspace", help="ROS 2 workspace path.")
    parser.add_argument(
        "-wc",
        "--workspace-config",
        help=(
            "Workspace config. Select from available configs or "
            "provide workspace config path."
        ),
    )
    parser.add_argument(
        "-df",
        "--dependency-file",
        help=(
            "Dependency config file. Select from available configs or "
            "provide dependency config path."
        ),
    )
    parser.add_argument(
        "-pim",
        "--pip-install-method",
        choices=["user", "pipx", "venv"],
        default="user",
        help=(
            "Method to install pip packages: 'user' installs with '--user', "
            "'pipx' uses pipx, 'venv' uses a virtual environment. "
            "Default is 'user'."
        ),
    )
    parser.add_argument(
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
        default="jazzy",
        help=(
            "ROS 2 distribution to install (e.g., 'iron', 'jazzy', 'rolling'). "
            "Default: 'jazzy'."
        ),
    )
    parser.add_argument(
        "-ir",
        "--install-ros2",
        action="store_true",
        help="Automate the installation of ROS 2.",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        choices=["debug", "info", "warning", "error", "critical", "silent"],
        default="info",
        help="Set the logging verbosity level. Default: info.",
    )
    parser.add_argument(
        "-lfp",
        "--log-file-path",
        default=None,
        help=(
            "Path to log file/directory. If None, system default location is "
            "selected. Default: None."
        ),
    )
    parser.add_argument(
        "-lms",
        "--log-max-size",
        type=int,
        default=5 * 1024 * 1024,  # 5 MB
        help="Maximum log file size in bytes before rotation. Default is 5MB.",
    )
    parser.add_argument(
        "-lbc",
        "--log-backup-count",
        type=int,
        default=5,
        help="Number of backup log files to keep. Default is 5.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        "--assume-yes",
        action="store_true",
        help="Assume yes to all prompts and use default options.",
    )

    args = parser.parse_args()

    # Set up logging
    logger = Logger(
        verbosity=args.verbosity,
        log_file_path=Path(args.log_file_path) if args.log_file_path else None,
        max_bytes=args.log_max_size,
        backup_count=args.log_backup_count,
    )

    logger.info("Starting arcscfg tool")

    # Map command names to classes
    command_classes = {
        "setup": SetupCommand,
        "install": InstallCommand,
        "build": BuildCommand,
        "update": UpdateCommand,
    }

    command_class = command_classes.get(args.command)
    if not command_class:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)

    # Instantiate and execute the command
    command = command_class(args, logger)
    command.execute()

    logger.info("arcscfg tool finished execution.")


if __name__ == "__main__":
    main()
