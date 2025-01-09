import subprocess
import sys

def build_workspace(workspace_path):
    """Build a ROS 2 workspace using colcon."""
    try:
        subprocess.run(["colcon", "build"], cwd=workspace_path, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building workspace: {e}")
        sys.exit(1)
