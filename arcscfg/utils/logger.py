import logging
from pathlib import Path
import colorlog

def setup_logger(log_file_path: Path, verbosity: str = "info") -> logging.Logger:
    """Set up a logger that logs to the console and a file with colored output.

    Args:
        log_file_path (Path): Path to the log file.
        verbosity (str): Logging level ('debug', 'info', 'warning', 'error',
    'critical', 'silent').

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

    # File handler (only if verbosity is not silent)
    if verbosity.lower() != "silent":
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)  # Log everything to the file
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent logging from propagating to the root logger
    logger.propagate = False

    return logger
