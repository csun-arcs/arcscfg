import sys
from pathlib import Path

from arcscfg.utils.dependency_manager import DependencyManager

from .base import BaseCommand


class InstallCommand(BaseCommand):
    """
    Handles the 'install' command.
    """

    def execute(self):
        self.logger.debug("Executing InstallCommand")

        # Initialize DependencyManager
        dep_manager = DependencyManager(
            dependencies_file=None,
            logger=self.logger,
            assume=self.args.assume,
            pip_install_method=self.args.pip_install_method or "user",
            context={
                "ARCSCFG_ROOT": str(Path(__file__).parent.parent.parent.resolve()),
                "ARCSCFG_ROS_DISTRO": self.args.ros_distro,
                "ARCSCFG_ROS_SOURCE_WORKSPACE_PATH": self.args.ros_source_workspace_path,
                "ARCSCFG_ROS_SOURCE_REF": self.args.ros_source_ref,
            },
        )

        # Handle ROS 2 installation
        try:
            if self.args.install_ros2 or self.user_prompter.prompt_yes_no("Install ROS 2?", default=False):
                self.args.ros_distro = self._get_or_prompt_ros_distro()
                dep_manager.context["ARCSCFG_ROS_DISTRO"] = self.args.ros_distro
                dep_manager.install_ros2()
        except Exception as e:
            self.logger.error(f"An error occurred during ROS 2 installation: {e}")
            sys.exit(1)

        # Handle dependencies installation
        try:
            if self.args.install_deps or self.user_prompter.prompt_yes_no("Install dependencies?", default=False):
                self.args.ros_distro = self._get_or_prompt_ros_distro()
                dep_manager.context["ARCSCFG_ROS_DISTRO"] = self.args.ros_distro
                dep_manager.dependencies_file = self._get_or_prompt_dependencies_file()
                self.logger.info(f"Installing dependencies from '{dep_manager.dependencies_file}'...")
                dep_manager.install_dependencies()
                self.logger.info("Dependencies installed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during dependency installation: {e}")
            sys.exit(1)

    def _get_or_prompt_ros_distro(self) -> str:
        """Handle ROS distribution selection with UserPrompter"""
        available_distros = [
            "ardent",
            "bouncy",
            "crystal",
            "dashing",
            "eloquent",
            "foxy",
            "galactic",
            "humble",
            "iron",
            "jazzy",
            "rolling",
        ]

        if self.args.ros_distro and self.args.ros_distro in available_distros:
            return self.args.ros_distro

        selection = self.user_prompter.prompt_selection(
            message="Select a ROS 2 distribution:",
            options=available_distros,
            default=available_distros.index("jazzy") + 1,  # 1-based index for display
        )

        return available_distros[selection]

    def _get_or_prompt_dependencies_file(self) -> Path:
        """Get dependency file path through UserPrompter"""
        if self.args.dependency_file:
            dep_file = self._resolve_dependencies_file(self.args.dependency_file)
            if dep_file.is_file():
                return dep_file

            self.logger.error(f"Dependencies file not found: {dep_file}")
            if self.args.yes:
                sys.exit(1)

        return self._prompt_dependencies_file()

    def _prompt_dependencies_file(self) -> Path:
        """Prompt for dependency file selection"""
        available_files = self._get_available_dependencies_files()

        if not available_files:
            self.logger.error("No dependency config files available!")
            sys.exit(1)

        # Prompt for selection
        options = [f"{f.stem} ('{f}')" for f in available_files]
        options.append("Enter custom path")

        selection = self.user_prompter.prompt_selection(
            message="Available dependency configurations:",
            options=options,
            default=1,  # First item as default
        )

        if selection < len(available_files):
            return available_files[selection]

        # Handle custom path input
        custom_path = self.user_prompter.prompt_input(
            "Enter path to custom dependencies file"
        )
        custom_path = Path(custom_path).expanduser().resolve()

        if not custom_path.exists():
            self.logger.error(f"File not found: {custom_path}")
            sys.exit(1)

        return custom_path

    def _resolve_dependencies_file(self, path_str: str) -> Path:
        """Resolve dependency file path"""
        paths_to_try = [
            Path(path_str).expanduser().resolve(),
            Path(__file__).parent.parent / "config/dependencies" / path_str,
            Path(__file__).parent.parent / "config/dependencies" / f"{path_str}.yaml",
        ]

        for path in paths_to_try:
            if path.exists():
                return path
        return Path(path_str)

    def _get_available_dependencies_files(self) -> list[Path]:
        """Get list of available dependency config files"""
        deps_dir = Path(__file__).parent.parent / "config/dependencies"
        return list(deps_dir.glob("*.yaml"))
