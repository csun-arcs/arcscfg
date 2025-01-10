import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("arcscfg")

def get_shell_setup_file(underlay_path: Path) -> Optional[Path]:
    """Determine appropriate setup file based on user's shell.

    Args:
        underlay_path (Path): The path to the underlay.

    Returns:
        Optional[Path]: Path to the setup file if found, else None.
    """
    # Get user's current shell
    shell = os.environ.get('SHELL', '').lower()

    # Map shells to their setup files
    setup_files = {
        'zsh': 'setup.zsh',
        'bash': 'setup.bash',
        'sh': 'setup.sh'
    }

    # Get the appropriate setup file name
    shell_name = Path(shell).name
    # Default to bash if unknown
    setup_file = setup_files.get(shell_name, 'setup.bash')

    # Possible setup file locations
    possible_paths = [
        # For system installs like /opt/ros/jazzy/setup.bash
        underlay_path / setup_file,
        # For colcon workspaces
        underlay_path / 'install' / setup_file,
        # For catkin workspaces
        underlay_path / 'devel' / setup_file
    ]

    # Try each possible path
    for path in possible_paths:
        if path.exists():
            logger.debug(f"Found setup file: {path}")
            return path

    logger.warning(f"No setup file found for shell '{shell_name}' "
                   f"in underlay '{underlay_path}'.")
    return None

def source_setup_file(setup_file: Path) -> bool:
    """Source the appropriate setup file and update environment.

    Args:
        setup_file (Path): Path to the setup file.

    Returns:
        bool: True if sourcing was successful, False otherwise.
    """
    try:
        # Get the current shell
        shell = os.environ.get('SHELL', '/bin/bash')

        # Create the source command
        source_cmd = f"source {setup_file} && env"

        # Execute the source command and capture environment
        proc = subprocess.Popen(
            [shell, '-c', source_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            logger.error(f"Error sourcing setup file: {stderr.strip()}")
            return False

        # Parse the environment variables
        for line in stdout.splitlines():
            if '=' not in line:
                continue
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

        logger.debug(f"Successfully sourced setup file: {setup_file}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Error sourcing setup file: {e.stderr.strip()}")
        return False

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
