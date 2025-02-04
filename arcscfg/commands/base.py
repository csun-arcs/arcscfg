from abc import ABC, abstractmethod
from typing import Optional

from arcscfg.utils.backer_upper import BackerUpper


class BaseCommand(ABC):
    """
    Abstract base class for all commands.
    """

    def __init__(self, args, logger, backer_upper: Optional[BackerUpper]):
        self.args = args
        self.logger = logger
        self.backer_upper = backer_upper

    @abstractmethod
    def execute(self):
        """
        Execute the command logic.
        """
        pass
