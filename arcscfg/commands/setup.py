import sys

from arcscfg.utils.workspace_manager import WorkspaceManager

from .base import BaseCommand


class SetupCommand(BaseCommand):
    """
    Handles the 'setup' command.
    """

    def execute(self):
        self.logger.debug("Executing SetupCommand")

        # Initialize WorkspaceManager
        manager = WorkspaceManager(
            workspace_path=self.args.workspace,
            workspace_config=self.args.workspace_config,
            assume=self.args.assume,
            logger=self.logger,
            dependency_file_names=self.args.package_dependency_files,
            recursive_search=self.args.recursive_search,
            max_retries=self.args.max_retries,
            user_prompter=self.user_prompter,
        )

        # Get or prompt for workspace configuration
        workspace_config = manager.get_or_prompt_workspace_config()
        if not workspace_config:
            self.logger.error("Workspace configuration could not be determined.")
            sys.exit(1)
        manager.workspace_config = workspace_config

        # Get or prompt for workspace path
        default_workspace_path = manager.infer_default_workspace_path(workspace_config)
        workspace_path = manager.get_or_prompt_workspace_path(
            default_workspace=default_workspace_path,
            allow_available=False,
            allow_create=True,
        )
        if not workspace_path:
            self.logger.error("Workspace path could not be determined.")
            sys.exit(1)
        manager.workspace_path = workspace_path

        # Set up the workspace
        manager.setup_workspace()
