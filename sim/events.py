from enum import StrEnum, auto

class Event(StrEnum): 
    #emit events
    ON_CARD_PLAYED = "on_card_played"
    ON_EXHAUST = auto()
    ON_DISCARD = auto()
    ON_ATTACK = auto()
    ON_SKILL = auto()
    ON_POWER = auto()
    ON_CARD_GEN = auto()
    ON_HP_LOST = auto()
    ON_SELF_DAMAGE = auto()
    ON_ENEMY_DAMAGE = auto()
    ON_TURN_START = auto()
    ON_TURN_END = auto()


    ### unsure if combat start should be a state yet. Could be used in the future but any position implemented hypothetically already has started combat?
    ON_COMBAT_START = auto()

    BEFORE_PLAYER_DEATH = auto()
    ON_KILL = auto()
    ON_DEBUFF_APPLIED = auto()

    #query states
    GET_CARD_COST = auto()
    CAN_PLAY = auto()
    CALCULATE_DAMAGE = auto()
    GAIN_BLOCK = auto()
    APPLY_DEBUFF_GIVEN = auto()
    APPLY_DEBUFF_RECIEVED = auto()
    TURN_START_BLOCKK = auto()
    TURN_START_ENERGY = auto()


