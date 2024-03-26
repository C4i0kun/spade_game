import json
from datetime import datetime, timedelta
from typing import Optional, Union, List, Dict, Any

from spade.agent import Agent
from spade.message import Message
from spade.behaviour import FSMBehaviour, State

from .exceptions import (
    MessageTypeError,
    PlayerAlreadyConnectedError,
    PlayerNotFoundError,
    InvalidContentError,
)

# State definitions
STATE_INPUT = "STATE_INPUT"
STATE_STEP = "STATE_STEP"
STATE_OUTPUT = "STATE_OUTPUT"


# Server States
class Input(State):
    async def run(self):
        if datetime.now() > self.agent.next_step_time:
            self.set_next_state(STATE_STEP)
        else:
            msg = await self.receive()
            if msg:
                try:
                    self.agent.decode_message(msg)
                except Exception as e:
                    print(
                        "[{}] Error in message received: {}".format(
                            str(self.agent.jid), e
                        )
                    )
            self.set_next_state(STATE_INPUT)


class Step(State):
    async def run(self):
        self.agent.step()
        self.set_next_state(STATE_OUTPUT)


class Output(State):
    async def run(self):
        if self.agent.end_condition():
            await self._disconnect_all_players()
            print("[{}] Game ended. Stopping server...".format(str(self.agent.jid)))
            await self.agent.stop()
        else:
            await self._update_all_players()
            self.agent.next_step_time = datetime.now() + self.agent.period_timedelta
            self.set_next_state(STATE_INPUT)

    async def _send_update_message(self, player) -> None:
        player_jid = player["jid"]
        player_data = player.copy()
        del player_data["jid"]  # no need to send player jid
        body = {"type": "update", "info": player_data}
        msg = Message(
            to=str(player_jid),
            sender=str(self.agent.jid),
            body=json.dumps(body),
            metadata={"performative": "inform"},
        )
        await self.send(msg)

    async def _update_player(self, player_jid) -> None:
        player = self.agent._find_player(player_jid)
        if player is not None:
            await self._send_update_message(player)

    async def _update_all_players(self) -> None:
        for player in self.agent.world_model["players"]:
            await self._send_update_message(player)

    async def _disconnect_all_players(self) -> None:
        for player in self.agent.world_model["players"]:
            player_jid = player["jid"]
            body = {"type": "disconnect"}
            msg = Message(
                to=str(player_jid),
                sender=str(self.agent.jid),
                body=json.dumps(body),
                metadata={"performative": "inform"},
            )
            await self.send(msg)

            # remove player from player list
            self.agent._process_disconnection(player_jid)


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
    ) -> None:
        super().__init__(jid, password, verify_security)
        self.period_timedelta = timedelta(milliseconds=1000 / frequency)
        self.next_step_time = datetime.now() + self.period_timedelta

        # initialize world model
        self.world_model = game_attributes.copy()
        self.world_model["players"] = []

        # set list of params to return
        self.player_attributes = player_attributes

        # set connection attributes
        self.connection_attributes = [
            attr
            for attr in list(player_attributes.keys())
            if player_attributes[attr] is None
        ]

        # set action attributes
        self.action_attributes = action_atrributes

    async def setup(self) -> None:
        fsm = FSMBehaviour()
        fsm.add_state(name=STATE_INPUT, state=Input(), initial=True)
        fsm.add_state(name=STATE_STEP, state=Step())
        fsm.add_state(name=STATE_OUTPUT, state=Output())
        fsm.add_transition(source=STATE_INPUT, dest=STATE_INPUT)
        fsm.add_transition(source=STATE_INPUT, dest=STATE_STEP)
        fsm.add_transition(source=STATE_STEP, dest=STATE_OUTPUT)
        fsm.add_transition(source=STATE_OUTPUT, dest=STATE_INPUT)
        self.add_behaviour(fsm)

    def step(self) -> None:
        raise NotImplementedError("Subclasses must implement this.")

    def end_condition(self) -> bool:
        raise NotImplementedError("Subclasses must implement this.")

    def decode_message(self, message: Message) -> None:
        sender_jid = str(message.sender)
        content = json.loads(message.body)

        if content["type"] == "connect":
            self._process_connection(sender_jid, content["info"])
        elif content["type"] == "disconnect":
            self._process_disconnection(sender_jid)
        elif content["type"] == "action":
            self._process_action(sender_jid, content["info"])
        else:
            raise MessageTypeError(content["type"])

    def _process_connection(self, sender_jid: str, content: Dict[str, Any]) -> None:
        # check if player is already connected
        if self._find_player(sender_jid) is not None:
            raise PlayerAlreadyConnectedError(sender_jid)

        # check if data necessary for connection is being received
        if list(content.keys()) == self.connection_attributes:
            # initialize player data
            player_data = self.player_attributes.copy()
            for key, value in player_data.items():
                if value is None:
                    player_data[key] = content[key]
            player_data["jid"] = str(sender_jid)
            player_data["action"] = None

            # add player data to world model
            self.world_model["players"].append(player_data)
        else:
            raise InvalidContentError(
                "connect", list(content.keys()), self.connection_attributes
            )

    def _process_disconnection(self, sender_jid: str) -> None:
        player = self._find_player(sender_jid)

        if player is None:
            raise PlayerNotFoundError(sender_jid)
        else:
            self.world_model["players"].remove(player)
            print("[{}] Player {} disconnected.".format(str(self.jid), sender_jid))

    def _process_action(
        self, sender_jid: str, content: Union[Dict[str, Any], Any]
    ) -> None:
        player = self._find_player(sender_jid)

        if player is None:
            raise PlayerNotFoundError(sender_jid)
        else:
            if isinstance(content, dict):
                # check if action has the expected attributes
                if list(content.keys()) != self.action_attributes:
                    raise InvalidContentError(
                        "action", list(content.keys()), self.action_attributes
                    )
            if self._is_action_valid(content):
                player["action"] = content
            else:
                print(
                    "[{}] Player {} sent an invalid action, so it's being disconsidered.".format(
                        str(self.jid), sender_jid
                    )
                )

    def _is_action_valid(self, content: Union[Dict[str, Any], Any]) -> bool:
        return True

    def _find_player(self, player_jid) -> Union[Dict[str, Any], None]:
        # look for player in world model
        for player in self.world_model["players"]:
            if player["jid"] == player_jid:
                return player
        return None
