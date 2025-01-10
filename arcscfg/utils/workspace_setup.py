import os
import subprocess
import sys
import yaml
from pathlib import Path

from .workspace_validation import (
    validate_workspace_path,
    validate_workspace_config,
    validate_src_directory,
)

def clone_repos(workspace, workspace_config):
    """Clone repos defined in a workspace config file to a ROS 2 workspace."""
    subprocess.run(["vcs", "import", "--input", str(workspace_config), "src"],
                   cwd=workspace, check=True)

def setup_workspace(workspace, workspace_config):
    """Set up a ROS 2 workspace."""
    try:
        # Validate workspace path and config
        workspace = validate_workspace_path(workspace)

        # Load and validate workspace configuration
        with open(workspace_config, "r") as f:
            config = yaml.safe_load(f)
        validate_workspace_config(config)

        # Validate/create src directory
        validate_src_directory(workspace)

        print(f"Setting up workspace at '{workspace}' "
              f"using config '{workspace_config}'")

        # Clone repositories
        clone_repos(workspace, workspace_config)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
