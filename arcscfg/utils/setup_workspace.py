# arcscfg/arcscfg/utils/setup_workspace.py

import os
import subprocess
import sys
from pathlib import Path

def create_workspace(workspace_path):
    """Create a ROS 2 workspace."""
    Path(os.path.join(workspace_path, "src")).mkdir(parents=True, exist_ok=True)

def clone_repos(workspace_config, workspace_path):
    """Clone repos defined in a workspace config file to a ROS 2 workspace."""
    subprocess.run(["vcs", "import", "--input", str(workspace_config), "src"], cwd=workspace_path, check=True)

def build_workspace(workspace_path):
    """Build a ROS 2 workspace."""
    subprocess.run(["colcon", "build"], cwd=workspace_path, check=True)

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
        print(f"{i + 1}: {underlay}")

    choice = input("Select an underlay (or press Enter to skip): ")
    if choice:
        return underlays[int(choice) - 1]
    return None

def setup_workspace(workspace_config):
    """Set up a ROS 2 workspace."""
    try:
        # Ensure the workspace_config path is absolute
        workspace_config = Path(workspace_config).resolve()
        if not workspace_config.exists():
            print(f"Error: Workspace configuration file not found: {workspace_config}")
            sys.exit(1)

        # Derive workspace name from the YAML file name
        workspace_name = Path(workspace_config).stem + "_ws"
        workspace_name = input(f"Enter workspace name (default: {workspace_name}): ") or workspace_name
        workspace_path = Path.home() / workspace_name

        # Find and prompt for underlays
        underlays = find_ros2_underlays()
        underlay = prompt_for_underlay(underlays)

        # Set up the underlay
        if underlay:
            print(f"Using underlay: {underlay}")
            # Add logic to source the underlay's setup.bash
        else:
            print("No underlay selected.")

        # Create and initialize the workspace
        create_workspace(workspace_path)

        # Proceed with cloning repositories
        clone_repos(workspace_config, workspace_path)

        # Build the workspace
        build_workspace(workspace_path)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
