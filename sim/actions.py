"""
Action space.

Layout (all indices flat, fixed width):
    0                     .. CARD_ACTIONS-1        play a card
    CARD_ACTIONS          .. +POTION_ACTIONS-1     use a potion
    +CHOICE_ACTIONS                                answer a pending choice
    END_TURN                                       end turn

Card and potion actions encode (slot, target_slot). What target_slot *means*
depends on the card: an enemy index for AnyEnemy cards, a hand index for
hand-targeting cards, ignored for Self/AllEnemies/RandomEnemy.
"""

from . import constants as const
from . import helpers as h
from . import engine


TARGET_SLOTS = max(const.MAX_ENEMIES, const.HAND_SIZE)

CARD_ACTIONS = const.HAND_SIZE * TARGET_SLOTS
POTION_ACTIONS = const.MAX_POTIONS * TARGET_SLOTS
CHOICE_ACTIONS = const.MAX_CHOICES

CARD_BASE = 0
POTION_BASE = CARD_ACTIONS
CHOICE_BASE = POTION_BASE + POTION_ACTIONS
END_TURN = CHOICE_BASE + CHOICE_ACTIONS
ACTION_SPACE_SIZE = END_TURN + 1


# Encoding

def encode_card(card_slot, target_slot=0) -> int:
    return CARD_BASE + card_slot * TARGET_SLOTS + target_slot


def encode_potion(potion_slot, target_slot=0) -> int:
    return POTION_BASE + potion_slot * TARGET_SLOTS + target_slot


def encode_choice(option) -> int:
    return CHOICE_BASE + option


def decode_action(action):
    """-> (kind, slot, target_slot). kind in {card, potion, choice, end}."""
    if action == END_TURN:
        return ("end", None, None)
    if action >= CHOICE_BASE:
        return ("choice", action - CHOICE_BASE, None)
    if action >= POTION_BASE:
        slot, target = divmod(action - POTION_BASE, TARGET_SLOTS)
        return ("potion", slot, target)
    slot, target = divmod(action - CARD_BASE, TARGET_SLOTS)
    return ("card", slot, target)


# Legality

def legal_actions(state) -> tuple:
    mask = [False] * ACTION_SPACE_SIZE

    if engine.combat_over(state):
        return tuple(mask)

    # A pending choice locks out everything else, including ending the turn.
    if state.pending_choice is not None:
        n = _choice_option_count(state)
        if n > const.MAX_CHOICES:
            raise ValueError(f"pending choice has {n} options, MAX_CHOICES is {const.MAX_CHOICES}")
        for i in range(n):
            mask[encode_choice(i)] = True
        return tuple(mask)

    living = h.find_enemy_inds(state.enemies)

    for slot, card in enumerate(state.hand):
        if slot >= const.HAND_SIZE:
            break
        if not engine.can_play(state, card):
            continue
        kind = engine.card_prop(card, "target", "Self")
        if kind == "AnyEnemy":
            for t in living:
                mask[encode_card(slot, t)] = True
        elif kind == "Hand":
            for t in range(len(state.hand)):
                if t != slot:
                    mask[encode_card(slot, t)] = True
        else:
            mask[encode_card(slot, 0)] = True

    for slot, potion in enumerate(state.potions):
        if potion is None or slot >= const.MAX_POTIONS:
            continue
        kind = _potion_prop(potion, "target", "Self")
        if kind == "AnyEnemy":
            for t in living:
                mask[encode_potion(slot, t)] = True
        else:
            mask[encode_potion(slot, 0)] = True

    mask[END_TURN] = True
    return tuple(mask)


def _choice_option_count(state) -> int:
    pc = state.pending_choice
    if pc.kind == "hand":
        return len(state.hand)
    return len(pc.cards)


def _potion_prop(potion, key, default=None):
    from .potion_data import POTION_DATA
    return POTION_DATA.get(potion.name, {}).get(key, default)


# Application

def apply_action(state, action, rng):
    kind, slot, target = decode_action(action)

    if kind == "end":
        state = engine.end_of_turn(state)
        if engine.combat_over(state):
            return state
        state = engine.enemy_turn(state, rng)
        if engine.combat_over(state):
            return state
        from dataclasses import replace
        state = replace(state, turn_number=state.turn_number + 1)
        return engine.start_of_turn(state, rng)

    if kind == "card":
        card = state.hand[slot]
        tkind = engine.card_prop(card, "target", "Self")
        real_target = target if tkind in ("AnyEnemy", "Hand") else None
        return engine.play_card(state, slot, real_target, rng)

    if kind == "potion":
        from .potion_data import use_potion
        return use_potion(state, slot, target, rng)

    if kind == "choice":
        from .card_data import resolve_pending_choice
        return resolve_pending_choice(state, slot, rng)

    raise ValueError(f"unknown action {action}")


# Rollout driver

def run_fight(state, policy, rng, max_turns=200):
    """
    policy(state, mask) -> action index.
    Returns the final state.
    """
    state = engine.start_of_turn(state, rng)
    while not engine.combat_over(state):
        if state.turn_number > max_turns:
            break
        mask = legal_actions(state)
        if not any(mask):
            break
        state = apply_action(state, policy(state, mask), rng)
    return state