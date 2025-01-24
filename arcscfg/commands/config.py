import sys
from pathlib import Path

from arcscfg.utils.dotfile_manager import DotfileManager

from .base import BaseCommand


class ConfigCommand(BaseCommand):
    """
    Handles the 'config' command for managing dotfiles and configurations.
    """

    def execute(self):
        self.logger.debug("Executing ConfigCommand")

        try:
            dotfile_manager = DotfileManager(
                logger=self.logger, assume_yes=self.args.yes
            )
            dotfile_manager.run_all()
            self.logger.info("Dotfile configuration completed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during configuration: {e}")
            sys.exit(1)

from pathlib import Path
import sys

from arcscfg.utils.dotfile_manager import DotfileManager
from arcscfg.utils.workspace_manager import WorkspaceManager

from .base import BaseCommand


class ConfigCommand(BaseCommand):
    """
    Handles the 'config' command.
    """

    def execute(self):
        self.logger.debug("Executing ConfigCommand")

        # Initialize DotfileManager
        dotfile_manager = DotfileManager(logger=self.logger, assume_yes=self.args.yes)

        # Get the workspace path if needed (for updating shell configuration and git hooks)
        workspace_path = self._get_workspace_path()

        try:
            dotfile_manager.run_all(workspace_path)
            self.logger.info("Dotfiles configuration completed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during dotfile configuration: {e}")
            sys.exit(1)

    def _get_workspace_path(self):
        """
        Get the workspace path for updating shell configurations and git hooks.
        """
        if self.args.workspace:
            workspace_path = Path(self.args.workspace).expanduser().resolve()
            self.logger.debug(f"Using provided workspace path: {workspace_path}")
            return workspace_path
        else:
            manager = WorkspaceManager(
                workspace_path=None,
                workspace_config=None,
                assume_yes=self.args.yes,
                logger=self.logger,
            )
            workspace_path = manager.prompt_for_workspace(
                default_workspace=None,
                allow_available=True,
                allow_create=False,
            )
            if workspace_path:
                self.logger.debug(f"User selected workspace path: {workspace_path}")
            return workspace_path
