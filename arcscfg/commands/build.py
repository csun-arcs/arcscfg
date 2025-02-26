import sys
from pathlib import Path

from arcscfg.utils.workspace_manager import WorkspaceManager

from .base import BaseCommand


class BuildCommand(BaseCommand):
    """
    Handles the 'build' command.
    """

    def execute(self):
        self.logger.debug("Executing BuildCommand")

        workspace_path = self._get_workspace_path()
        if not workspace_path:
            self.logger.error("Workspace path could not be determined.")
            sys.exit(1)

        manager = WorkspaceManager(
            workspace_path=str(workspace_path),
            workspace_config=None,  # Assuming build doesn't require config
            assume_yes=self.args.yes,
            logger=self.logger,
        )

        manager.build_workspace()

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
            workspace_path = manager._prompt_for_workspace(
                default_workspace=None,
                allow_available=True,
                allow_create=False,
            )
            if workspace_path:
                self.logger.debug(f"User selected workspace path: {workspace_path}")
            return workspace_path
