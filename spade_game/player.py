import json
from typing import Optional, Union, List, Dict, Any

from spade.agent import Agent
from spade.message import Message
from spade.behaviour import FSMBehaviour, State

# State definitions
STATE_CONNECT = "STATE_CONNECT"
STATE_INPUT = "STATE_INPUT"
STATE_ACTION = "STATE_ACTION"
STATE_OUTPUT = "STATE_OUTPUT"
STATE_DISCONNECT = "STATE_DISCONNECT" # TO-DO ?

# Player States
class Connect(State):
    async def run(self):
        body = {
            "type": "connect",
            "info": self.agent.initial_attributes,
        }

        msg = Message(
            to=str(self.agent.server_jid),
            sender=str(self.agent.jid),
            body=json.dumps(body),
            metadata={"performative": "inform"}
        )

        await self.send(msg)
        self.set_next_state(STATE_INPUT)

class Input(State):
    async def run(self):
        msg = await self.receive()
        if msg:
            self.agent.decode_message(msg)
            self.set_next_state(STATE_ACTION)
        else:
            self.set_next_state(STATE_INPUT)

class Action(State):
    async def run(self):
        self.agent.decide_action()
        self.set_next_state(STATE_OUTPUT)

class Output(State):
    async def run(self):
        body = {
            "type": "action",
            "info": self.agent.action
        }
        
        msg = Message(
            to=str(self.agent.server_jid),
            sender=str(self.agent.jid),
            body=json.dumps(body),
            metadata={"performative": "inform"}
        )

        await self.send(msg)
        self.set_next_state(STATE_INPUT)

# Player Agent
class Player(Agent):
    def __init__(self, 
                 jid: str,
                 password: str,
                 server_jid: str,
                 initial_attributes: Optional[Dict[str, Any]] = {},
                 verify_security: Optional[bool] = False) -> None:
        super().__init__(jid, password, verify_security)
        self.server_jid = server_jid
        self.initial_attributes = initial_attributes
        self.world_model = {}
        self.action = None

    async def setup(self) -> None:
        fsm = FSMBehaviour()
        fsm.add_state(name=STATE_CONNECT, state=Connect(), initial=True)
        fsm.add_state(name=STATE_INPUT, state=Input())
        fsm.add_state(name=STATE_ACTION, state=Action())
        fsm.add_state(name=STATE_OUTPUT, state=Output())
        fsm.add_transition(source=STATE_CONNECT, dest=STATE_INPUT)
        fsm.add_transition(source=STATE_INPUT, dest=STATE_INPUT)
        fsm.add_transition(source=STATE_INPUT, dest=STATE_ACTION)
        fsm.add_transition(source=STATE_ACTION, dest=STATE_OUTPUT)
        fsm.add_transition(source=STATE_OUTPUT, dest=STATE_INPUT)
        self.add_behaviour(fsm)

    def decide_action(self) -> Union[Dict[str, Any], Any]:
        raise NotImplementedError("Subclasses must implement this")
    
    def decode_message(self, message: Message) -> None:
        sender_jid = str(message.sender)
        content = json.loads(message.body)

        if content["type"] == "update":
            self._process_update(sender_jid, content["info"])
        else:
            # TO-DO: error message should be sent here
            return
        
    def _process_update(self, sender_jid: str, content: Dict[str, Any]) -> None:
        if sender_jid == self.server_jid:
            self.world_model = content
        else:
            # TO-DO: error message (update is not from server)
            return