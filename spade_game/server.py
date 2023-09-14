from datetime import datetime, timedelta

from spade.agent import Agent
from spade.message import Message
from spade.behaviour import FSMBehaviour, State

# State definitions
STATE_INPUT = "STATE_INPUT"
STATE_STEP = "STATE_STEP"
STATE_OUTPUT = "STATE_OUTPUT"

# Server Finite State Machine


# Server States
class Input(State):
    async def run(self):
        if datetime.now() > self.agent.next_step_time:
            self.set_next_state(STATE_STEP)
        else:
            msg = await self.receive()
            if msg:
                self.agent.update_world_model(msg)
            self.set_next_state(STATE_INPUT)

class Step(State):
    async def run(self):
        self.agent.step()
        self.set_next_state(STATE_OUTPUT)

class Output(State):
    async def run(self):
        # send messages to all players
        self.agent.next_step_time = datetime.now() + self.period_timedelta
        self.set_next_state(STATE_INPUT)

# Server Agent
class Server(Agent):
    def __init__(self, 
                 jid: str,
                 password: str,
                 frequency: int = 10, 
                 verify_security: bool = False):
        super().__init__(jid, password, verify_security)
        self.world_model = {}
        self.period_timedelta = timedelta(milliseconds=1000/frequency)
        self.next_step_time = datetime.now() + self.period_timedelta

    def step(self):
        raise NotImplementedError("Subclasses must implement this")
    