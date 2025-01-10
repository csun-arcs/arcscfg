import os
import subprocess
from pathlib import Path

def get_shell_setup_file(underlay_path):
    """Determine appropriate setup file based on user's shell."""
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
    setup_file = setup_files.get(shell_name, 'setup.bash')

    # Possible setup file locations
    possible_paths = [
        Path(underlay_path) / setup_file,  # For system installs like /opt/ros/jazzy
        Path(underlay_path) / 'install' / setup_file,  # For colcon workspaces
        Path(underlay_path) / 'devel' / setup_file,  # For catkin workspaces
    ]

    # Try each possible path
    for path in possible_paths:
        if path.exists():
            return path

    # If no setup file found, return the default path
    return possible_paths[0]

def source_setup_file(setup_file):
    """Source the appropriate setup file and update environment."""
    try:
        # Get the current shell
        shell = os.environ.get('SHELL', '/bin/bash')

        # Create the source command
        source_cmd = f"source {setup_file} && env"

        # Execute the source command and capture environment
        proc = subprocess.Popen(
            [shell, '-c', source_cmd],
            stdout=subprocess.PIPE,
            universal_newlines=True
        )

        # Parse the environment variables
        for line in proc.stdout:
            if '=' not in line:
                continue
            key, value = line.rstrip().split('=', 1)
            os.environ[key] = value

        proc.communicate()

        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, source_cmd)

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error sourcing setup file: {e}")
        return False
