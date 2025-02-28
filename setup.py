# arcscfg/setup.py

from setuptools import setup, find_packages

setup(
    name="arcscfg",
    version="0.1.0",
    packages=find_packages(include=["arcscfg", "arcscfg.*"]),
    include_package_data=True,
    install_requires=[
        "pyyaml", # For YAML parsing
        "colorlog", # For colored logging
        "appdirs", # For finding log dirs on different systems
        "colcon-common-extensions" # For ROS 2 builds
    ],
    extras_require={
        "dev": ["pytest"] # For testing
    },
    entry_points={
        "console_scripts": [
            "arcscfg = arcscfg.cli:main",
        ],
    },
)
