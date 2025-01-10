import os
import yaml
from pathlib import Path

def validate_workspace_path(workspace_path):
    """Validate that the workspace path is writable."""
    path = Path(workspace_path)
    if path.exists() and not os.access(path, os.W_OK):
        raise PermissionError(f"No write permission for {path}")
    return path

def validate_workspace_config(config):
    """Validate workspace configuration structure."""
    if not isinstance(config, dict):
        raise ValueError("Invalid workspace configuration format")
    if "repositories" not in config:
        raise ValueError("No repositories specified in configuration")
    return config

def validate_src_directory(workspace_path):
    """Validate that the workspace has a src directory."""
    src_dir = workspace_path / "src"
    if not src_dir.exists():
        src_dir.mkdir(parents=True)
    elif not src_dir.is_dir():
        raise ValueError(f"'{src_dir}' exists but is not a directory")
    return src_dir

def validate_ros_environment():
    """Validate that ROS 2 is installed and sourced."""
    if "ROS_DISTRO" not in os.environ:
        raise EnvironmentError("ROS 2 environment not sourced")
    return os.environ["ROS_DISTRO"]
