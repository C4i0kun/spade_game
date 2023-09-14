import json
from datetime import datetime, timedelta
from typing import Optional, Union, List, Dict, Any

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
                self.agent.decode_message(msg)
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
    def __init__(
        self,
        jid: str,
        password: str,
        game_attributes: Dict[str, Any],
        player_attributes: Dict[str, Any],
        action_atrributes: Optional[List[str]] = None,
        frequency: Optional[int] = 10,
        verify_security: Optional[bool] = False,
    ):
        super().__init__(jid, password, verify_security)
        self.period_timedelta = timedelta(milliseconds=1000 / frequency)
        self.next_step_time = datetime.now() + self.period_timedelta

        # initialize world model
        self.world_model = game_attributes.copy()
        self.world_model["players"] = []

        # set list of params to return
        self.player_attributes = list(player_attributes.keys())

        # set connection attributes
        self.connection_attributes = [
            attr
            for attr in list(player_attributes.keys())
            if player_attributes[attr] is None
        ]

        # set action attributes
        self.action_attributes = action_atrributes

    def step(self):
        raise NotImplementedError("Subclasses must implement this")

    def decode_message(self, message: str):
        sender_jid = message.sender
        content = json.loads(message.body)

        if content["type"] == "connect":
            self._process_connection(sender_jid, content["info"])
        elif content["type"] == "disconnect":
            self._process_disconnection(sender_jid, content["info"])
        elif content["type"] == "action":
            self._process_action(sender_jid, content["action"])
        else:
            # TO-DO: error message should be sent here
            return

    def _process_connection(self, sender_jid: str, info: Dict[str, Any]) -> None:
        # check if player is already connected
        if self._find_player(sender_jid) is not None:
            # TO-DO: error message should be sent
            return

        # check if data necessary for connection is being received
        if list(info.keys) == self.connection_attributes:
            # initialize player data
            player_data = self.player_attributes.copy()
            for key, value in player_data.items():
                if value is None:
                    value = info[key]
            player_data["jid"] = sender_jid
            player_data["action"] = None

            # add player data to world model
            self.world_model["players"].append(player_data)
        else:
            # TO-DO: error message should be sent here
            return

    def _process_disconnection(self, sender_jid: str, info: Dict[str, Any]) -> None:
        player = self._find_player(sender_jid)

        if player is None:
            # TO-DO: error message should be sent here
            return
        else:
            self.world_model["players"].remove(player)
            # TO-DO: disconnection message here

    def _process_action(
        self, sender_jid: str, info: Union[Dict[str, Any], Any]
    ) -> None:
        player = self._find_player(sender_jid)

        if player is None:
            # TO-DO: error message should be sent here
            return
        else:
            if isinstance(info, dict):
                # check if action has the expected attributes
                if list(info.keys) != self.action_attributes:
                    # TO-DO: error message should be sent here
                    return
            player["action"] = info

    def _find_player(self, player_jid) -> Union[Dict[str, Any], None]:
        # look for player in world model
        for player in self.world_model["players"]:
            if player["jid"] == player_jid:
                return player
        return None
