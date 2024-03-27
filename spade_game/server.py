import json
from datetime import datetime, timedelta
from typing import Optional, Union, List, Dict, Any
from abc import ABC, abstractmethod

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
        if self.agent.step_condition() and self.agent.running_steps:
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
        self.agent.on_step_start()
        self.agent.step()
        self.agent.on_step_end()
        self.set_next_state(STATE_OUTPUT)


class Output(State):
    async def run(self):
        if self.agent.end_condition():
            await self._disconnect_all_players()
            print("[{}] Game ended. Stopping server...".format(str(self.agent.jid)))
            await self.agent.stop()
        else:
            self.agent.on_output_start()
            await self._update_all_players()
            self.agent.on_output_end()
            self.set_next_state(STATE_INPUT)

    async def _send_update_message(self, player) -> None:
        player_jid = player["jid"]
        player_data = player.copy()
        del player_data["jid"]  # no need to send player jid
        for key in list(player_data.keys()):
            if key.startswith("_"):  # delete control attributes
                del player_data[key]
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


# Abstract Server Agent
class Server(Agent, ABC):
    def __init__(
        self,
        jid: str,
        password: str,
        game_attributes: Dict[str, Any],
        player_attributes: Dict[str, Any],
        action_atrributes: Optional[List[str]] = None,
        verify_security: Optional[bool] = False,
    ) -> None:
        super().__init__(jid, password, verify_security)

        # Server starts without running steps
        self.running_steps = False

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

        # List of players who can perform actions and receive updates.
        self.can_perform_action = []
        self.can_receive_update = []

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

    @abstractmethod
    def step_condition(self) -> bool:
        raise NotImplementedError("Subclasses must implement this.")

    @abstractmethod
    def step(self) -> None:
        raise NotImplementedError("Subclasses must implement this.")

    @abstractmethod
    def end_condition(self) -> bool:
        raise NotImplementedError("Subclasses must implement this.")

    def on_step_start(self) -> None:
        pass

    def on_step_end(self) -> None:
        pass

    def on_output_start(self) -> None:
        pass

    def on_output_end(self) -> None:
        pass

    def run_steps(self) -> None:
        self.can_perform_action = self._all_player_jids()
        self.can_receive_update = self._all_player_jids()
        self.running_steps = True

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
        # if game is already running, player can't connect
        if self.running_steps:
            print(
                "[{}] Player {} connection not allowed. Game already started.".format(
                    str(self.jid), sender_jid
                )
            )
            return

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
            player_data["_action_datetime"] = datetime.now()

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
            # the player can be in the list of players who can perform
            # actions or receive updates. We must take it.
            try:
                self.can_perform_action.remove(sender_jid)
                self.can_receive_update.remove(sender_jid)
            except:
                # if it's not, nothing needs to me done.
                pass
            print("[{}] Player {} disconnected.".format(str(self.jid), sender_jid))

    def _process_action(
        self, sender_jid: str, content: Union[Dict[str, Any], Any]
    ) -> None:
        if sender_jid not in self.can_perform_action:
            print(
                "[{}] Player {} is not allowed to perform actions.".format(
                    str(self.jid), sender_jid
                )
            )
            return

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
                player["_action_datetime"] = datetime.now()
                # register action as last performed
                self.world_model["_last_action_performed"] = content
                self.world_model["_last_action_player"] = sender_jid
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

    def _all_player_jids(self) -> Union[List[Dict[str, Any]], None]:
        return [player["jid"] for player in self.world_model["players"]]


# Abstract Continuous Server Agent
class ContinuousServer(Server):
    def __init__(
        self,
        jid: str,
        password: str,
        game_attributes: Dict[str, Any],
        player_attributes: Dict[str, Any],
        action_atrributes: Optional[List[str]] = None,
        verify_security: Optional[bool] = False,
        frequency: Optional[int] = 10,
    ) -> None:
        super().__init__(
            jid,
            password,
            game_attributes,
            player_attributes,
            action_atrributes,
            verify_security,
        )
        self.period_timedelta = timedelta(milliseconds=1000 / frequency)
        self.next_step_time = datetime.now() + self.period_timedelta

    def step_condition(self) -> bool:
        return datetime.now() > self.next_step_time

    def on_output_end(self) -> None:
        self.next_step_time = datetime.now() + self.period_timedelta

    def run_steps(self) -> None:
        self.next_step_time = datetime.now() + self.period_timedelta
        super().run_steps()


# Abstract Turn-Based Server
class TurnBasedServer(Server):
    def __init__(
        self,
        jid: str,
        password: str,
        game_attributes: Dict[str, Any],
        player_attributes: Dict[str, Any],
        action_atrributes: Optional[List[str]] = None,
        verify_security: Optional[bool] = False,
    ) -> None:
        super().__init__(
            jid,
            password,
            game_attributes,
            player_attributes,
            action_atrributes,
            verify_security,
        )
        # initialize first player turn
        self._current_player_jid = None

    def run_steps(self) -> None:
        self._current_player_jid = self._next_player_jid()
        if self._current_player_jid is None:
            print(
                "[{}] Server could not define the next player in the game.".format(
                    str(self.jid),
                )
            )
        else:
            self.running_steps = True

    def _next_player_jid(self) -> Union[str, None]:
        oldest_play_datetime = datetime.now()
        next_player_jid = None

        for player in self.world_model["player"]:
            if player["_action_datetime"] < oldest_play_datetime:
                oldest_play_datetime = player["_action_datetime"]
                next_player_jid = player["jid"]
        return next_player_jid
