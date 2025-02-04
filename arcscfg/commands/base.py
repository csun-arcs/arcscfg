from abc import ABC, abstractmethod
from typing import Optional

from arcscfg.utils.backer_upper import BackerUpper
from arcscfg.utils.user_prompter import UserPrompter


class BaseCommand(ABC):
    """
    Abstract base class for all commands.
    """

    def __init__(self,
               args,
               logger,
               backer_upper: Optional[BackerUpper] = None,
               user_prompter: Optional[UserPrompter] = None
               ):
        self.args = args
        self.logger = logger
        self.backer_upper = backer_upper
        self.user_prompter = user_prompter

    @abstractmethod
    def execute(self):
        """
        Execute the command logic.
        """
        pass
