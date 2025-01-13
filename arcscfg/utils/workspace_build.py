import subprocess
import sys
import logging
from pathlib import Path
from typing import Optional, List

from .workspace_setup_parser import parse_setup_bash
from .workspace_validation import (
    validate_workspace_path,
    validate_src_directory,
    verify_ros_setup,
    find_ros2_underlays
)
from .shell import (
    get_workspace_setup_file,
    source_setup_file,
    run_command
)

# Initialize logger
logger = logging.getLogger("arcscfg")


def prompt_for_underlay(underlays: List[Path],
                      default_underlay: Optional[Path] = None) -> Optional[Path]:
    """Prompt the user to select an underlay or enter a custom path, with an
    optional default.

    Args:
        underlays (List[Path]): List of available underlays.
        default_underlay (Optional[Path]): The default underlay to select if
    present.

    Returns:
        Optional[Path]: Selected or entered underlay path.
    """
    if not underlays:
        logger.warning("No underlays found. Proceeding without underlays.")
        return None

    print("\nAvailable underlays:")
    default_option = None
    for i, underlay in enumerate(underlays, start=1):
        if default_underlay and underlay == default_underlay:
            print(f"{i}: {underlay} (last used underlay)")
            default_option = i
        else:
            print(f"{i}: {underlay}")

    # Always add the custom underlay option at the end
    custom_option_number = len(underlays) + 1
    print(f"{custom_option_number}: Enter a custom underlay path")

    # Determine the default option index
    if default_underlay and default_underlay in underlays:
        default_option = underlays.index(default_underlay) + 1
    elif default_underlay and default_underlay not in underlays:
        # Add the default_underlay to the list
        underlays.append(default_underlay)
        print(f"{len(underlays)}: {default_underlay} (last used underlay)")
        custom_option_number = len(underlays) + 1
        print(f"{custom_option_number}: Enter a custom underlay path")
        default_option = len(underlays)
    else:
        default_option = custom_option_number  # Default to custom path

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
                print("Invalid input. Please enter a number corresponding "
                      "to the options.")
                continue

        if 1 <= choice_num <= len(underlays):
            selected_underlay = underlays[choice_num - 1]
            logger.debug(f"User selected underlay: {selected_underlay}")
            return selected_underlay
        elif choice_num == custom_option_number:
            # Allow user to enter a custom path
            custom_path = input(
                "Enter the path to the custom underlay: ").strip()
            if not custom_path:
                print("Please enter a valid existing path.")
                continue
            custom_underlay = Path(custom_path).expanduser().resolve()
            if not custom_underlay.exists():
                logger.error(
                    f"Provided underlay path does not exist: {custom_underlay}")
                print("Provided underlay path does not exist. "
                      "Please enter a valid path.")
                continue
            setup_file = get_workspace_setup_file(custom_underlay)
            if not setup_file or not setup_file.exists():
                logger.error(f"No setup file found in the custom underlay: "
                             f"{custom_underlay}")
                print(
                    "No valid setup file found in the provided underlay path.")
                continue
            logger.debug(f"User entered custom underlay: {custom_underlay}")
            return custom_underlay
        else:
            print("Invalid selection. Please choose a valid number.")


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

        # Determine the path to setup.bash
        setup_bash_path = workspace / "install" / "setup.bash"
        default_underlay_path_str = parse_setup_bash(setup_bash_path)
        default_underlay = (Path(default_underlay_path_str)
                            if default_underlay_path_str else None)

        # Find and set up underlays
        underlays = find_ros2_underlays([Path("/opt/ros"), Path.home()])

        # Remove duplicates and ensure all underlays are resolved
        underlays = list(set(underlays))

        # Pass the default_underlay to the prompt function
        underlay = prompt_for_underlay(underlays,
                                       default_underlay=default_underlay)

        if underlay:
            logger.info(f"Using underlay: {underlay}")
            setup_file = get_workspace_setup_file(underlay)
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
                logger.warning(
                    f"Setup file not found for underlay: {underlay}")

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
