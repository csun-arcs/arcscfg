import sys
from pathlib import Path

from arcscfg.utils.workspace_manager import WorkspaceManager

from .base import BaseCommand


class UpdateCommand(BaseCommand):
    """
    Handles the 'update' command.
    """

    def execute(self):
        self.logger.debug("Executing UpdateCommand")

        workspace_path = self._get_workspace_path()
        if not workspace_path:
            self.logger.error("Workspace path could not be determined.")
            sys.exit(1)

        manager = WorkspaceManager(
            workspace_path=str(workspace_path),
            workspace_config=None,
            assume_yes=self.args.yes,
            logger=self.logger,
        )

        try:
            self.logger.info(f"Updating workspace at '{workspace_path}'")
            manager.update_workspace()
            self.logger.info("Workspace update completed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during update: {e}")
            sys.exit(1)

    def _get_workspace_path(self) -> Path:
        """
        Get the workspace path from arguments or prompt the user.
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
