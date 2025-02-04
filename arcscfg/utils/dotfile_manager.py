import os
import shutil
from pathlib import Path
from string import Template
from typing import Optional


from arcscfg.utils.workspace_manager import WorkspaceManager

from .logger import Logger
from .backer_upper import BackerUpper


class DotfileManager:
    def __init__(
        self,
        logger: Optional[Logger] = None,
        backer_upper: Optional[BackerUpper] = None,
        workspace_path: Optional[Path] = None,
        assume_yes: bool = False,
    ):
        self.logger = logger or Logger()
        self.backer_upper = backer_upper or BackerUpper()
        self.workspace_path = workspace_path
        self.assume_yes = assume_yes

        # Define the dotfiles to manage
        self.dotfiles = [
            ".bashrc",
            ".zshrc",
            ".vimrc",
            ".emacs",
            ".tmux.conf",
            # Add more dotfiles as needed
        ]

        # Paths to the dotfiles and githooks directories
        self.dotfiles_dir = Path(__file__).parent.parent / "config" / "dotfiles"
        self.githooks_dir = Path(__file__).parent.parent / "config" / "githooks"

        # Path to the Gitconfig template
        self.gitconfig_template = self.dotfiles_dir / ".gitconfig"

    def backup_dotfile(self, filepath: Path):
        """
        Backup the existing dotfile by copying it to a backup location.
        """
        backup_dir = filepath.parent / ".arcscfg_dotfile_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / (filepath.name + ".bak")
        shutil.copy(filepath, backup_path)
        self.logger.debug(f"Backed up {filepath} to {backup_path}")

    def install_dotfiles(self):
        """
        Install or update all dotfiles, delegating specific configurations
        to helper methods as necessary.
        """
        self.logger.info("Installing dotfiles...")
        for dotfile in self.dotfiles:
            src = self.dotfiles_dir / dotfile.lstrip(".")
            dst = Path.home() / dotfile

            # Prompt the user
            if not self.assume_yes:
                proceed = input(f"Update {dst}? (y/N): ").strip().lower()
                if proceed != "y":
                    self.logger.debug(f"Skipping {dst} as per user request.")
                    continue

            if dotfile in [".bashrc", ".zshrc"]:
                self.handle_shell_dotfile(dotfile, src, dst)
            elif dotfile in [".vimrc", ".emacs"]:
                self.handle_editor_dotfile(src, dst)
            elif dotfile == ".tmux.conf":
                self.handle_tmux_config(src, dst)
            else:
                self.handle_generic_dotfile(src, dst)

    def handle_shell_dotfile(self, dotfile_name: str, src: Path, dst: Path):
        """
        Handle .bashrc and .zshrc files by adding include lines to snippets.
        """
        snippets_dir = self.dotfiles_dir / dotfile_name.lstrip(".")
        main_snippet = snippets_dir / "main.sh"
        main_snippet_path = main_snippet.resolve()
        include_line = f"source {main_snippet_path}\n"

        if dst.exists():
            self.logger.info(f"{dst} exists. Adding include line.")
            self.backer_upper.backup(dst)

            # Check if the include line already exists
            with dst.open("r") as file:
                lines = file.readlines()
                if any(include_line.strip() in line.strip() for line in lines):
                    self.logger.info(f"Include line already present in {dst}")
                    return

            # Append the include line
            with dst.open("a") as file:
                file.write("\n# Added by arcscfg\n")
                file.write(include_line)
            self.logger.info(f"Updated {dst} to include arcscfg snippets.")

        else:
            # Create a new dotfile with the include line
            with dst.open("w") as file:
                file.write("# Created by arcscfg\n")
                file.write(include_line)
            self.logger.info(f"Installed new shell dotfile {dst}")

    def handle_editor_dotfile(self, src: Path, dst: Path):
        """
        Handle editor configuration files like .vimrc and .emacs.
        """
        self.logger.info(f"Configuring editor dotfile {dst}")
        self.modify_dotfile(src, dst)

    def handle_tmux_config(self, src: Path, dst: Path):
        """
        Handle tmux configuration file.
        """
        self.logger.info(f"Configuring TMUX config {dst}")
        self.modify_dotfile(src, dst)

    def handle_generic_dotfile(self, src: Path, dst: Path):
        """
        Handle generic dotfiles not requiring special processing.
        """
        if dst.exists():
            self.logger.info(f"Dotfile {dst} exists.")
            self.backer_upper.backup(dst)
            shutil.copy(src, dst)
            self.logger.info(f"Updated {dst}")
        else:
            # Copy the dotfile
            shutil.copy(src, dst)
            self.logger.info(f"Installed new dotfile {dst}")

    def modify_dotfile(self, src: Path, dst: Path):
        """
        Modify the existing dotfile by appending necessary configurations.
        """
        self.logger.info(f"Modifying existing dotfile {dst}")
        with src.open("r") as src_file:
            content_to_add = src_file.read()

        with dst.open("a") as dst_file:
            dst_file.write("\n# Added by arcscfg\n")
            dst_file.write(content_to_add)

    def handle_gitconfig(self, target_path: Path):
        """
        Handle the installation of the .gitconfig file by templating the hooksPath.
        """
        if not self.gitconfig_template.exists():
            self.logger.error(
                f"Gitconfig template not found at {self.gitconfig_template}"
            )
            return

        self.logger.debug(f"Configuring Git using template: {self.gitconfig_template}")

        # Read the template content
        with self.gitconfig_template.open("r") as template_file:
            template_content = template_file.read()

        # Prepare the hooks path
        hooks_path = str(self.githooks_dir.resolve())

        # Substitute the placeholder with actual hooks path
        gitconfig_content = Template(template_content).safe_substitute(
            HOOKS_PATH=hooks_path
        )

        # If target_path exists, back it up
        if target_path.exists():
            self.logger.debug(f"{target_path} exists. Backing it up before overwriting.")
            self.backer_upper.backup(target_path)

        # Write the new .gitconfig
        with target_path.open("w") as config_file:
            config_file.write(gitconfig_content)

        self.logger.debug(f"Installed Git configuration to {target_path}")

    def install_gitconfig(
        self,
        global_config: bool = False,
    ):
        """
        Install the .gitconfig either globally or in a specific repository.

        Args:
            global_config (bool): If True, install globally to ~/.gitconfig.
            local_repo_path (Optional[Path]): If provided, install to <repo>/.git/config.
        """
        if global_config:
            target_path = Path.home() / ".gitconfig"
            self.logger.info("Installing Git configuration globally.")
            self.handle_gitconfig(target_path)
        else:
            if self.workspace_path:
                src_dir = self.workspace_path / "src"
            else:
                self.logger.error("Workspace path has not been set.")
                return

            for repo_dir in src_dir.iterdir():
                if not repo_dir.is_dir():
                    continue
                target_path = repo_dir / ".git" / "config"
                self.logger.info(
                    f"Installing Git configuration for repository: {repo_dir}"
                )
                self.handle_gitconfig(target_path)

    def source_workspace_from_shell_cfg(self):
        """
        Add a line to the user's shell configuration file to source the workspace setup script.
        """
        source_workspace = (
            input("Source workspace from your shell config (.bashrc or .zshrc)? (y/N): ")
            .strip()
            .lower()
            if not self.assume_yes
            else "y"
        )
        if not source_workspace == "y":
            return

        shell = Path(os.environ.get("SHELL", "/bin/bash")).name
        shell_rc = {
            "bash": ".bashrc",
            "zsh": ".zshrc",
        }

        shell_rc_file = Path.home() / shell_rc.get(shell, ".bashrc")
        if self.workspace_path:
            setup_script_path = self.workspace_path / "install" / "setup.bash"
        else:
            self.logger.error("Workspace path has not been set.")
            return

        if not setup_script_path.exists():
            self.logger.error(f"Setup script not found at {setup_script_path}")
            return

        line_to_add = f"source {setup_script_path}\n"

        # Check if the line already exists
        with shell_rc_file.open("r") as file:
            lines = file.readlines()
            if any(line.strip() == line_to_add.strip() for line in lines):
                self.logger.info(f"Setup script already sourced in {shell_rc_file}")
                return

        # Prompt the user
        if not self.assume_yes:
            proceed = (
                input(
                    f"Update {shell_rc_file} to source the workspace setup script? (y/N): "
                )
                .strip()
                .lower()
            )
            if proceed != "y":
                self.logger.debug(
                    f"Skipping update of {shell_rc_file} as per user request."
                )
                return

        # Backup the shell configuration file
        self.backer_upper.backup(shell_rc_file)

        # Append the sourcing line
        with shell_rc_file.open("a") as file:
            file.write("\n# Added by arcscfg\n")
            file.write(line_to_add)

        self.logger.info(
            f"Updated {shell_rc_file} to source the workspace setup script."
        )

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
            )
            self.workspace_path = manager.prompt_for_workspace(
                default_workspace=None,
                allow_available=True,
                allow_create=False,
            )
            if self.workspace_path:
                self.logger.debug(f"User selected workspace path: {self.workspace_path}")

    def run_all(self):
        """
        Run all the dotfile installation steps.
        """
        install_dotfiles = (
            input("Install dotfiles? (y/N): ").strip().lower()
            if not self.assume_yes
            else "y"
        )
        if install_dotfiles == "y":
            self.install_dotfiles()

        # Get the workspace path if needed (for updating shell configuration and git hooks)
        config_workspace = (
            input("Configure your environment for a specific ROS 2 workspace? (y/N): ")
            .strip()
            .lower()
            if not self.assume_yes
            else "y"
        )
        if config_workspace == "y":
            self.resolve_workspace_path()
            self.source_workspace_from_shell_cfg()

        # Handle Git configuration
        self.logger.debug("Configuring Git hooks paths.")
        gitconfig_choice = (
            input(
                "Configure Git hooks globally or locally in workspace repositories? ((g)lobal/(l)ocal/(S)kip): "
            )
            .strip()
            .lower()
            if not self.assume_yes
            else "global"
        )
        if gitconfig_choice == "g" or gitconfig_choice == "global":
            self.install_gitconfig(global_config=True)
        elif gitconfig_choice == "l" or gitconfig_choice in "local":
            self.install_gitconfig(global_config=False)
        else:
            self.logger.info("Skipping Git hooks configuration as per user choice.")
