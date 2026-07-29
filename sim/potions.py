from dataclasses import dataclass

@dataclass(frozen=True)
class Potion:
    name: str