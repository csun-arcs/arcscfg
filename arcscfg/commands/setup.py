import sys
from pathlib import Path

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
            workspace_path=None,  # Will set after prompting
            workspace_config=None,
            assume_yes=self.args.yes,
            logger=self.logger,
            dependency_file_names=self.args.package_dependency_files,
            recursive_search=self.args.recursive_search,
            user_prompter=self.user_prompter,  # Inject UserPrompter
        )

        # Get or prompt for workspace configuration
        workspace_config = self._get_or_prompt_workspace_config()
        if not workspace_config:
            self.logger.error("Workspace configuration could not be determined.")
            sys.exit(1)

        # Load workspace configuration into WorkspaceManager
        manager.workspace_config = workspace_config

        # Get or prompt for workspace path
        workspace_path = self._get_or_prompt_workspace(manager)
        if not workspace_path:
            self.logger.error("Workspace path could not be determined.")
            sys.exit(1)

        manager.workspace_path = workspace_path

        # Set up the workspace
        manager.setup_workspace()

    def _get_or_prompt_workspace_config(self) -> Path:
        """
        Get the workspace configuration path from arguments or prompt the user.
        """
        workspace_config = None
        if self.args.workspace_config:
            try:
                # Attempt absolute path
                workspace_config = Path(self.args.workspace_config).resolve()
                self.logger.debug(
                    f"Attempting to resolve absolute workspace config path: {workspace_config}"
                )
                if not workspace_config.is_file():
                    raise ValueError
            except Exception:
                try:
                    # Attempt relative to config/workspaces
                    workspace_config = (
                        Path(__file__).parent.parent
                        / "config"
                        / "workspaces"
                        / self.args.workspace_config
                    ).resolve()
                    self.logger.debug(
                        f"Attempting to resolve relative workspace config: {workspace_config}"
                    )
                    if not workspace_config.is_file():
                        raise ValueError
                except Exception:
                    try:
                        # Attempt adding .yaml extension
                        workspace_config = (
                            Path(__file__).parent.parent
                            / "config"
                            / "workspaces"
                            / f"{self.args.workspace_config}.yaml"
                        ).resolve()
                        self.logger.debug(
                            f"Attempting to resolve workspace config path with .yaml extension: {workspace_config}"
                        )
                        if not workspace_config.is_file():
                            raise ValueError
                    except Exception:
                        workspace_config = None
                        self.logger.error(
                            "Unable to resolve workspace config argument!"
                        )
                        # Reset "assume yes to defaults" to ensure user is prompted for workspace config
                        self.args.yes = False

        if not workspace_config:
            workspace_configs = self._get_available_workspace_configs()
            workspace_config = self._prompt_for_workspace_config(workspace_configs)
            self.logger.debug(f"Selected workspace config: {workspace_config}")
        return workspace_config

    def _get_available_workspace_configs(self) -> list[Path]:
        """
        Retrieve available workspace configuration files.
        """
        workspaces_dir = Path(__file__).parent.parent / "config" / "workspaces"
        workspace_configs = list(workspaces_dir.glob("*.yaml"))
        self.logger.debug(f"Found workspace configs: {workspace_configs}")
        return workspace_configs

    def _prompt_for_workspace_config(self, workspace_configs: list) -> Path:
        """
        Prompt the user to select a workspace configuration from the available options.
        """
        if self.args.yes:
            selected_config = workspace_configs[0] if workspace_configs else None
            if selected_config:
                self.logger.debug(
                    f"Assuming default workspace config: {selected_config}"
                )
                return selected_config
            else:
                self.logger.error(
                    "No workspace configurations available to select by default."
                )
                sys.exit(1)

        options = [f"{config.stem} ('{config}')" for config in workspace_configs]
        options.append("Enter a custom workspace config file path")

        selection = self.user_prompter.prompt_selection(
            message="Available workspace configurations:",
            options=options,
            default=1,  # First option as default
        )

        if selection < len(workspace_configs):
            return workspace_configs[selection]

        # Handle custom path input
        custom_config = self.user_prompter.prompt_input(
            "Enter the path to the custom workspace config"
        )
        custom_config_path = Path(custom_config).expanduser().resolve()

        if not custom_config_path.is_file():
            self.logger.error(
                f"Custom workspace config does not exist: {custom_config_path}"
            )
            sys.exit(1)

        return custom_config_path

    def _get_or_prompt_workspace(self, manager: WorkspaceManager) -> Path:
        """
        Get the workspace path from arguments or prompt the user.
        """
        if self.args.workspace:
            workspace_path = Path(self.args.workspace).expanduser().resolve()
            self.logger.debug(f"Using provided workspace path: {workspace_path}")
            return workspace_path
        else:
            default_workspace_path = manager._infer_default_workspace_path(
                Path(manager.workspace_config)
            )
            return manager._prompt_for_workspace(
                default_workspace=default_workspace_path,
                allow_available=False,
                allow_create=True,
            )
