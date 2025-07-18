<!-- arcscfg/README.md -->

# CSUN ARCS Configurator

*arcscfg* is a command-line tool designed to streamline the management of ROS-based robotics projects at the Autonomy Research Center for STEAHM (ARCS) at California State University, Northridge (CSUN). It facilitates workspace setup, dependency management, build processes, and configuration of developer environments, ensuring consistency and efficiency across projects.

## Features

- **Dependency Handling**: Automate the installation ROS 2, as well as of system and Python dependencies using *apt* and *pip*.
- **Workspace Management**: Easily set up and manage ROS 2 workspaces with predefined configurations.
- **Build Automation**: Streamline the build process using *colcon* with detailed logging.
- **Environment Configuration**: Configure shell environments (*bash*, *zsh*) with necessary setup scripts.
- **Dotfile Management**: Manage and update shell configuration files and Git hooks consistently across repositories.
- **Logging and Debugging**: Comprehensive logging with configurable verbosity levels and log file rotation.
- **Extensibility**: Modular command structure allows for easy addition of new functionalities.

## Prerequisites
<details>

Before installing =arcscfg=, ensure your system meets the following requirements:

- **Operating System**: Recommended: [Ubuntu 24.04 LTS (Noble Numbat)](https://releases.ubuntu.com/noble/) for a [ROS 2 Jazzy Jalisco](https://docs.ros.org/en/jazzy/index.html) installation.
  - **NOTE**: We may attempt to support MacOS and Windows installations of ROS 2 in the future, either natively or via [Docker](https://www.docker.com/) containers.  Until then, here are some possible options:
    - **MacOS**:
      - Virtual Machines: [VirtualBox](https://www.virtualbox.org/) (free / open-source) or Parallels (https://www.parallels.com/) (paid / proprietary).
    - **Windows**:
      - Virtual Machines: [VirtualBox](https://www.virtualbox.org/).
      - Windows Subsystem for Linux (WSL): [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).
- **Python**: Python 3.8 or higher.
- **ROS 2**: Recommended to have ROS 2 installed. *arcscfg* can assist in installing ROS 2 distributions. [ROS 2 Jazzy Jalisco](https://docs.ros.org/en/jazzy/index.html) is recommended.
- **System Dependencies**: `git`, `curl`, and other build-essential packages.
</details>

## Installation

### Quickstart

Install [pyenv](https://github.com/pyenv/pyenv):

```bash
curl -fsSL https://pyenv.run | bash
```

Configure `pyenv` for a `bash` shell environment:

```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
source ~/.bashrc
```

Install `pyenv` Python version that matches system version:

```bash
pyenv install `python3 --version | sed 's/Python //'`
```

Set up and activate `pyenv` virtual environment for `arcscfg`:

```bash
pyenv virtualenv `python3 --version | sed 's/Python //'` arcscfg
pyenv activate arcscfg
```

Clone and install `arcscfg` in `pyenv` virtual environment:

```bash
git clone https://github.com/csun-arcs/arcscfg.git
cd arcscfg
pip install -e .
```

### Virtual Environments

<details>

It's recommended to use a virtual environment to avoid conflicts with other Python packages.

[venv](https://docs.python.org/3/library/venv.html), [virtualenv](https://virtualenv.pypa.io/en/latest/user_guide.html), [virtualenvwrapper](https://pypi.org/project/virtualenvwrapper/), [pipenv](https://pipenv.pypa.io/en/latest/) and [pyenv](https://python.land/virtual-environments/pyenv) / [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) are all good options for this.

Here is an example using `venv`:

1. **Create a Virtual Environment**:

   ```bash
   python3 -m venv arcscfg_env
   ```

2. **Activate the Virtual Environment**:

   - **Bash/Zsh**:

     ```bash
     source arcscfg_env/bin/activate
     ```

   - **Fish**:

     ```bash
     source arcscfg_env/bin/activate.fish
     ```

3. **Install arcscfg Within the Virtual Environment**:

   ```bash
   pip install .
   ```

</details>

### Using pip

<details>

Another possible way to install =arcscfg= is via *pip*, although its usage tends to restricted by default on more recent Ubuntu distributions. Ensure you have Python and `pip` installed on your system.

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/csun-arcs/arcscfg.git
   cd arcscfg
   ```

2. **Install via pip**:

   ```bash
   pip install .
   ```

   *Note*: You might need to use `pip3` instead of `pip` depending on your system configuration.

</details>

### From Source

<details>

To install `arcscfg` from source:

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/csun-arcs/arcscfg.git
   cd arcscfg
   ```
2. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install the Package**:

   ```bash
   python setup.py install
   ```

</details>

## Usage

Usage instructions can be found in the [arcscfg wiki](https://github.com/csun-arcs/arcscfg/wiki).
