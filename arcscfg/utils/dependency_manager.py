import subprocess
from pathlib import Path
from string import Template
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
        context: Optional[Dict[str, str]] = None,  # Context for template substitution
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
        if not self.dependencies_file:
            self.logger.error("No dependencies file provided.")
            raise ValueError("Dependencies file not set.")
        self.load_dependencies()

        if "apt" in self.dependencies:
            self._install_apt_packages(self.dependencies["apt"])
        if "pip" in self.dependencies:
            self._install_pip_packages(self.dependencies["pip"])

    def _install_apt_packages(self, packages: List[Any]):
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

    def _install_pip_packages(self, packages: List[Any]):
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
