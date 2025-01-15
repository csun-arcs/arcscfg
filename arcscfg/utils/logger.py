import logging
import colorlog
import datetime
from pathlib import Path
from typing import Optional
from appdirs import user_log_dir

def setup_logger(log_file_path: Optional[Path] = None,
               verbosity: str = "info",
               project_name: str = "arcscfg") -> logging.Logger:
    """Set up a logger that logs to the console and a file with colored output.

    Args:
        log_file_path (Path, optional): Path to the log file or directory.  If a
            directory is provided, a timestamped log file is created within it.
            Default: None, which uses a canonical default location.
        verbosity (str): Logging level ('debug', 'info', 'warning', 'error',
            'critical', 'silent').
        project_name (str): Base name for the log files when a directory is
            provided.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger("arcscfg")
    logger.setLevel(logging.DEBUG)  # Capture all levels; control via handlers

    # Define log levels
    level_mapping = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "silent": logging.CRITICAL + 10  # Effectively silences the logger
    }

    console_level = level_mapping.get(verbosity.lower(), logging.INFO)

    # Remove existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console handler with colored output
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Determine default log file path if not provided
    if not log_file_path:
        log_dir = Path(user_log_dir(appname=project_name, appauthor=False))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / f"{project_name}.log"

    log_file_path = log_file_path.expanduser().resolve()

    if log_file_path.exists():
        if log_file_path.is_dir():
            # Path is a directory that exists
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            log_filename = f"{project_name}-{timestamp}.log"
            final_log_path = log_file_path / log_filename
        elif log_file_path.is_file():
            final_log_path = log_file_path
        else:
            # Neither file nor directory; treat as file path
            final_log_path = log_file_path
    else:
        # Path does not exist
        if log_file_path.suffix:  # Likely a file path
            # Check if parent directory exists
            parent_dir = log_file_path.parent
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    print(f"Created directory: {parent_dir}")
                except Exception as e:
                    logger.error(
                        f"Failed to create directory '{parent_dir}': {e}")
                    raise
            final_log_path = log_file_path
        else:
            # Path without suffix; treat as directory
            try:
                log_file_path.mkdir(parents=True, exist_ok=True)
                print(f"Created directory: {log_file_path}")
            except Exception as e:
                logger.error(
                    f"Failed to create directory '{log_file_path}': {e}")
                raise
            # Directory exists now; create log file with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            log_filename = f"{project_name}-{timestamp}.log"
            final_log_path = log_file_path / log_filename

    try:
        # Ensure the log file exists
        final_log_path.touch(exist_ok=True)
    except Exception as e:
        logger.error(
            f"Failed to create or access log file '{final_log_path}': {e}")
        raise

    # File handler with rotation (to be detailed in the next section)
    file_handler = logging.FileHandler(final_log_path, mode='a')
    file_handler.setLevel(logging.DEBUG)  # Log everything to the file
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.debug(f"Logging to file: {final_log_path}")

    # Prevent logging from propagating to the root logger
    logger.propagate = False

    return logger
