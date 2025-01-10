import os
import subprocess
import sys
import yaml
import logging
from pathlib import Path

from .workspace_validation import (
    validate_workspace_path,
    validate_workspace_config,
    validate_src_directory,
)
from .shell import run_command

# Initialize logger
logger = logging.getLogger("arcscfg")

def clone_repos(workspace: Path, workspace_config: Path):
    """Clone repos defined in the workspace config file to the ROS 2 workspace.

    Args:
        workspace (Path): The workspace directory.
        workspace_config (Path): The workspace configuration YAML file.
    """
    try:
        logger.info("Cloning repositories...")
        run_command(["vcs", "import", "--input", str(workspace_config), "src"],
                    cwd=str(workspace), verbose=True)
        logger.info("Repositories cloned successfully.")
    except subprocess.CalledProcessError:
        logger.error("Failed to clone repositories.")
        sys.exit(1)

def setup_workspace(workspace_path: str, workspace_config: str):
    """Set up a ROS 2 workspace by cloning repositories.

    Args:
        workspace_path (str): Path to the ROS 2 workspace.
        workspace_config (str): Path to the workspace configuration YAML file.
    """
    try:
        # Expand and validate workspace path
        workspace = Path(workspace_path).expanduser().resolve()
        workspace = validate_workspace_path(workspace)
        logger.debug(f"Validated workspace path: {workspace}")

        # Load and validate workspace configuration
        with open(workspace_config, "r") as f:
            config = yaml.safe_load(f)
        validate_workspace_config(config)
        logger.debug(f"Validated workspace configuration: {workspace_config}")

        # Validate/create src directory
        validate_src_directory(workspace)
        logger.debug(f"Validated 'src' directory in workspace: {workspace}")

        logger.info(f"Setting up workspace at '{workspace}' "
                    f"using config '{workspace_config}'")

        # Clone repositories
        clone_repos(workspace, Path(workspace_config))

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
