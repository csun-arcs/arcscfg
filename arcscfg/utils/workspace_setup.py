import os
import subprocess
import sys
import yaml
from pathlib import Path

from .workspace_validation import (
    validate_workspace_path,
    validate_workspace_config,
    validate_src_directory,
    validate_ros_environment
)

def create_workspace(workspace):
    """Create a ROS 2 workspace."""
    Path(os.path.join(workspace, "src")).mkdir(parents=True, exist_ok=True)

def clone_repos(workspace, workspace_config):
    """Clone repos defined in a workspace config file to a ROS 2 workspace."""
    subprocess.run(["vcs", "import", "--input", str(workspace_config), "src"],
                   cwd=workspace, check=True)

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

def setup_workspace(workspace, workspace_config):
    """Set up a ROS 2 workspace."""
    try:
        # Validate ROS environment
        ros_distro = validate_ros_environment()

        # Ensure the workspace_config path is absolute
        workspace_config = Path(workspace_config).resolve()
        if not workspace_config.exists():
            print(f"Error: Workspace configuration file not found: {workspace_config}")
            sys.exit(1)

        # Validate workspace path
        workspace = validate_workspace_path(workspace)
        print(f"Setting up workspace at '{workspace}' using config '{workspace_config}'")

        # Load and validate workspace configuration
        with open(workspace_config, "r") as f:
            config = yaml.safe_load(f)
        validate_workspace_config(config)

        # Validate/create src directory
        validate_src_directory(workspace)

        # Find and prompt for underlays
        underlays = find_ros2_underlays()
        underlay = prompt_for_underlay(underlays)

        # Set up the underlay
        if underlay:
            print(f"Using underlay: {underlay}")
            # Add logic to source the underlay's setup.bash

        # Proceed with cloning repositories
        clone_repos(workspace, workspace_config)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
