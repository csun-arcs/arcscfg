import subprocess
import sys
from pathlib import Path
from .workspace_validation import (
    validate_workspace_path,
    validate_src_directory,
    validate_ros_environment
)

def build_workspace(workspace_path):
    """Build a ROS 2 workspace."""
    try:
        # Validate ROS environment
        ros_distro = validate_ros_environment()

        # Validate workspace path
        workspace_path = validate_workspace_path(workspace_path)
        
        # Validate src directory
        src_dir = validate_src_directory(workspace_path)

        # Proceed with build
        subprocess.run(["colcon", "build"], cwd=workspace_path, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building workspace: {e}")
        sys.exit(1)
