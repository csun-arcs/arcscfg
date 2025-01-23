import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger("arcscfg")


class Shell:
    @staticmethod
    def source_file(setup_file: Path) -> bool:
        """
        Source the specified file and update the current process environment.

        Args:
            setup_file (Path): Path to the file that should be sourced.

        Returns:
            bool: True if sourcing was successful, False otherwise.
        """
        shell = os.environ.get("SHELL", "/bin/bash")
        source_cmd = f"source {setup_file} && env"

        try:
            result = Shell.run_command(
                [shell, "-c", source_cmd], capture_output=True, verbose=False
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Error sourcing setup file '{setup_file}': {e.stderr.strip()}"
            )
            return False

        if result.returncode != 0:
            logger.error(
                f"Error sourcing setup file '{setup_file}': {result.stderr.strip()}"
            )
            return False

        # Update environment variables
        for line in result.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.strip().split("=", 1)
            os.environ[key] = value

        logger.debug(f"Successfully sourced file: {setup_file}")
        return True

    @staticmethod
    def run_command(
        command: Union[str, List[str]],
        cwd: Optional[str] = None,
        capture_output: bool = True,
        verbose: bool = False,
        shell: bool = False,
        text: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Execute a system command, log its output, and handle errors.

        Args:
            command (Union[str, List[str]]): The command and its arguments to execute.
            cwd (Optional[str]): The working directory in which to execute the command.
            capture_output (bool): Whether to capture the command's output.
            verbose (bool): Whether to log the command's output in real-time.
            shell (bool): Whether to execute the command through the shell.
            text (bool): If True, streams will be opened in text mode.

        Returns:
            subprocess.CompletedProcess: The result of the executed command.
        """
        logger.debug(f"Executing command: {command} in '{cwd}'")
        try:
            if verbose:
                # Enforce text=True when verbose to handle outputs as strings
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=shell,
                    text=True,  # Ensures outputs are strings
                )

                # Stream output to logger
                for stdout_line in iter(process.stdout.readline, ""):
                    if stdout_line:
                        logger.info(stdout_line.strip())
                for stderr_line in iter(process.stderr.readline, ""):
                    if stderr_line:
                        logger.error(stderr_line.strip())

                process.stdout.close()
                process.stderr.close()
                return_code = process.wait()

                if return_code != 0:
                    logger.error(f"Command exited with return code {return_code}")
                return subprocess.CompletedProcess(command, return_code)
            else:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=capture_output,
                    text=text,
                    shell=shell,
                    check=True,
                )
                logger.debug(f"Command output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Command stderr: {result.stderr}")
                return result

        except subprocess.CalledProcessError as e:
            logger.error(f"Command '{command}' failed with return code {e.returncode}")
            if e.stdout:
                logger.error(f"stdout: {e.stdout}")
            if e.stderr:
                logger.error(f"stderr: {e.stderr}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error while running command: {command}")
            raise
