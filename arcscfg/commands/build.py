from arcscfg.utils.workspace_manager import WorkspaceManager

from .base import BaseCommand


class BuildCommand(BaseCommand):
    """
    Handles the 'build' command.
    """

    def execute(self):
        self.logger.debug("Executing BuildCommand")

        # Create a WorkspaceManager instance
        manager = WorkspaceManager(
            workspace_path=self.args.workspace,
            underlay_path=self.args.underlay,
            build_script_path=self.args.build_script,
            assume=self.args.assume,
            logger=self.logger,
            user_prompter=self.user_prompter,
        )

        # Get or prompt for workspace path
        workspace_path = manager.get_or_prompt_workspace_path(
            allow_available=True,
            allow_create=False,  # Assume we don't create a new workspace during build
        )

        # Determine the path to setup.bash
        default_underlay_path = manager.get_last_underlay_from_setup(workspace_path / "install" / "setup.bash")

        # Get or prompt for underlay path
        underlay_path = manager.get_or_prompt_underlay_path(default_underlay=default_underlay_path)

        # Get or prompt for build script path
        build_script_path = manager.get_or_prompt_build_script_path()

        # Update the manager with the resolved paths
        manager.workspace_path = workspace_path
        manager.underlay_path = underlay_path
        manager.build_script_path = build_script_path

        # Proceed with building the workspace
        manager.build_workspace()
