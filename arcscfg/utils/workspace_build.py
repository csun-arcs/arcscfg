import subprocess
import sys
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

def find_ros2_underlays():
    """Search for ROS 2 installations and workspaces."""
    underlays = []

    # Search for ROS 2 installations in /opt/ros
    ros2_installations = list(Path("/opt/ros").glob("*"))
    underlays.extend(ros2_installations)

    # Search for workspaces in the home directory
    home_workspaces = list(Path.home().glob("*/install/setup.bash"))
    underlays.extend([ws.parent.parent for ws in home_workspaces])

    return underlays

def prompt_for_underlay(underlays):
    """Prompt the user to select an underlay."""
    print("Available underlays:")
    for i, underlay in enumerate(underlays):
        print(f"{i}: {underlay}")

    choice = input("Select an underlay (default: 0): ")
    if choice:
        return underlays[int(choice)]
    return underlays[0]

def build_workspace(workspace_path):
    """Build a ROS 2 workspace."""
    try:
        # Validate workspace path
        workspace_path = validate_workspace_path(workspace_path)

        # Validate src directory
        src_dir = validate_src_directory(workspace_path)

        # Find and set up underlays
        underlays = find_ros2_underlays()
        underlay = prompt_for_underlay(underlays)

        if underlay:
            print(f"Using underlay: {underlay}")
            setup_file = get_shell_setup_file(underlay)
            if setup_file.exists():
                print(f"Sourcing {setup_file}")
                if source_setup_file(setup_file):
                    print("Successfully sourced setup file")
                    if not verify_ros_setup():
                        print("Warning: ROS environment may not be fully configured")
                else:
                    print("Warning: Failed to source setup file")
            else:
                print(f"Warning: Setup file not found: {setup_file}")

        # Proceed with build
        subprocess.run(["colcon", "build"], cwd=workspace_path, check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error building workspace: {e}")
        sys.exit(1)
