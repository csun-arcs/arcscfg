import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .logger import Logger
from .shell import Shell


class DependencyManager:
    def __init__(
        self,
        dependencies_file: Optional[Union[str, Path]] = None,
        logger: Optional[Logger] = None,
        assume_yes: bool = False,
        pip_install_method: str = "user",  # Options: 'user', 'pipx', 'venv'
    ):
        if dependencies_file:
            self.dependencies_file = Path(dependencies_file)
        else:
            self.dependencies_file = None
        self.logger = logger or Logger()
        self.assume_yes = assume_yes
        self.pip_install_method = pip_install_method
        self.dependencies = {}  # type: Dict[str, Any]

    def load_dependencies(self):
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
            self.dependencies = yaml.safe_load(f)
        self.logger.debug(f"Loaded dependencies: {self.dependencies}")

    def install_dependencies(self):
        if not self.dependencies_file:
            self.logger.error("No dependencies file provided.")
            raise ValueError("Dependencies file not set.")
        self.load_dependencies()

        if "apt" in self.dependencies:
            self.install_apt_packages(self.dependencies["apt"])
        if "pip" in self.dependencies:
            self.install_pip_packages(self.dependencies["pip"])

    def install_apt_packages(self, packages: List[Any]):
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
                # Decide whether to proceed or exit
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

    def install_pip_packages(self, packages: List[Any]):
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
                    # Implement virtual environment setup and installation
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

    def install_ros2(self, ros_distro: str):
        """
        Install the specified ROS 2 distribution.

        Args:
            ros_distro (str): The ROS 2 distribution to install (e.g., 'foxy',
            'galactic', 'humble').
        """
        self.logger.info(f"Starting installation of ROS 2 '{ros_distro}'...")

        # Check if ROS 2 is already installed
        if self._is_ros2_installed(ros_distro):
            self.logger.info(f"ROS 2 distribution '{ros_distro}' is already installed.")
            return

        try:
            # Step 1: Add the ROS 2 apt repository and keys
            self._add_ros2_repository()

            # Step 2: Install the ROS 2 packages
            ros_package = f"ros-{ros_distro}-desktop"
            self.logger.info(f"Installing ROS 2 package: {ros_package}")
            cmd = ["sudo", "apt-get", "install", "-y", ros_package]
            Shell.run_command(cmd, verbose=True)

            # Step 3: Initialize rosdep
            self._initialize_rosdep()

            self.logger.info(f"ROS 2 '{ros_distro}' installed successfully.")
        except Exception as e:
            self.logger.error(f"Failed to install ROS 2 '{ros_distro}': {e}")
            raise

    def _add_ros2_repository(self):
        """
        Add the ROS 2 apt repository and keys to the system.
        """
        self.logger.info("Adding ROS 2 apt repository and keys...")
        # Update the package index
        Shell.run_command(["sudo", "apt-get", "update"], verbose=True)

        # Install curl if not installed
        Shell.run_command(
            ["sudo", "apt-get", "install", "-y", "curl", "gnupg2", "lsb-release"],
            verbose=True,
        )

        # Add the ROS 2 GPG key
        Shell.run_command(
            [
                "sudo",
                "curl",
                "-sSL",
                "https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc",
                "-o",
                "/usr/share/keyrings/ros-archive-keyring.gpg",
            ],
            verbose=True,
        )

        # Add the ROS 2 apt repository
        distro_codename = Shell.run_command(
            ["lsb_release", "-cs"], capture_output=True, text=True
        ).stdout.strip()

        repo_entry = (
            f"deb [arch=$(dpkg --print-architecture) "
            f"signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] "
            f"http://packages.ros.org/ros2/ubuntu {distro_codename} main"
        )

        cmd = (
            f'echo "{repo_entry}" | '
            f"sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null"
        )
        Shell.run_command(cmd, shell=True, verbose=True)

        # Update the package index again
        Shell.run_command(["sudo", "apt-get", "update"], verbose=True)

    def _initialize_rosdep(self):
        """
        Initialize rosdep for dependency management.
        """
        self.logger.info("Initializing rosdep...")
        try:
            Shell.run_command(["sudo", "rosdep", "init"], verbose=True)
        except subprocess.CalledProcessError as e:
            if "rosdep already initialized" in e.stderr.lower():
                self.logger.info("rosdep is already initialized.")
            else:
                raise e
        Shell.run_command(["rosdep", "update"], verbose=True)

    def _is_ros2_installed(self, ros_distro: str) -> bool:
        """
        Check if the ROS 2 distribution is already installed.

        Args:
            ros_distro (str): The ROS 2 distribution to check.

        Returns:
            bool: True if installed, False otherwise.
        """
        ros_version_file = Path(f"/opt/ros/{ros_distro}/setup.bash")
        return ros_version_file.exists()
