"""
Cards.

CARD_DATA schema — every key optional except type/cost/target:

    type        Attack | Skill | Power | Curse | Status | Quest
    cost        int; negative means unplayable
    target      Self | AnyEnemy | AllEnemies | RandomEnemy | Hand | None
    damage      int, dealt to each resolved target
    hits        int, default 1
    block       int, gained by the player
    status      {name: amount} applied to each resolved target
    self_status {name: amount} applied to the player
    draw        int
    keywords    tuple of printed keywords (Exhaust, Ethereal, Retain, ...)
    upgrade     dict of overrides applied when card.upgraded
    custom      name into CUSTOM_EFFECTS; takes over resolution entirely

A custom effect signature:
    fn(state, card, target, rng, _depth=0) -> GameState
"""

from .events import Event
from .engine import register, CARD_EMIT          # noqa: F401  (for card listeners)


CARD_DATA = {
    "Strike": {
        "type": "Attack",
        "cost": 1,
        "target": "AnyEnemy",
        "damage": 6,
        "upgrade": {"damage": 9},
    },
    "Defend": {
        "type": "Skill",
        "cost": 1,
        "target": "Self",
        "block": 5,
        "upgrade": {"block": 8},
    },
    "Bash": {
        "type": "Attack",
        "cost": 2,
        "target": "AnyEnemy",
        "damage": 8,
        "status": {"Vulnerable": 2},
        "upgrade": {"damage": 10, "status": {"Vulnerable": 3}},
    },
    "Ascenders_Bane": {
        "type": "Curse",
        "cost": -1,
        "target": "None",
        "keywords": ("Unplayable", "Ethereal"),
    },
}


CUSTOM_EFFECTS = {}


# Pending choices

CHOICE_RESOLVERS = {}


def resolve_pending_choice(state, option, rng):
    """Called by apply_action when the agent answers a pending choice."""
    from dataclasses import replace
    pc = state.pending_choice
    resolver = CHOICE_RESOLVERS[pc.kind]
    state = resolver(state, option, rng)
    return replace(state, pending_choice=None)