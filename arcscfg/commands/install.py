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

        # Initialize DependencyManager without dependencies_file
        dep_manager = DependencyManager(
            dependencies_file=None,
            logger=self.logger,
            assume_yes=self.args.yes,
            pip_install_method=self.args.pip_install_method or "user",
        )

        try:
            # Handle ROS 2 installation
            if self.args.install_ros2:
                ros_distro = self._prompt_for_ros_distro()
                dep_manager.context["ROS_DISTRO"] = ros_distro  # Add context
                self._install_ros2(ros_distro)
            else:
                if not self.args.yes:
                    install_ros2 = (
                        input("Do you want to install ROS 2? (y/N): ").strip().lower()
                    )
                    if install_ros2 == "y":
                        ros_distro = self._prompt_for_ros_distro()
                        dep_manager.context["ROS_DISTRO"] = ros_distro  # Add context
                        dep_manager.install_ros2(ros_distro)
        except Exception as e:
            self.logger.error(f"An error occurred during ROS 2 installation: {e}")
            sys.exit(1)

        try:
            dependencies_file = self._get_or_prompt_dependencies_file()
            self.logger.info(f"Installing dependencies from '{dependencies_file}'...")

            # Update dependencies_file in dep_manager
            dep_manager.dependencies_file = dependencies_file
            dep_manager.pip_install_method = self.args.pip_install_method or "user"
            dep_manager.assume_yes = self.args.yes

            # Pass the ros_distro context to install dependencies
            if "ros_distro" not in dep_manager.context:
                dep_manager.context["ROS_DISTRO"] = self.args.ros_distro

            dep_manager.install_dependencies()
            self.logger.info("Dependencies installed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during dependency installation: {e}")
            sys.exit(1)

    def _prompt_for_ros_distro(self):
        available_distros=[
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
        print("\nAvailable ROS 2 distributions:")
        for i, distro in enumerate(available_distros, start=1):
            if distro == self.args.ros_distro:
                print(f"{i}: {distro} (default)")
            else:
                print(f"{i}: {distro}")

        default_ros_distro = available_distros.index(self.args.ros_distro) + 1

        if self.args.yes:
            self.logger.debug(
                f"Assuming default ROS 2 distro: {default_ros_distro} ({self.args.ros_distro})"
            )
            return self.args.ros_distro

        while True:
            choice = input(
                f"Select a ROS 2 distribution to install (default: {default_ros_distro}): "
            ).strip()
            if not choice:
                choice_num = default_ros_distro
            else:
                try:
                    choice_num = int(choice)
                except ValueError:
                    print(
                        "Invalid input. Please enter a number corresponding to the options."
                    )
                    continue
            if 1 <= choice_num <= len(available_distros):
                selected_distro = available_distros[choice_num - 1]
                self.logger.debug(
                    f"User selected ROS 2 distribution: {selected_distro}"
                )
                return selected_distro
            else:
                print("Invalid selection. Please choose a valid number.")

    def _install_ros2(self, ros_distro: str):
        self.logger.info(f"Installing ROS 2 distribution: {ros_distro}")
        dep_manager = DependencyManager(
            dependencies_file=None,  # No dependency file needed for ROS 2 base install
            logger=self.logger,
            assume_yes=self.args.yes,
            pip_install_method="user",
            context={"ROS_DISTRO": ros_distro},  # Pass context
        )
        dep_manager.install_ros2(ros_distro)

    def _get_or_prompt_dependencies_file(self) -> Path:
        """
        Get the dependencies file path from arguments or prompt the user.
        """
        if self.args.dependency_file:
            dependencies_file = self._resolve_dependency_file_path(
                self.args.dependency_file
            )
            if dependencies_file.is_file():
                self.logger.debug(
                    f"Using provided dependencies file: {dependencies_file}"
                )
                return dependencies_file
            else:
                self.logger.error(
                    f"Dependencies file does not exist: {dependencies_file}"
                )
                # Reset "assume yes to defaults" to ensure user is prompted
                self.args.yes = False

        dependencies_files = self._get_available_dependencies_files()
        dependencies_file = self._prompt_for_dependencies_file(dependencies_files)
        self.logger.debug(f"Selected dependencies file: {dependencies_file}")
        return dependencies_file

    def _resolve_dependency_file_path(self, path_str: str) -> Path:
        """
        Resolve the dependency file path from a string, checking several locations.
        """
        # Try absolute path
        dependencies_file = Path(path_str).expanduser().resolve()
        if dependencies_file.is_file():
            return dependencies_file

        # Try relative to config/dependencies
        dependencies_file = (
            Path(__file__).parent.parent / "config/dependencies" / path_str
        ).resolve()
        if dependencies_file.is_file():
            return dependencies_file

        # Try adding .yaml extension
        dependencies_file_with_extension = dependencies_file.with_suffix(".yaml")
        if dependencies_file_with_extension.is_file():
            return dependencies_file_with_extension

        # If not found, return original path
        return Path(path_str)

    def _get_available_dependencies_files(self) -> list:
        """
        Retrieve available dependency configuration files.
        """
        dependencies_dir = Path(__file__).parent.parent / "config" / "dependencies"
        dependencies_files = list(dependencies_dir.glob("*.yaml"))
        self.logger.debug(f"Found dependencies files: {dependencies_files}")
        return dependencies_files

    def _prompt_for_dependencies_file(self, dependencies_files: list) -> Path:
        """
        Prompt the user to select a dependencies file from the available options.
        """
        if self.args.yes:
            selected_file = dependencies_files[0] if dependencies_files else None
            if selected_file:
                self.logger.debug(
                    f"Assuming default dependencies file: {selected_file}"
                )
                return selected_file
            else:
                self.logger.error(
                    "No dependencies files available to select by default."
                )
                sys.exit(1)

        print("\nAvailable dependencies files:")
        for i, dependencies_file in enumerate(dependencies_files, start=1):
            print(f"{i}: {dependencies_file.name}")

        print(f"{len(dependencies_files)+1}: Enter a custom dependencies file path")

        while True:
            try:
                choice = input("Select a dependencies file (default: 1): ").strip()
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

            if 1 <= choice_num <= len(dependencies_files):
                selected_file = dependencies_files[choice_num - 1]
                self.logger.debug(f"User selected dependencies file: {selected_file}")
                return selected_file
            elif choice_num == len(dependencies_files) + 1:
                # Allow user to enter a custom path
                custom_file = input(
                    "Enter the path to the custom dependencies file: "
                ).strip()
                custom_file_path = Path(custom_file).expanduser().resolve()
                if not custom_file_path.is_file():
                    self.logger.error(
                        f"Custom dependencies file does not exist: {custom_file_path}"
                    )
                    print("Please enter a valid existing file path.")
                    continue
                self.logger.debug(
                    f"User entered custom dependencies file: {custom_file_path}"
                )
                return custom_file_path
            else:
                print("Invalid selection. Please choose a valid number.")
