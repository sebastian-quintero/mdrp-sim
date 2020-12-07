from dataclasses import dataclass
from typing import Optional

from simpy import Environment, Process

from utils.logging_utils import log, configure_logs


@dataclass
class Actor:
    """A class used to handle the standard structure of an actor's state and events"""

    configure_logs()

    env: Optional[Environment] = Environment()
    state: Optional[Process] = None
    condition: str = ''

    def __post_init__(self):
        """Immediately after the actor is created, it starts idling"""

        self._log('Actor logged on')

        self.state = self.env.process(self._idle_state())

    def _idle_state(self):
        """State that simulates the actor being idle and waiting for events"""

        yield

    def _log(self, msg: str):
        """Method to log detailed information of the actor's actions"""

        log(env=self.env, actor_name=self.__class__.__name__, condition=self.condition, msg=msg)
