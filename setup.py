# arcscfg/setup.py

from setuptools import setup, find_packages

setup(
    name="arcscfg",
    version="0.1.0",
    packages=find_packages(include=["arcscfg", "arcscfg.*"]),
    include_package_data=True,
    install_requires=[
        "setuptools", # For installation
        "pyyaml", # For YAML parsing
        "pytest", # For testing
        "colorlog", # For colored logging
        "appdirs", # For finding log dirs on different systems
        "colcon-common-extensions" # For ROS 2 builds
    ],
    entry_points={
        "console_scripts": [
            "arcscfg = arcscfg.cli:main",
        ],
    },
)
