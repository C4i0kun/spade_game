import random
import numpy as np
from typing import Union, Any, Dict, List

import spade
from spade_game import TurnBasedServer, Player


class GameServer(TurnBasedServer):
    def __init__(
        self,
        jid: str,
        password: str,
        num_players_needed: int,
        game_attributes: Dict[str, Any],
        player_attributes: Dict[str, Any],
        action_atrributes: List[str] | None = None,
        verify_security: bool | None = False,
    ) -> None:
        super().__init__(
            jid,
            password,
            num_players_needed,
            game_attributes,
            player_attributes,
            action_atrributes,
            verify_security,
            frequency=1,
        )
        self.counter = 0
        self.world_model["game_state"] = np.zeros((3, 3)).tolist()

    def step(self) -> None:
        last_action_player_jid = self.world_model["_last_action_player"]
        last_action_player = self._find_player(last_action_player_jid)

        last_action_performed = self.world_model["_last_action_performed"]
        x_index = last_action_performed[0]
        y_index = last_action_performed[1]

        self.world_model["game_state"][x_index][y_index] = last_action_player["type"]

        # update players state
        for player in self.world_model["players"]:
            player["state"] = self.world_model["game_state"].copy()

        print(np.array(self.world_model["game_state"]))

    def end_condition(self) -> bool:
        game_state = np.array(self.world_model["game_state"])
        draw = 0 not in game_state
        if not draw:
            if (
                3 in np.sum(game_state, axis=0)
                or 3 in np.sum(game_state, axis=1)
                or np.trace(game_state) == 3
                or np.trace(np.fliplr(game_state)) == 3
            ):
                print(
                    "[{}] Player {} won!".format(
                        str(self.jid), self._find_player_by_type(+1)["jid"]
                    )
                )
                return True
            if (
                -3 in np.sum(game_state, axis=0)
                or -3 in np.sum(game_state, axis=1)
                or np.trace(game_state) == -3
                or np.trace(np.fliplr(game_state)) == -3
            ):
                print(
                    "[{}] Player {} won!".format(
                        str(self.jid), self._find_player_by_type(-1)["jid"]
                    )
                )
                return True
            return False
        else:
            print("[{}] The game ended in a draw!".format(str(self.jid)))
            return True

    def _is_action_valid(self, content: list) -> bool:
        is_tuple = isinstance(content, list)
        size_is_valid = len(content) == 2
        value_is_valid = self.world_model["game_state"][content[0]][content[1]] == 0
        return is_tuple and size_is_valid and value_is_valid

    def _find_player_by_type(self, type_: int) -> Union[Dict[str, Any], None]:
        for player in self.world_model["players"]:
            if player["type"] == type_:
                return player


class GamePlayer(Player):
    def decide_action(self) -> None:
        state = self.world_model["state"]
        possible_values = []

        for i in range(len(state)):
            for j in range(len(state[i])):
                if state[i][j] == 0:
                    possible_values.append([i, j])

        self.action = random.choice(possible_values)
        print(self.action)


async def main():
    server = GameServer(
        "exec_0@localhost",
        "caio123",
        2,
        {},
        {"type": None, "state": np.zeros((3, 3)).tolist()},
    )
    await server.start()

    player_1 = GamePlayer(
        "exec_1@localhost", "caio123", "exec_0@localhost", {"type": 1}
    )
    await player_1.start()

    player_2 = GamePlayer(
        "exec_2@localhost", "caio123", "exec_0@localhost", {"type": -1}
    )
    await player_2.start()


if __name__ == "__main__":
    spade.run(main())
