import sys
import subprocess
import logging
from pathlib import Path
from .workspace_validation import (
    validate_workspace_path,
    validate_src_directory,
    verify_ros_setup
)
from .shell import (
    get_shell_setup_file,
    source_setup_file
)

# Initialize logger
logger = logging.getLogger("arcscfg")

def find_ros2_underlays():
    """Search for ROS 2 installations and workspaces."""
    underlays = []

    # Search for ROS 2 installations in /opt/ros
    ros2_installations = list(Path("/opt/ros").glob("*"))
    underlays.extend(ros2_installations)

    # Search for workspaces in the home directory
    home_workspaces = list(Path.home().glob("*/install/setup.bash"))
    underlays.extend([ws.parent.parent for ws in home_workspaces])

    logger.debug(f"Found underlays: {underlays}")
    return underlays

def prompt_for_underlay(underlays):
    """Prompt the user to select an underlay."""
    if not underlays:
        logger.warning("No underlays found.")
        return None

    print("Available underlays:")
    for i, underlay in enumerate(underlays):
        print(f"{i}: {underlay}")

    choice = input("Select an underlay (default: 0): ")
    if choice.strip():
        try:
            index = int(choice)
            if 0 <= index < len(underlays):
                return underlays[index]
        except (ValueError, IndexError):
            pass
    return underlays[0]

def build_workspace(workspace_path):
    """Build a ROS 2 workspace."""
    try:
        # Validate workspace path
        workspace_path = validate_workspace_path(workspace_path)
        logger.debug(f"Validated workspace path for build: {workspace_path}")

        # Validate src directory
        src_dir = validate_src_directory(workspace_path)
        logger.debug(
            f"Validated 'src' directory in workspace: {workspace_path}")

        # Find and set up underlays
        underlays = find_ros2_underlays()
        underlay = prompt_for_underlay(underlays)

        if underlay:
            logger.info(f"Using underlay: {underlay}")
            setup_file = get_shell_setup_file(underlay)
            if setup_file.exists():
                logger.debug(f"Sourcing setup file: {setup_file}")
                if source_setup_file(setup_file):
                    logger.info("Successfully sourced setup file.")
                    if not verify_ros_setup():
                        logger.warning(
                            "ROS environment may not be fully configured.")
                else:
                    logger.warning("Failed to source setup file.")
            else:
                logger.warning(f"Setup file not found: {setup_file}")

        # Proceed with build
        logger.info("Starting workspace build using colcon...")
        subprocess.run(["colcon", "build"], cwd=workspace_path, check=True)
        logger.info("Workspace build completed successfully.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error building workspace: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
