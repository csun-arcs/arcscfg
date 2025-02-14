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
        Execute a multi-line script.
        """
        self.logger.debug(f"Running script:\n{script_content}")
        try:
            Shell.run_command(script_content, shell=True, verbose=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Script failed: {e}")
            raise
