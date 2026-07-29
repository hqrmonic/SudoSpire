from .card import Card
from .enemies import Enemy
from . import constants as const


def get_pair(bag: tuple[tuple[str, int], ...], key: str) -> int:
    for name, val in bag:
        if name == key: return val
    return 0

def set_power(powers: tuple[tuple[str, int], ...], key: str, new_val: int) -> tuple[tuple[str, int], ...]: 
    new_bag = []
    found = False
    for name, val in powers:
        if(name == key): 
            found = True
            new_bag.append((name, new_val))
        else: new_bag.append((name, val))
    if not found: new_bag.append((key, new_val))
    return tuple(new_bag)

def set_counter(counters: tuple[tuple[str, int], ...], key: str, new_val: int) -> tuple[tuple[str, int], ...]: 
    return tuple(sorted(set_power(counters,key, new_val)))

def add_power(powers: tuple[tuple[str, int], ...], key: str, delta: int) -> tuple[tuple[str, int], ...]:
    return set_power(powers, key, get_pair(powers, key) + delta)

def add_counter(counters: tuple[tuple[str, int], ...], key: str, delta: int) -> tuple[tuple[str, int], ...]:
    return set_counter(counters, key, get_pair(counters, key) + delta)

def add_to(pile: tuple[Card, ...], card: Card) -> tuple: 
    return pile + (card,)

def remove_at(pile: tuple[Card, ...], ind: int) -> tuple: 
    return pile[:ind] + pile[ind+1:]

def replace_at(pile: tuple[Card, ...], ind: int, new_card: Card) -> tuple: 
    return pile[:ind] + (new_card,) + pile[ind+1:]

def find_enemy_inds(enemies: tuple[Enemy | None, ...]) -> tuple[int, ...]: 
    inds = []
    for i in range(const.MAX_ENEMIES):
        if enemies[i] is not None and enemies[i].hp > 0:
            inds.append(i)
    return tuple(inds)

def find_enemies(enemies: tuple[Enemy | None, ...]) -> tuple[Enemy, ...]: 
    enemy_list = []
    for i in range(const.MAX_ENEMIES):
        if enemies[i] is not None and enemies[i].hp > 0:
            enemy_list.append(enemies[i])
    return tuple(enemy_list)

def find_summon_slot(enemies: tuple[Enemy | None, ...]) -> int | None: 
    for i in reversed(range(const.MAX_ENEMIES)):
        if enemies[i] is None or enemies[i].hp <= 0:
            return i
    return None