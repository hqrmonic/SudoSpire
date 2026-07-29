from dataclasses import dataclass

@dataclass(frozen=True)
class Enemy:
    name: str
    hp: int
    max_hp: int
    block: int
    intent: str
    powers: tuple[tuple[str, int], ...] = ()
