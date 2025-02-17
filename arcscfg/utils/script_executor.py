import yaml
import subprocess
from typing import Dict, Any
from pathlib import Path
from string import Template  # Import Template for substitution

from arcscfg.utils.logger import Logger
from arcscfg.utils.shell import Shell

class ScriptExecutor:
    def __init__(self, script_path: Path, logger: Logger, context: Dict[str, str] = None):
        self.script_path = script_path
        self.logger = logger
        self.context = context or {}
        self.script_content = self.load_and_substitute_script()

    def load_and_substitute_script(self) -> Dict[str, Any]:
        """
        Load the YAML script and perform template substitution.
        """
        with self.script_path.open('r') as file:
            raw_content = file.read()
        
        self.logger.debug(f"Raw script content before substitution:\n{raw_content}")

        # Perform template substitution
        template = Template(raw_content)
        try:
            substituted_content = template.safe_substitute(self.context)
        except KeyError as e:
            self.logger.error(f"Missing substitution variable: {e}")
            raise

        self.logger.debug(f"Substituted script content:\n{substituted_content}")

        return yaml.safe_load(substituted_content)

    def execute(self):
        """
        Execute each step in the substituted YAML script.
        """
        steps = self.script_content.get('steps', [])
        for step in steps:
            message = step.get('message')
            if message:
                self.logger.info(message)

            # Handle 'command', 'commands', and 'script'
            if 'command' in step:
                self.run_command(step['command'])
            elif 'commands' in step:
                for cmd in step['commands']:
                    self.run_command(cmd)
            elif 'script' in step:
                self.run_script(step['script'])
            else:
                self.logger.debug("No command found in this step.")

    def run_command(self, cmd: str):
        """
        Execute a single command.
        """
        self.logger.debug(f"Running command: {cmd}")
        try:
            Shell.run_command(cmd, shell=True, verbose=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e}")
            raise

    def run_script(self, script_content: str):
        """
        Execute a multi-line script with proper shell handling.
        """
        self.logger.debug(f"Running script:\n{script_content}")
        
        lines = script_content.strip().splitlines()
        if not lines:
            self.logger.warning("Empty script content provided.")
            return

        # Detect shebang
        first_line = lines[0].strip()
        if first_line.startswith("#!"):
            shell_path = first_line[2:].strip()
            script_body = "\n".join(lines[1:])
            self.logger.debug(f"Detected shebang: {shell_path}")
        else:
            # Default to the user's preferred shell
            shell_path = Shell.get_user_shell()
            script_body = script_content
            self.logger.debug(f"No shebang detected. Using default shell: {shell_path}")

        if not shell_path:
            self.logger.error("No shell executable found. Cannot execute script.")
            raise ValueError("Shell executable not determined.")

        # Execute the script using the detected shell
        try:
            Shell.run_command(
                [shell_path, "-c", script_body],
                shell=False,  # We are explicitly specifying the shell
                verbose=True
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Script execution failed: {e}")
            raise
