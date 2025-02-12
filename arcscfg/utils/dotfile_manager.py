import os
import re
from pathlib import Path
from string import Template
from typing import Optional

from arcscfg.utils.backer_upper import BackerUpper
from arcscfg.utils.logger import Logger
from arcscfg.utils.user_prompter import UserPrompter
from arcscfg.utils.workspace_manager import WorkspaceManager


class DotfileManager:
    def __init__(
        self,
        logger: Optional[Logger] = None,
        backer_upper: Optional[BackerUpper] = None,
        workspace_path: Optional[Path] = None,
        assume_yes: bool = False,
        user_prompter: Optional[UserPrompter] = None,
    ):
        self.logger = logger or Logger()
        self.backer_upper = backer_upper or BackerUpper()
        self.workspace_path = workspace_path
        self.assume_yes = assume_yes
        self.user_prompter = user_prompter or UserPrompter(assume_yes=assume_yes)

        # Paths to the dotfiles and githooks directories
        self.dotfiles_dir = Path(__file__).parent.parent / "config" / "dotfiles"
        self.githooks_dir = self.dotfiles_dir / "githooks"

        # Collect dotfile templates present in the dotfiles directory
        self.dotfiles = [
            f"{f.name}"
            for f in self.dotfiles_dir.iterdir()
            if f.is_file() and f.name != ".gitconfig"
        ]

        # Create a unified context for template variable substitution
        self.context = {
            "ARCSCFG_START_BLOCK": "# >>> arcscfg >>>",
            "ARCSCFG_END_BLOCK": "# <<< arcscfg <<<",
            "ARCSCFG_BASHRC_DIR": str((self.dotfiles_dir / "bashrc").resolve()),
            "ARCSCFG_ZSHRC_DIR": str((self.dotfiles_dir / "zshrc").resolve()),
            "ARCSCFG_GITHOOKS_PATH": str(self.githooks_dir.resolve()),
            "ARCSCFG_SOURCE_WOKSPACE": "",
            # Add more variables as needed
        }

    def config_dotfiles(self):
        """
        Configure dotfiles with their respective handlers.
        """
        self.logger.info("Installing dotfiles...")
        for dotfile in self.dotfiles:
            src = self.dotfiles_dir / dotfile
            dst = Path.home() / dotfile

            # Prompt the user using UserPrompter
            if self.user_prompter.prompt_yes_no(f"Update {dst}?", default=False):
                self.handle_dotfile(dotfile, src, dst)
            else:
                self.logger.debug(f"Skipping {dst} as per user request.")

    def handle_dotfile(self, dotfile_name: str, src: Path, dst: Path):
        """
        Handle generic dotfiles by inserting or updating a template block.
        """
        # Read the template content and perform variable substitution
        with src.open("r") as template_file:
            template = Template(template_file.read())
            template_content = template.safe_substitute(self.context)

        start_marker = self.context["ARCSCFG_START_BLOCK"]
        end_marker = self.context["ARCSCFG_END_BLOCK"]

        # Prepare the regex pattern to search for the block
        block_pattern = re.compile(
            rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}",
            re.DOTALL,
        )

        if dst.exists():
            self.logger.info(f"{dst} exists. Updating or inserting the block.")
            self.backer_upper.backup(dst)

            with dst.open("r") as file:
                content = file.read()

            # Search for the existing block
            if block_pattern.search(content):
                # Replace the existing block
                new_content = block_pattern.sub(template_content, content).rstrip()
                self.logger.debug(f"Replaced existing block in {dst}")
            else:
                # Append the block at the end
                new_content = content.rstrip() + "\n\n" + template_content
                self.logger.debug(f"Appended new block to {dst}")

            with dst.open("w") as file:
                file.write(new_content)
            self.logger.info(f"Updated {dst}")
        else:
            # Create a new dotfile with the template content
            with dst.open("w") as file:
                file.write(template_content)
            self.logger.info(f"Installed new dotfile {dst}")

    def handle_gitconfig(self, src: Path, dst: Path):
        """
        Handle the installation of the .gitconfig file by merging configurations.
        """
        import configparser

        self.logger.debug(f"Configuring Git using template: {src}")

        # Read the template config
        template_config = configparser.RawConfigParser()
        template_config.read_string(src.read_text())

        # Substitute variables in the template config
        for section in template_config.sections():
            for key, value in template_config.items(section):
                substituted_value = Template(value).safe_substitute(self.context)
                template_config.set(section, key, substituted_value)

        # Read the existing config
        existing_config = configparser.RawConfigParser()
        existing_config.read(dst)

        # Merge the template config into the existing config
        for section in template_config.sections():
            if not existing_config.has_section(section):
                existing_config.add_section(section)
            for key, value in template_config.items(section):
                existing_config.set(section, key, value)

        # Backup the existing config
        if dst.exists():
            self.backer_upper.backup(dst)

        # Write the merged config back to the file
        with dst.open("w") as configfile:
            existing_config.write(configfile)

        self.logger.debug(f"Updated Git configuration at {dst}")

    def config_gitconfig(self, mode: str):
        """
        Configure git config either globally or in local repositories.

        Args:
            mode (str): 'global' or 'local' indicating installation mode.
        """
        src = self.dotfiles_dir / ".gitconfig"
        if mode == "global":
            dst = Path.home() / ".gitconfig"
            self.logger.info("Installing Git configuration globally.")
            self.handle_gitconfig(src, dst)
        elif mode == "local":
            if self.workspace_path:
                src_dir = self.workspace_path / "src"
                for repo_dir in src_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue
                    git_config_path = repo_dir / ".git" / "config"
                    if git_config_path.exists():
                        self.logger.info(
                            f"Installing Git configuration for repository: {repo_dir}"
                        )
                        self.handle_gitconfig(src, git_config_path)
            else:
                self.logger.error("Workspace path has not been set.")
        else:
            self.logger.error(f"Invalid mode '{mode}' for Git configuration.")

    def update_shell_config(self):
        """
        Update the shell configuration file to conditionally source the workspace setup script.
        """
        # Determine the shell and corresponding config file
        shell = Path(os.environ.get("SHELL", "/bin/bash")).name
        shell_rc_map = {
            "bash": ".bashrc",
            "zsh": ".zshrc",
        }
        shell_setup_map = {
            "bash": "setup.bash",
            "zsh": "setup.zsh",
        }
        shell_rc_file = Path.home() / shell_rc_map.get(shell, ".bashrc")
        template_name = shell_rc_file.name

        # Prompt the user for workspace sourcing
        source_workspace = self.user_prompter.prompt_yes_no(
            "Source the workspace from your shell config?",
            default=False,
        )

        if source_workspace:
            # Resolve workspace path
            self.resolve_workspace_path()
            setup_script_path = self.workspace_path / "install" / shell_setup_map[shell]

            if not setup_script_path.exists():
                self.logger.error(f"Setup script not found at {setup_script_path}")
                self.logger.debug(
                    f"Workspace path: {self.workspace_path}, Setup script path: {setup_script_path}"
                )
                # Even if the setup.bash doesn't exist, ensure the placeholder is handled
                self.context["ARCSCFG_SOURCE_WOKSPACE"] = (
                    "# Workspace sourcing script not found\n"
                )
            else:
                # Update context to include the sourcing line
                self.context["ARCSCFG_SOURCE_WOKSPACE"] = (
                    "# Source workspace setup script\nsource {}\n".format(
                        setup_script_path
                    )
                )
                self.logger.debug(
                    f"Workspace sourcing line added to context: {self.context['ARCSCFG_SOURCE_WOKSPACE']}"
                )
        else:
            # Update context to omit the sourcing line
            self.context["ARCSCFG_SOURCE_WOKSPACE"] = (
                "# Workspace sourcing not configured\n"
            )
            self.logger.debug("Workspace sourcing line omitted from context.")

        # Handle updating the shell config
        src = self.dotfiles_dir / template_name
        dst = shell_rc_file
        self.handle_dotfile(template_name, src, dst)

    def resolve_workspace_path(self):
        """
        Resolve a given workspace path or get it by prompting the user.
        """
        if self.workspace_path:
            self.workspace_path = Path(self.workspace_path).expanduser().resolve()
            self.logger.debug(f"Using provided workspace path: {self.workspace_path}")
        else:
            manager = WorkspaceManager(
                workspace_path=None,
                workspace_config=None,
                assume_yes=self.assume_yes,
                logger=self.logger,
                user_prompter=self.user_prompter,
            )
            self.workspace_path = manager.prompt_for_workspace(
                default_workspace=None,
                allow_available=True,
                allow_create=False,
            )
            if self.workspace_path:
                self.logger.debug(
                    f"User selected workspace path: {self.workspace_path}"
                )

    def run_all(self):
        """
        Run all the dotfile installation steps.
        """
        # Configure dotfiles
        if self.user_prompter.prompt_yes_no("Configure dotfiles?", default=False):
            self.config_dotfiles()

        # Configure environment for specific ROS 2 workspace
        config_workspace = self.user_prompter.prompt_yes_no(
            "Configure environment for specific ROS 2 workspace?", default=False
        )

        # Update shell config to source workspace
        if config_workspace:
            self.resolve_workspace_path()
            self.update_shell_config()

        # Configure git
        if config_workspace:
            gitconfig_choice = self.user_prompter.prompt_input(
                "Configure Git hooks globally or locally in workspace repositories?",
                options=["global", "local", "skip"],
                default="skip",
            )
        else:
            gitconfig_choice = self.user_prompter.prompt_input(
                "Configure Git hooks globally?",
                options=["global", "skip"],
                default="skip",
            )

        if gitconfig_choice == "global":
            self.config_gitconfig(mode="global")
        elif gitconfig_choice == "local":
            self.config_gitconfig(mode="local")
        else:
            self.logger.debug("Skipping Git hooks configuration as per user choice.")
