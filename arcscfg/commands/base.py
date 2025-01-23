from abc import ABC, abstractmethod


class BaseCommand(ABC):
    """
    Abstract base class for all commands.
    """

    def __init__(self, args, logger):
        self.args = args
        self.logger = logger

    @abstractmethod
    def execute(self):
        """
        Execute the command logic.
        """
        pass
