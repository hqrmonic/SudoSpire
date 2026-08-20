from enum import StrEnum, auto


class Event(StrEnum):
    """
    ON_*  -> emitted after a fact. Listener: (state, **kwargs) -> GameState
    GET_* -> queried before a fact. Listener: (state, value, **kwargs) -> value
    """

    # --- emitted ---
    ON_COMBAT_START = auto()
    ON_COMBAT_END = auto()
    ON_TURN_START = auto()
    ON_TURN_END = auto()
    ON_ENEMY_TURN_START = auto()
    ON_ENEMY_TURN_END = auto()
    ON_CARD_PLAYED = auto()
    ON_DRAW = auto()
    ON_DISCARD = auto()
    ON_EXHAUST = auto()
    ON_BLOCK_GAINED = auto()
    ON_DAMAGE_TAKEN = auto()
    ON_HP_LOST = auto()
    ON_KILL = auto()
    ON_POWER_APPLIED = auto()
    ON_ATTACK = auto()
    BEFORE_PLAYER_DEATH = auto()

    # --- queried ---
    GET_CARD_COST = auto()
    GET_CAN_PLAY = auto()
    GET_KEYWORD = auto()
    GET_BLOCK = auto()
    GET_DAMAGE_GIVEN = auto()
    GET_DAMAGE_RECEIVED = auto()
    GET_DAMAGE_FINAL = auto()
    GET_HP_LOSS = auto()
    GET_STATUS_GIVEN = auto()
    GET_STATUS_RECEIVED = auto()
    GET_TURN_START_BLOCK = auto()
    GET_TURN_START_ENERGY = auto()
    GET_TURN_START_DRAW = auto()