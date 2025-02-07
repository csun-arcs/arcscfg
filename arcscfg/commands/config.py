import sys

from arcscfg.utils.dotfile_manager import DotfileManager

from .base import BaseCommand


class ConfigCommand(BaseCommand):
    """
    Handles the 'config' command.
    """

    def execute(self):
        self.logger.debug("Executing ConfigCommand")

        # Initialize DotfileManager
        dotfile_manager = DotfileManager(
            logger=self.logger,
            backer_upper=self.backer_upper,
            workspace_path=self.args.workspace,
            assume_yes=self.args.yes,
        )

        try:
            dotfile_manager.run_all()
            self.logger.info("Dotfiles configuration completed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during dotfile configuration: {e}")
            sys.exit(1)
