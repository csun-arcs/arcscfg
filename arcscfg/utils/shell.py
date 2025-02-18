import logging
import os
import subprocess
import sys
import threading
import itertools
import time
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger("arcscfg")


class Spinner:
    """A simple CLI spinner to indicate progress while a command is executing."""
    def __init__(self, message: str = ""):
        self.spinner = itertools.cycle(['|', '/', '-', '\\'])
        self.running = False
        self.thread = None
        self.message = message

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while self.running:
            sys.stderr.write(f"\r{self.message}{next(self.spinner)}")
            sys.stderr.flush()
            time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        # Clear the spinner line
        sys.stderr.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stderr.flush()


class Shell:
    @staticmethod
    def source_file(setup_file: Path, shell_executable: Optional[str] = None) -> bool:
        """
        Source the specified setup file using the chosen shell and update the current environment.

        Args:
            setup_file (Path): Path to the setup file to be sourced.
            shell_executable (Optional[str]): Path to the shell executable. Defaults to user's shell.

        Returns:
            bool: True if sourcing was successful, False otherwise.
        """
        shell = shell_executable or os.environ.get("SHELL", "/bin/bash")
        source_cmd = f"source {setup_file} && env"

        try:
            result = Shell.run_command(
                command=[shell, "-c", source_cmd],
                capture_output=True,
                verbose=False,
                shell=False,  # Already specifying shell in command
                executable=shell,
                text=True,
                timeout=60,  # Optional: Set a timeout if needed
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Error sourcing setup file '{setup_file}': {e.stderr.strip()}")
            return False

        if result.returncode != 0:
            logger.error(f"Error sourcing setup file '{setup_file}': {result.stderr.strip()}")
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
        executable: Optional[str] = None,
        text: bool = True,
        timeout: Optional[int] = None,  # Timeout in seconds
    ) -> subprocess.CompletedProcess:
        """
        Execute a system command with optional shell specification, timeout, and display a spinner while running.

        Args:
            command (Union[str, List[str]]): The command and its arguments to execute.
            cwd (Optional[str]): The working directory in which to execute the command.
            capture_output (bool): Whether to capture the command's output.
            verbose (bool): Whether to log the command's output in real-time.
            shell (bool): Whether to execute the command through the shell.
            executable (Optional[str]): Path to the shell executable to use. Defaults to user's shell.
            text (bool): If True, streams will be opened in text mode.
            timeout (Optional[int]): Maximum time (in seconds) to allow the command to run before terminating.

        Returns:
            subprocess.CompletedProcess: The result of the executed command.
        """
        if shell and not executable:
            # Default to user's shell
            executable = os.environ.get("SHELL", "/bin/bash")

        spinner = Spinner()
        if verbose:
            spinner.start()

        try:
            if isinstance(command, list):
                cmd = command
                cmd_str = ' '.join(command)
            else:
                cmd = [command]
                cmd_str = command

            if verbose:
                # Execute the command and stream output in real-time
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE if capture_output else None,
                    stderr=subprocess.PIPE if capture_output else None,
                    shell=shell,
                    executable=executable,
                    text=text,
                )

                # Stream output to logger
                if capture_output and process.stdout and process.stderr:
                    def stream_output(pipe, log_method):
                        for line in iter(pipe.readline, ''):
                            if line:
                                log_method(line.strip())
                        pipe.close()

                    # Change logging level for stderr to WARNING
                    stdout_thread = threading.Thread(target=stream_output, args=(process.stdout, logger.debug))
                    stderr_thread = threading.Thread(target=stream_output, args=(process.stderr, logger.warning))

                    stdout_thread.start()
                    stderr_thread.start()

                    try:
                        # Wait for process to complete with timeout
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        spinner.stop()  # Stop spinner before logging timeout
                        stdout_thread.join()
                        stderr_thread.join()
                        logger.error(f"Command '{cmd_str}' timed out after {timeout} seconds.")
                        raise

                    stdout_thread.join()
                    stderr_thread.join()

                else:
                    try:
                        # Wait for process to complete with timeout
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        spinner.stop()  # Stop spinner before logging timeout
                        logger.error(f"Command '{cmd_str}' timed out after {timeout} seconds.")
                        raise

                return_code = process.returncode
                if return_code != 0:
                    logger.error(f"Command exited with return code {return_code}")
                return subprocess.CompletedProcess(cmd, return_code)
            else:
                # Execute the command without streaming output
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=capture_output,
                    text=text,
                    shell=shell,
                    executable=executable,
                    timeout=timeout,  # Pass the timeout here
                )
                if result.returncode != 0:
                    logger.error(
                        f"Command '{cmd_str}' failed with return code {result.returncode}"
                    )
                if capture_output:
                    logger.debug(f"Command stdout: {result.stdout}")
                    if result.stderr:
                        logger.warning(f"Command stderr: {result.stderr}")
                return result

        except subprocess.TimeoutExpired as e:
            spinner.stop()  # Ensure spinner is stopped before logging
            logger.error(f"Command '{cmd_str}' timed out after {timeout} seconds.")
            raise
        except subprocess.CalledProcessError as e:
            spinner.stop()  # Ensure spinner is stopped before logging
            logger.error(f"Command '{' '.join(cmd)}' failed: {e}")
            raise
        except Exception as e:
            spinner.stop()  # Ensure spinner is stopped before logging
            logger.exception(f"Unexpected error while running command: {' '.join(cmd)}")
            raise
        finally:
            if verbose:
                spinner.stop()

    @staticmethod
    def get_user_shell() -> str:
        """
        Retrieve the user's preferred shell from environment variables.

        Returns:
            str: Path to the user's shell executable.
        """
        return os.environ.get("SHELL", "/bin/bash")
