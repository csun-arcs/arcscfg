import subprocess
import sys
import logging
from pathlib import Path
from typing import Optional, List

from .workspace_validation import (
    validate_workspace_path,
    validate_src_directory,
    verify_ros_setup,
    find_ros2_underlays
)
from .shell import (
    get_shell_setup_file,
    source_setup_file,
    run_command
)

# Initialize logger
logger = logging.getLogger("arcscfg")

def prompt_for_underlay(underlays: List[Path]) -> Optional[Path]:
    """Prompt the user to select an underlay or enter a custom path.

    Args:
        underlays (List[Path]): List of available underlays.

    Returns:
        Optional[Path]: Selected or entered underlay path.
    """
    if not underlays:
        logger.warning("No underlays found. Proceeding without underlays.")
        return None

    print("\nAvailable underlays:")
    for i, underlay in enumerate(underlays, start=1):
        print(f"{i}: {underlay}")

    print(f"{len(underlays)+1}: Enter a custom underlay path")

    while True:
        choice = input("Select an underlay (number): ").strip()
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(underlays):
                selected_underlay = underlays[choice_num - 1]
                logger.debug(f"User selected underlay: {selected_underlay}")
                return selected_underlay
            elif choice_num == len(underlays) + 1:
                # Allow user to enter a custom path
                custom_path = input(
                    "Enter the path to the custom underlay: ").strip()
                if not custom_path:
                    logger.error("No path entered for custom underlay.")
                    print("Please enter a valid existing path.")
                    continue
                custom_underlay = Path(custom_path).expanduser().resolve()
                if not custom_underlay.exists():
                    logger.error(f"Provided underlay path does not exist: "
                                 f"{custom_underlay}")
                    print("Provided underlay path does not exist. "
                          "Please enter a valid path.")
                    continue
                setup_file = get_shell_setup_file(custom_underlay)
                if not setup_file.exists():
                    logger.error(f"No setup file found in the custom underlay: "
                                 f"{custom_underlay}")
                    print("No valid setup file found in "
                          "the provided underlay path.")
                    continue
                logger.debug(f"User entered custom underlay: {custom_underlay}")
                return custom_underlay
            else:
                print("Invalid selection. Please choose a valid number.")
        except ValueError:
            print("Invalid input. "
                  "Please enter a number corresponding to the options.")

def build_workspace(workspace_path: str):
    """Build a ROS 2 workspace.

    Args:
        workspace_path (str): Path to the ROS 2 workspace.
    """
    try:
        # Validate workspace path
        workspace = Path(workspace_path).expanduser().resolve()
        workspace = validate_workspace_path(workspace)
        logger.debug(f"Validated workspace path for build: {workspace}")

        # Validate src directory
        src_dir = validate_src_directory(workspace)
        logger.debug(f"Validated 'src' directory in workspace: {workspace}")

        # Find and set up underlays
        underlays = find_ros2_underlays()
        underlay = prompt_for_underlay(underlays)

        if underlay:
            logger.info(f"Using underlay: {underlay}")
            setup_file = get_shell_setup_file(underlay)
            if setup_file:
                logger.debug(f"Sourcing setup file: {setup_file}")
                if source_setup_file(setup_file):
                    logger.info("Successfully sourced setup file.")
                    if not verify_ros_setup():
                        logger.warning(
                            "ROS environment may not be fully configured.")
                else:
                    logger.warning("Failed to source setup file.")
            else:
                logger.warning(f"Setup file not found for underlay: "
                               f"{underlay}")

        # Proceed with build
        logger.info("Starting workspace build using colcon...")
        run_command(["colcon", "build"], cwd=str(workspace), verbose=True)
        logger.info("Workspace build completed successfully.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error building workspace: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
