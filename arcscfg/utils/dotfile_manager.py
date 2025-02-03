import os
import shutil
from pathlib import Path
from typing import List, Optional

from .logger import Logger


class DotfileManager:
    def __init__(self, logger: Optional[Logger] = None, assume_yes: bool = False):
        self.logger = logger or Logger()
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

    def backup_dotfile(self, filepath: Path):
        """
        Backup the existing dotfile by copying it to a backup location.
        """
        backup_dir = filepath.parent / "arcscfg_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / (filepath.name + ".bak")
        shutil.copy(filepath, backup_path)
        self.logger.info(f"Backed up {filepath} to {backup_path}")

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
            self.backup_dotfile(dst)

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
            self.backup_dotfile(dst)
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

    def update_shell_configuration(self, workspace_path: Path):
        """
        Add a line to the user's shell configuration file to source the workspace setup script.
        """
        shell = Path(os.environ.get("SHELL", "/bin/bash")).name
        shell_rc = {
            "bash": ".bashrc",
            "zsh": ".zshrc",
        }

        shell_rc_file = Path.home() / shell_rc.get(shell, ".bashrc")
        setup_script_path = workspace_path / "install" / "setup.bash"

        if not setup_script_path.exists():
            self.logger.warning(f"Setup script not found at {setup_script_path}")
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
        self.backup_dotfile(shell_rc_file)

        # Append the sourcing line
        with shell_rc_file.open("a") as file:
            file.write("\n# Added by arcscfg\n")
            file.write(line_to_add)

        self.logger.info(
            f"Updated {shell_rc_file} to source the workspace setup script."
        )

    def install_git_hooks(self, workspace_path: Path):
        """
        Install git hooks in the workspace repositories.
        """
        git_hooks = list(self.githooks_dir.glob("*"))
        src_dir = workspace_path / "src"

        # Prompt the user
        if not self.assume_yes:
            proceed = (
                input(
                    f"Install git hooks in '{workspace_path}' workspace repositories (y/N): "
                )
                .strip()
                .lower()
            )
            if proceed != "y":
                self.logger.debug(
                    f"Skipping workspace repository git hook installation as per user request."
                )
                return

        for repo_dir in src_dir.iterdir():
            git_dir = repo_dir / ".git"
            hooks_dir = git_dir / "hooks"
            if git_dir.exists() and hooks_dir.exists():
                self.logger.info(f"Installing git hooks in {repo_dir}")
                for hook in git_hooks:
                    hook_dst = hooks_dir / hook.name
                    shutil.copy(hook, hook_dst)
                    hook_dst.chmod(0o755)  # Ensure the hook script is executable
            else:
                self.logger.warning(f"No git repository found at {repo_dir}")

    def run_all(self, workspace_path: Optional[Path]):
        """
        Run all the dotfile installation steps in a streamlined manner.
        Handles all types of dotfiles without redundancy.
        """
        install_dotfiles = input("Install dotfiles? (y/N): ").strip().lower()
        if install_dotfiles == "y":
            self.install_dotfiles()

        if workspace_path:
            self.update_shell_configuration(workspace_path)
            self.install_git_hooks(workspace_path)
        else:
            self.logger.debug(
                "Workspace path not provided. Skipping workspace-related configurations."
            )
