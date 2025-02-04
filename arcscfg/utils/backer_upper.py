import shutil
from pathlib import Path
from typing import Optional

from .logger import Logger


class BackerUpper:
    """
    A utility class for backing up files. It manages backup copies of specified files
    by storing them in a designated backup directory and maintaining a fixed number
    of backups using a rotation mechanism similar to RotatingFileHandler.

    Example Usage:
        backer_upper = BackerUpper(backup_dir=".arcscfg_backups", backup_count=5)
        backer_upper.backup("/path/to/important_data.txt")
    """

    def __init__(
        self,
        backup_dir: str = ".arcscfg_backups",
        backup_count: int = 10,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the BackerUpper.

        Args:
            backup_dir (str): Name of the backup directory to store backups.
                              This directory will be created inside the original file's directory.
            backup_count (int): Maximum number of backups to retain per file.
            logger (Logger, optional): An instance of the Logger class for logging.
                                       If not provided, a default Logger is initialized.
        """
        self.backup_dir_name = backup_dir
        self.backup_count = backup_count
        self.logger = logger or Logger(
            verbosity="info",
            log_file_path=None,
            max_bytes=5 * 1024 * 1024,  # 5 MB
            backup_count=backup_count,
        )

    def backup(self, file_path: Path):
        """
        Backup the specified file. Creates a backup copy in the backup directory.
        Maintains only the latest `backup_count` backups by deleting older ones.

        Args:
            file_path (Path): The path to the file that needs to be backed up.
        """
        if not file_path.is_file():
            self.logger.error(f"File to backup does not exist: {file_path}")
            return

        backup_dir = file_path.parent / self.backup_dir_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Backup directory set to: {backup_dir}")

        backup_base = backup_dir / file_path.name

        # Rotate existing backups
        for i in range(self.backup_count, 0, -1):
            src = backup_base.with_suffix(f"{file_path.suffix}.{i}")
            dst = backup_base.with_suffix(f"{file_path.suffix}.{i + 1}")
            if src.exists():
                if i == self.backup_count:
                    self.logger.debug(f"Removing oldest backup: {src}")
                    try:
                        src.unlink()
                        self.logger.debug(f"Deleted old backup: {src}")
                    except Exception as e:
                        self.logger.error(f"Failed to delete {src}: {e}")
                else:
                    self.logger.debug(f"Renaming backup {src} to {dst}")
                    try:
                        src.rename(dst)
                        self.logger.debug(f"Rotated backup: {src} -> {dst}")
                    except Exception as e:
                        self.logger.error(f"Failed to rotate {src} to {dst}: {e}")

        # Create new backup (.1)
        new_backup = backup_base.with_suffix(f"{file_path.suffix}.1")
        try:
            shutil.copy2(file_path, new_backup)
            self.logger.debug(f"Created backup: {new_backup}")
        except Exception as e:
            self.logger.error(f"Failed to backup {file_path} to {new_backup}: {e}")
