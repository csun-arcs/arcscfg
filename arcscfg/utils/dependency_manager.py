import sys
import yaml
import subprocess
import platform
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Union

from arcscfg.utils.user_prompter import UserPrompter
from arcscfg.utils.script_executor import ScriptExecutor

from .logger import Logger
from .shell import Shell


class DependencyManager:
    def __init__(
        self,
        dependencies_file: Optional[Union[str, Path]] = None,
        logger: Optional[Logger] = None,
        assume_yes: bool = False,
        pip_install_method: str = "user",
        context: Optional[Dict[str, str]] = None,
        user_prompter: Optional[UserPrompter] = None,
    ):
        if dependencies_file:
            self.dependencies_file = Path(dependencies_file)
        else:
            self.dependencies_file = None
        self.logger = logger or Logger()
        self.assume_yes = assume_yes
        self.pip_install_method = pip_install_method
        self.dependencies = {}  # type: Dict[str, Any]
        self.context = context or {}
        self.user_prompter = user_prompter or UserPrompter(assume_yes=assume_yes)

    def load_dependencies(self):
        """Load dependencies from dependencies file"""
        if not self.dependencies_file:
            self.logger.error("No dependencies file provided.")
            raise ValueError("Dependencies file not set.")
        if not self.dependencies_file.exists():
            self.logger.error(
                f"Dependencies file does not exist: {self.dependencies_file}"
            )
            raise FileNotFoundError(
                f"Dependencies file not found: {self.dependencies_file}"
            )
        with self.dependencies_file.open("r") as f:
            raw_content = f.read()

        # Perform template substitution
        template = Template(raw_content)
        try:
            substituted_content = template.safe_substitute(self.context)
        except KeyError as e:
            self.logger.error(f"Missing substitution variable: {e}")
            raise

        self.dependencies = yaml.safe_load(substituted_content)
        self.logger.debug(
            f"Loaded dependencies after substitution: {self.dependencies}"
        )

    def install_dependencies(self):
        """Install apt/pip dependencies specified in dependencies file"""
        if not self.dependencies_file:
            self.logger.error("No dependencies file provided.")
            raise ValueError("Dependencies file not set.")
        self.load_dependencies()

        if "apt" in self.dependencies:
            self._install_apt_packages(self.dependencies["apt"])
        if "pip" in self.dependencies:
            self._install_pip_packages(self.dependencies["pip"])
        if "brew" in self.dependencies:
            self._install_brew_packages(self.dependencies["brew"])
        if "homebrew" in self.dependencies:
            self._install_brew_packages(self.dependencies["homebrew"])

    def _install_apt_packages(self, packages: List[Any]):
        """Install apt packages from a given list"""
        self.logger.info("Installing apt packages...")
        package_names = []
        for package in packages:
            if isinstance(package, str):
                # Simple package name without version
                pkg_name = package
                package_names.append(pkg_name)
            else:
                self.logger.warning(f"Invalid apt package format: {package}")
                continue

        if package_names:
            # Update package index
            cmd = ["sudo", "apt-get", "update"]
            self.logger.info("Updating apt package index...")
            try:
                Shell.run_command(cmd, verbose=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to update apt package index: {e}")
                pass

            # Install packages
            cmd = ["sudo", "apt-get", "install", "-y"] + package_names
            self.logger.info(f"Installing apt packages: {', '.join(package_names)}")
            try:
                Shell.run_command(cmd, verbose=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install apt packages: {e}")
                # Decide whether to proceed or exit
                pass

    def _install_pip_packages(self, packages: List[Any]):
        """Install pip packages from a given list"""
        self.logger.info("Installing pip packages...")
        for package in packages:
            if isinstance(package, str):
                # Simple package name without version
                pkg_full_name = package
            elif isinstance(package, dict):
                # Package with version specified
                if len(package) != 1:
                    self.logger.warning(f"Invalid pip package format: {package}")
                    continue
                pkg_name, pkg_version = next(iter(package.items()))
                pkg_full_name = f"{pkg_name}=={pkg_version}"
            else:
                self.logger.warning(f"Invalid pip package format: {package}")
                continue

            self.logger.info(f"Installing pip package: {pkg_full_name}")
            try:
                if self.pip_install_method == "user":
                    cmd = ["pip", "install", "--user", pkg_full_name]
                elif self.pip_install_method == "pipx":
                    cmd = ["pipx", "install", pkg_full_name]
                elif self.pip_install_method == "venv":
                    # TODO: Implement virtual environment setup and installation
                    pass
                else:
                    self.logger.error(
                        f"Unknown pip installation method: {self.pip_install_method}"
                    )
                    continue

                Shell.run_command(cmd, verbose=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install pip package {pkg_full_name}: {e}")
                # Decide whether to continue or stop on error
                continue


    def _install_brew_packages(self, packages: List[Any]):
        """Install homebrew packages from a given list"""
        self.logger.info("Installing homebrew packages...")
        package_names = []
        for package in packages:
            if isinstance(package, str):
                # Simple package name without version
                packages.append(package)
            elif isinstance(package, dict):
                # Package with version specified
                if len(package) != 1:
                    self.logger.warning(f"Invalid homebrew package format: {package}")
                    continue
                pkg_name, pkg_version = next(iter(package.items()))
                package_names.append(f"{pkg_name}@{pkg_version}")
            else:
                self.logger.warning(f"Invalid homebrew package format: {package}")
                continue

        if package_names:
            # Update package index
            self.logger.info("Updating brew package index...")
            try:
                cmd = ["brew", "update"]
                Shell.run_command(cmd, verbose=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to update brew package index: {e}")
                pass

            # Install packages
            cmd = ["brew", "install"] + package_names
            self.logger.info(f"Installing brew packages: {', '.join(package_names)}")
            try:
                Shell.run_command(cmd, verbose=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install brew packages: {e}")
                pass

    def install_ros2(self):
        """Install given ROS 2 distro using available OS-specific install scripts"""
        # Determine available scripts based on OS and ROS distro
        if platform.system().lower() == "darwin":
            os_name = "macos"
        elif platform.system().lower() == "linux":
            if "ubuntu" in platform.uname().version.lower():
                os_name = "ubuntu"
            else:
                os_name = "linux"
        else:
            os_name = sys.platform

        # Get the desired ros distribution from the context
        ros_distro = self.context["ARCSCFG_ROS_DISTRO"]

        scripts = self._get_available_ros_install_scripts(os_name, ros_distro)

        if not scripts:
            self.logger.error(f"No installation scripts available for OS: {os_name} and ROS distro: {ros_distro}")
            sys.exit(1)

        # Prompt user to select a script
        script_path = self._prompt_script_selection(scripts)

        # Execute the selected script
        executor = ScriptExecutor(script_path, self.logger, self.context)
        try:
            executor.execute()
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            sys.exit(1)

    def _get_available_ros_install_scripts(self, os_name: str, ros_distro: str) -> List[Path]:
        """Get available ROS 2 install scripts for given OS/ROS distro"""
        scripts_dir = Path(__file__).parent.parent / 'config' / 'scripts'
        pattern = f"install_ros2_{ros_distro}_{os_name}_*.yaml"
        return list(scripts_dir.glob(pattern))

    def _prompt_script_selection(self, scripts: List[Path]) -> Path:
        """Prompt user for install script given list of script paths"""
        options = [f"{script.name}" for script in scripts]
        selection = self.user_prompter.prompt_selection(
            message="Select an installation script:",
            options=options,
            default=1,
        )
        return scripts[selection]
