from dataclasses import dataclass

@dataclass(frozen=True)
class Card:
    name: str
    keywords: tuple[str, ...] = ()
    counters: tuple[tuple[str, int], ...] = ()
    #for card-specific incrementals. (Rampage, gen algo, scythe, momentum, hidden gem, transfigure)
    enchantment: tuple[str, int] | None = None