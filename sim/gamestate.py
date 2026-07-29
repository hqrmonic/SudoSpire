from dataclasses import dataclass
from .card import Card
from .relics import Relic
from .potions import Potion
from .enemies import Enemy

@dataclass(frozen=True)
class PendingChoice:
    kind: str
    cards: tuple[Card, ...]

@dataclass
class GameState:
    hand: tuple[Card, ...]
    draw: tuple[Card, ...]
    discard: tuple[Card, ...]
    exhaust: tuple[Card, ...]

    player_hp: int
    player_max_hp: int
    osty_hp: int
    osty_max_hp: int
    gold: int
    player_block: int
    energy: int
    max_energy: int
    stars: int

    player_powers: tuple[tuple[str, int], ...]
    relics:tuple[Relic, ...]
    potions: tuple[Potion | None, ...]
    enemies: tuple[Enemy | None, ...]
    #Enemy class contains enemy health, intent, and powers
    turn_number: int
    turn_counters: tuple[tuple[str, int], ...]
    #Turn counters tracks how many attacks, skills, powers, exhausting cards played this turn, and number of cards discarded.

    pending_choice: PendingChoice | None = None