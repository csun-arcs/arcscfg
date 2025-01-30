import os
import subprocess
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

        workspace_config = self._get_or_prompt_workspace_config()
        if not workspace_config:
            self.logger.error("Workspace configuration could not be determined.")
            sys.exit(1)

        manager = WorkspaceManager(
            workspace_path=None,  # Will set after prompting
            workspace_config=str(workspace_config),
            assume_yes=self.args.yes,
            logger=self.logger,
            dependency_file_names=self.args.package_dependency_files,
            recursive_search=self.args.recursive_search,
        )

        workspace_path = self._get_or_prompt_workspace(manager)
        if not workspace_path:
            self.logger.error("Workspace path could not be determined.")
            sys.exit(1)

        manager.workspace_path = workspace_path
        manager.setup_workspace()

        self.logger.info("Workspace setup completed successfully.")

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
                        / "config/workspaces"
                        / self.args.workspace_config
                    )
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
                            / "config/workspaces"
                            / f"{self.args.workspace_config}.yaml"
                        )
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

    def _get_available_workspace_configs(self) -> list:
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

        print("\nAvailable workspace configs:")
        for i, workspace_config in enumerate(workspace_configs, start=1):
            print(
                f"{i}: {os.path.splitext(workspace_config.name)[0]} (config file path: '{workspace_config}')"
            )

        print(f"{len(workspace_configs)+1}: Enter a custom workspace config file path")

        while True:
            try:
                choice = input("Select a workspace config (default: 1): ").strip()
            except EOFError:
                choice = "1"

            if not choice:
                choice_num = 1
            else:
                try:
                    choice_num = int(choice)
                except ValueError:
                    print(
                        "Invalid input. Please enter a number corresponding to the options."
                    )
                    continue

            if 1 <= choice_num <= len(workspace_configs):
                selected_config = workspace_configs[choice_num - 1]
                self.logger.debug(f"User selected workspace config: {selected_config}")
                return selected_config
            elif choice_num == len(workspace_configs) + 1:
                # Allow user to enter a custom path
                custom_config = input(
                    "Enter the path to the custom workspace config: "
                ).strip()
                custom_config_path = Path(custom_config).expanduser().resolve()
                if not custom_config_path.is_file():
                    self.logger.error(
                        f"Custom workspace config does not exist: {custom_config_path}"
                    )
                    print("Please enter a valid existing file path.")
                    continue
                self.logger.debug(
                    f"User entered custom workspace config: {custom_config_path}"
                )
                return custom_config_path
            else:
                print("Invalid selection. Please choose a valid number.")

    def _get_or_prompt_workspace(self, manager: WorkspaceManager) -> Path:
        """
        Get the workspace path from arguments or prompt the user.
        """
        if self.args.workspace:
            workspace_path = Path(self.args.workspace).expanduser().resolve()
            self.logger.debug(f"Using provided workspace path: {workspace_path}")
            return workspace_path
        else:
            default_workspace_path = manager.infer_default_workspace_path(
                Path(manager.workspace_config)
            )
            return manager.prompt_for_workspace(
                default_workspace=default_workspace_path,
                allow_available=False,
                allow_create=True,
            )
