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
            assume_yes=self.args.yes,
            pip_install_method=self.args.pip_install_method or "user",
        )

        try:
            # Handle ROS 2 installation
            if self.args.install_ros2:
                ros_distro = self._prompt_ros_distro()
                dep_manager.context["ROS_DISTRO"] = ros_distro
                self._install_ros2(ros_distro)
            else:
                if not self.args.yes:
                    install_ros2 = self.user_prompter.prompt_yes_no(
                        "Do you want to install ROS 2?", default=False
                    )
                    if install_ros2:
                        ros_distro = self._prompt_ros_distro()
                        dep_manager.context["ROS_DISTRO"] = ros_distro
                        self._install_ros2(ros_distro)
        except Exception as e:
            self.logger.error(f"An error occurred during ROS 2 installation: {e}")
            sys.exit(1)

        try:
            dependencies_file = self._get_or_prompt_dependencies_file()
            self.logger.info(f"Installing dependencies from '{dependencies_file}'...")

            dep_manager.dependencies_file = dependencies_file
            dep_manager.install_dependencies()
            self.logger.info("Dependencies installed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during dependency installation: {e}")
            sys.exit(1)

    def _prompt_ros_distro(self) -> str:
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

        default_index = (
            available_distros.index(self.args.ros_distro)
            if self.args.ros_distro in available_distros
            else 9
        )  # Default to 'jazzy'

        selection = self.user_prompter.prompt_selection(
            message="Select a ROS 2 distribution to install:",
            options=available_distros,
            default=default_index + 1,  # 1-based index for display
        )

        return available_distros[selection]

    def _install_ros2(self, ros_distro: str):
        """Handle ROS 2 installation"""
        self.logger.info(f"Installing ROS 2 distribution: {ros_distro}")
        dep_manager = DependencyManager(
            dependencies_file=None,
            logger=self.logger,
            assume_yes=self.args.yes,
            pip_install_method="user",
            context={"ROS_DISTRO": ros_distro},
        )
        dep_manager.install_ros2(ros_distro)

    def _get_or_prompt_dependencies_file(self) -> Path:
        """Get dependency file path through UserPrompter"""
        if self.args.dependency_file:
            dep_file = self._resolve_dependency_file(self.args.dependency_file)
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
        options = [f.name for f in available_files]
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

    def _resolve_dependency_file(self, path_str: str) -> Path:
        """Resolve dependency file path with multiple fallbacks"""
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
