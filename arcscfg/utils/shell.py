import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("arcscfg")

def get_workspace_setup_file(workspace_path: Path) -> Optional[Path]:
    """
    Determine the appropriate setup file based on the user's shell for a given
    workspace.

    Args:
        workspace_path (Path): The path to the workspace or underlay.

    Returns:
        Optional[Path]: Path to the setup file if found, else None.
    """
    # Get user's current shell
    shell = os.environ.get('SHELL', '/bin/bash').lower()

    # Map shells to their setup files
    setup_files = {
        'zsh': 'setup.zsh',
        'bash': 'setup.bash',
        'sh': 'setup.sh'
    }

    # Extract shell name (e.g., 'bash' from '/bin/bash')
    shell_name = Path(shell).name
    # Default to bash if unknown
    setup_file_name = setup_files.get(shell_name, 'setup.bash')

    logger.debug(
        f"Detected shell: {shell_name}, looking for '{setup_file_name}'")

    # Possible setup file locations
    possible_paths = [
        # For system installs like /opt/ros/jazzy/setup.bash
        workspace_path / setup_file_name,
        # For colcon workspaces
        workspace_path / 'install' / setup_file_name,
        # For catkin workspaces
        workspace_path / 'devel' / setup_file_name
    ]

    # Try each possible path
    for path in possible_paths:
        if path.exists():
            logger.debug(f"Found setup file: {path}")
            return path

    logger.warning(f"No setup file found for shell '{shell_name}' "
                   f"in workspace '{workspace_path}'.")
    return None

def source_file(setup_file: Path) -> bool:
    """
    Source the specified file and update the current process environment.

    Args:
        setup_file (Path): Path to the file that should be sourced.

    Returns:
        bool: True if sourcing was successful, False otherwise.
    """
    shell = os.environ.get('SHELL', '/bin/bash')
    source_cmd = f"source {setup_file} && env"

    try:
        result = run_command(
            [shell, '-c', source_cmd],
            capture_output=True,
            verbose=False
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error sourcing setup file '{setup_file}': {e.stderr.strip()}")
        return False

    if result.returncode != 0:
        logger.error(f"Error sourcing setup file '{setup_file}': {result.stderr.strip()}")
        return False

    # Update environment variables
    for line in result.stdout.splitlines():
        if '=' not in line:
            continue
        key, value = line.strip().split('=', 1)
        os.environ[key] = value

    logger.debug(f"Successfully sourced file: {setup_file}")
    return True

def run_command(command: List[str], cwd: Optional[str] = None, capture_output: bool = True,
              verbose: bool = False) -> subprocess.CompletedProcess:
    """
    Execute a system command, log its output, and handle errors.

    Args:
        command (List[str]): The command and its arguments to execute.
        cwd (Optional[str]): The working dir in which to execute the command.
        capture_output (bool): Whether to capture the command's output.
        verbose (bool): Whether to log the command's output in real-time.

    Returns:
        subprocess.CompletedProcess: The result of the executed command.
    """
    logger.debug(f"Executing command: {' '.join(command)} in '{cwd}'")
    try:
        if verbose:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Stream output to logger
            for stdout_line in iter(process.stdout.readline, ""):
                logger.info(stdout_line.strip())
            for stderr_line in iter(process.stderr.readline, ""):
                logger.error(stderr_line.strip())

            process.stdout.close()
            process.stderr.close()
            return_code = process.wait()

            if return_code != 0:
                logger.error(f"Command {' '.join(command)} exited "
                             f"with {return_code}")
            return subprocess.CompletedProcess(command, return_code)

        else:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=True
            )
            logger.debug(f"Command output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr}")
            return result

    except subprocess.CalledProcessError as e:
        logger.error(f"Command '{' '.join(e.cmd)}' failed "
                     f"with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"stderr: {e.stderr}")
        raise
    except Exception as e:
        logger.exception(
            f"Unexpected error while running command: {' '.join(command)}")
        raise
