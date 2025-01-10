import os
import yaml
import logging
from pathlib import Path
from typing import List

# Initialize logger
logger = logging.getLogger("arcscfg")

def validate_workspace_path(workspace_path: Path) -> Path:
    """Validate that the workspace path is writable.

    Args:
        workspace_path (Path): The path to validate.

    Returns:
        Path: The validated workspace path.

    Raises:
        PermissionError: If the path is not writable.
    """
    if workspace_path.exists():
        if not os.access(workspace_path, os.W_OK):
            raise PermissionError(f"No write permission for {workspace_path}")
    else:
        # Attempt to create the workspace directory
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created workspace directory: {workspace_path}")
        except Exception as e:
            raise PermissionError(
                f"Cannot create workspace directory: {workspace_path}") from e
    return workspace_path

def validate_workspace_config(config: dict) -> dict:
    """Validate workspace configuration structure.

    Args:
        config (dict): The workspace configuration.

    Returns:
        dict: The validated configuration.

    Raises:
        ValueError: If the configuration is invalid.
    """
    if not isinstance(config, dict):
        raise ValueError(
            "Invalid workspace configuration format; expected a dictionary.")
    if "repositories" not in config:
        raise ValueError("No 'repositories' specified in configuration.")
    if not isinstance(config["repositories"], dict):
        raise ValueError("'repositories' should be a dictionary "
                         "of repository configurations.")
    for repo_name, repo_cfg in config["repositories"].items():
        if not isinstance(repo_cfg, dict):
            raise ValueError(
                "Each repository configuration should be a dictionary.")
        if "type" not in repo_cfg or "url" not in repo_cfg or "version" not in repo_cfg:
            raise ValueError(
                "Each repository must have 'type', 'url' and 'version' fields.")
    return config

def validate_src_directory(workspace_path: Path) -> Path:
    """Validate that the workspace has a 'src' directory.

    Args:
        workspace_path (Path): The workspace path.

    Returns:
        Path: The 'src' directory path.

    Raises:
        ValueError: If the 'src' path exists but is not a directory.
    """
    src_dir = workspace_path / "src"
    if not src_dir.exists():
        src_dir.mkdir(parents=True)
        logger.debug(f"Created 'src' directory at {src_dir}")
    elif not src_dir.is_dir():
        raise ValueError(f"'{src_dir}' exists but is not a directory")
    return src_dir

def verify_ros_setup() -> bool:
    """Verify that ROS 2 environment variables are set correctly.

    Returns:
        bool: True if all required ROS 2 environment variables are present,
    False otherwise.
    """
    required_vars = [
        'ROS_DISTRO',
        'ROS_VERSION',
        'AMENT_PREFIX_PATH',
        'CMAKE_PREFIX_PATH',
        'COLCON_PREFIX_PATH'
    ]

    missing_vars = [var for var in required_vars if var not in os.environ]

    if missing_vars:
        logger.warning("Some ROS 2 environment variables are missing:")
        for var in missing_vars:
            logger.warning(f"  - {var}")
        return False
    return True

def find_available_workspaces(home_dir: Path = Path.home()) -> List[Path]:
    """Find available ROS 2 workspaces in the home directory.

    Args:
        home_dir (Path, optional): The home directory to search.
    Defaults to Path.home().

    Returns:
        List[Path]: List of workspace paths.
    """
    workspaces = []
    # Define naming pattern (e.g., workspaces end with '_ws')
    naming_pattern = "*_ws"
    setup_files = [
        "install/setup.bash",
        "install/setup.zsh",
        "install/setup.sh",
        "devel/setup.bash",
        "devel/setup.zsh",
        "devel/setup.sh"
    ]

    logger.debug(f"Searching for available workspaces in {home_dir} "
                 f"with pattern '{naming_pattern}'")

    for dir in home_dir.glob(naming_pattern):
        if dir.is_dir():
            # Check if 'src' directory exists
            src_dir = dir / "src"
            if src_dir.exists() and src_dir.is_dir():
                workspaces.append(dir)
                logger.debug(f"Found workspace with 'src' directory: {dir}")
                continue  # No need to check setup files if 'src' exists

            # Check for setup files
            for setup_file in setup_files:
                setup_path = dir / setup_file
                if setup_path.exists():
                    workspaces.append(dir)
                    logger.debug(f"Found workspace: {dir}")
                    break  # No need to check other setup files

    logger.debug(f"Total workspaces found: {len(workspaces)}")
    return workspaces

def find_ros2_underlays(search_dirs: List[Path] = None) -> List[Path]:
    """Search for ROS 2 installs and workspaces outside of '~/workspace_ws'.

    Args:
        search_dirs (List[Path], optional): Directories to search.
            Defaults to [Path("/opt/ros")].

    Returns:
        List[Path]: List of paths to ROS 2 underlays.
    """
    if search_dirs is None:
        search_dirs = [Path("/opt/ros")]

    underlays = []
    setup_files = ["setup.bash", "setup.zsh", "setup.sh"]

    for search_dir in search_dirs:
        if not search_dir.exists():
            logger.debug(f"Search directory does not exist: {search_dir}")
            continue

        logger.debug(f"Searching in directory: {search_dir}")
        # Iterate over immediate subdirectories (e.g., /opt/ros/jazzy)
        for subdir in search_dir.iterdir():
            if subdir.is_dir():
                # Check for setup files in the subdir
                for setup_file in setup_files:
                    setup_path = subdir / setup_file
                    if setup_path.exists():
                        underlays.append(subdir)
                        logger.debug(f"Found underlay: {subdir}")
                        break  # No need to check other setup files
                else:
                    # For workspaces, setup files might be in
                    # 'install' or 'devel' directories
                    for install_type in ['install', 'devel']:
                        install_dir = subdir / install_type
                        if install_dir.exists() and install_dir.is_dir():
                            for setup_file in setup_files:
                                setup_path = install_dir / setup_file
                                if setup_path.exists():
                                    underlays.append(subdir)
                                    logger.debug(f"Found underlay in "
                                                 f"{install_type}: {subdir}")
                                    break
                            else:
                                continue
                            break

    logger.debug(f"Total underlays found: {len(underlays)}")
    return underlays

def infer_default_workspace_path(workspace_config: Path) -> Path:
    """
    Infer a default workspace path based on the workspace config.

    For example, if the config is 'cohort.yaml', suggest '~/cohort_ws'.

    Args:
        workspace_config (Path): The path to the workspace configuration file.

    Returns:
        Path: The inferred default workspace path.
    """
    config_name = workspace_config.stem  # e.g., 'cohort' from 'cohort.yaml'
    suggested_name = f"{config_name}_ws"  # e.g., 'cohort_ws'
    default_workspace = Path.home() / suggested_name
    logger.debug(f"Inferred default workspace path: {default_workspace}")
    return default_workspace
