import yaml
import subprocess

from typing import Dict, Any
from pathlib import Path

from arcscfg.utils.logger import Logger
from arcscfg.utils.shell import Shell


class ScriptExecutor:
    def __init__(self, script_path: Path, logger: Logger):
        self.script_path = script_path
        self.logger = logger
        self.script_content = self.load_script()

    def load_script(self) -> Dict[str, Any]:
        with self.script_path.open('r') as file:
            return yaml.safe_load(file)

    def execute(self):
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
        self.logger.debug(f"Running command: {cmd}")
        try:
            Shell.run_command(cmd, shell=True, verbose=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e}")
            raise

    def run_script(self, script_content: str):
        self.logger.debug(f"Running script:\n{script_content}")
        try:
            Shell.run_command(script_content, shell=True, verbose=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Script failed: {e}")
            raise
