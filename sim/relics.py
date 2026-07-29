from dataclasses import dataclass

@dataclass(frozen=True)
class Relic:
    name: str
    counter: int = 0