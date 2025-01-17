import logging
import datetime
import colorlog
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from appdirs import user_log_dir


class Logger:
    """A utility class for logger creation.  Supports both console streaming and
    log file handling, as well as log file rotation.  Also supports log file
    creation in default system folders (using appdirs) if no log file path is
    provided."""

    def __init__(
        self,
        log_file_path: Optional[Path] = None,
        verbosity: str = "info",
        project_name: str = "arcscfg",
        max_bytes: int = 5 * 1024 * 1024,  # 5 MB
        backup_count: int = 5
    ):
        """
        Args:
            log_file_path (Path, optional): Path to the log file or directory.
                If a directory is provided, a timestamped log file is created
                within it. Default: None, which uses a canonical default
                location via appdirs.
            verbosity (str): Logging level for console ('debug', 'info',
                'warning', 'error', 'critical', 'silent').
            project_name (str): Base name for log files when `log_file_path` is
                a directory or None.
            max_bytes (int): Maximum size in bytes before a log file is rotated.
            backup_count (int): Number of backup log files to keep.
        """
        # Capture the logger by the project name (as in original code).
        self._logger = logging.getLogger(project_name)
        self._logger.setLevel(logging.DEBUG)  # capture all levels

        # Remove existing handlers to avoid duplicates if re-initializing
        if self._logger.hasHandlers():
            self._logger.handlers.clear()

        # Define log levels
        level_mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "silent": logging.CRITICAL + 10  # beyond CRITICAL = "silent"
        }
        console_level = level_mapping.get(verbosity.lower(), logging.INFO)

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
        self._logger.addHandler(console_handler)

        # Determine the final log file path based on original logic
        final_log_path = self._determine_log_path(
            log_file_path=log_file_path,
            project_name=project_name
        )

        # Ensure the final file actually exists
        final_log_path.touch(exist_ok=True)

        # Rotating File Handler
        file_handler = RotatingFileHandler(
            final_log_path,
            mode='a',
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
            delay=False
        )
        file_handler.setLevel(logging.DEBUG)  # log everything to file
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)

        self._logger.debug(
            f"Logging to file: {final_log_path} with rotation "
            f"maxBytes={max_bytes}, backupCount={backup_count}"
        )

        # Prevent logs from propagating to the root logger
        self._logger.propagate = False

    def _determine_log_path(self,
                          log_file_path: Optional[Path],
                          project_name: str) -> Path:
        """
        Internal helper for figuring out the final log file path, including
        'directory -> timestamped file' logic and default location if None is
        provided.
        """
        # If no path was provided, use canonical default location via appdirs
        if not log_file_path:
            log_dir = Path(user_log_dir(appname=project_name, appauthor=False))
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = log_dir / f"{project_name}.log"

        # Expand and resolve user path
        log_file_path = log_file_path.expanduser().resolve()

        # If path exists
        if log_file_path.exists():
            if log_file_path.is_dir():
                # Directory -> generate timestamped filename
                timestamp = datetime.datetime.now().strftime(
                    "%Y-%m-%d-%H-%M-%S")
                return log_file_path / f"{project_name}-{timestamp}.log"
            elif log_file_path.is_file():
                # It's a file -> use directly
                return log_file_path
        else:
            # Path doesn't exist
            if log_file_path.suffix:
                # It's a file path
                log_file_path.parent.mkdir(parents=True, exist_ok=True)
                return log_file_path
            else:
                # It's intended as a directory
                log_file_path.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.datetime.now().strftime(
                    "%Y-%m-%d-%H-%M-%S")
                return log_file_path / f"{project_name}-{timestamp}.log"

        # Fallback (should never hit here logically)
        return log_file_path

    def __getattr__(self, name: str):
        """
        Delegate attribute access to the underlying `logging.Logger`.  So calls
        like `logger.info(...)` go straight to `self._logger.info(...)`.
        """
        return getattr(self._logger, name)
