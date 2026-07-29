from .gamestate import GameState
from .card import Card
from .relics import Relic
from .potions import Potion
from .enemies import Enemy
from . import constants as const

def from_string(s: str) -> GameState:
    sections = s.split("/")
    if(len(sections) != 16): raise ValueError("too many args in gamestate string")
    hand = parse_cards(sections[0])
    draw = parse_cards(sections[1])
    discard = parse_cards(sections[2])
    exhaust = parse_cards(sections[3])
    player_hp = int(sections[4])
    player_max_hp = int(sections[5])
    gold = int(sections[6])
    player_block = int(sections[7])
    energy = int(sections[8])
    max_energy = int(sections[9])
    player_powers = parse_powers(sections[10])
    relics = parse_relics(sections[11])
    potions = parse_potions(sections[12])
    enemies = parse_enemies(sections[13])
    turn_number = int(sections[14])
    turn_counters = parse_turn_counters(sections[15])
    return GameState(
        hand=hand,
        draw=draw,
        discard=discard,
        exhaust=exhaust,
        player_hp=player_hp,
        player_max_hp=player_max_hp,
        gold=gold,
        player_block=player_block,
        energy=energy,
        max_energy=max_energy,
        player_powers=player_powers,
        relics=relics,
        potions=potions,
        enemies=enemies,
        turn_number=turn_number,
        turn_counters=turn_counters,
    )

def to_string(state: GameState) -> str:
    sections = [
        serialize_cards(state.hand),
        serialize_cards(state.draw),
        serialize_cards(state.discard),
        serialize_cards(state.exhaust),
        str(state.player_hp),
        str(state.player_max_hp),
        str(state.gold),
        str(state.player_block),
        str(state.energy),
        str(state.max_energy),
        serialize_powers(state.player_powers),
        serialize_relics(state.relics),
        serialize_potions(state.potions),
        serialize_enemies(state.enemies),
        str(state.turn_number),
        serialize_turn_counters(state.turn_counters)
    ]
    return "/".join(sections)


def parse_cards(section: str) -> tuple[Card, ...]:
    section = section.replace(" ", "")
    if section == "": return ()
    names = section.split(";")
    card_list = []
    for string in names:
        tokens = string.split(",")
        upgraded = tokens[0].endswith("+")
        name = tokens[0].removesuffix("+")
        keywords = []
        counters = []
        enchantment = None
        for modifier in tokens[1:]:
            parts = modifier.split(":")
            if(parts[0] == "key"):
                keywords.append(parts[1])
            elif(parts[0] == "count"):
                counters.append((parts[1], int(parts[2])))
            elif(parts[0] == "ench"):
                enchantment = (parts[1], int(parts[2]))
            else: raise ValueError(parts[0] + " modifier written bad")
        card_list.append(Card(name=name, upgraded=upgraded, keywords=tuple(sorted(keywords)), counters=tuple(sorted(counters)), enchantment=enchantment))

    return tuple(card_list)

def serialize_cards(cards: tuple[Card, ...]) -> str:
    card_list = []
    for card in cards:
        string = ""
        string += card.name
        if card.upgraded: string += "+"
        for keyword in card.keywords:
            string += ",key:" + keyword
        for counter in card.counters:
            string += ",count:" + counter[0] + ":" + str(counter[1])
        if(card.enchantment is not None): 
            string += ",ench:" + card.enchantment[0] + ":" + str(card.enchantment[1])

        card_list.append(string)
    return ";".join(card_list)


def parse_powers(section: str) -> tuple[tuple[str, int], ...]:
    section = section.replace(" ", "")
    if section == "": return ()
    power_list = []
    powers = section.split(",")
    for power in powers:
        name, count = power.split(":")
        power_list.append((name, int(count)))
    return tuple(power_list)

def serialize_powers(powers: tuple[tuple[str, int], ...]) -> str:
    power_list = []
    for power in powers:
        power_list.append(power[0] + ":" + str(power[1]))
    return ",".join(power_list)


def parse_relics(section: str) -> tuple[Relic, ...]:
    section = section.replace(" ", "")
    if section == "": return ()
    relics = section.split(",")
    relic_list = []
    for relic in relics:
        name, count = relic.split(":")
        relic_list.append(Relic(name=name, counter=int(count)))

    return tuple(relic_list)

def serialize_relics(relics: tuple[Relic, ...]) -> str:
    relic_list = []
    for relic in relics:
        relic_list.append(relic.name + ":" + str(relic.counter))

    return ",".join(relic_list)


def parse_potions(section: str) -> tuple[Potion | None, ...]:
    section = section.replace(" ", "")
    if section == "": return ()
    potions = []
    potion_list = section.split(",")
    for part in potion_list:
        if part == "Empty": potions.append(None)
        else: potions.append(Potion(name=part))
    return tuple(potions)

def serialize_potions(potions: tuple[Potion | None, ...]) -> str:
    potion_list = []
    for part in potions:
        if part is None: potion_list.append("Empty")
        else: potion_list.append(part.name)
    return ",".join(potion_list)


def parse_enemies(section: str) -> tuple[Enemy | None, ...]:
    section = section.replace(" ", "")
    if section == "": return (None,) * const.MAX_ENEMIES
    enemy_list = []
    enemies = section.split("\\")
    if len(enemies) > const.MAX_ENEMIES: raise ValueError("too many enemies")
    for blank in range(const.MAX_ENEMIES - len(enemies)): enemy_list.append(None)
    for enemy in enemies:
        if enemy == "Empty": 
            enemy_list.append(None)
            continue
        info = enemy.split(";")
        if (len(info) != 6): raise ValueError("Bad enemy Serialization")
        name = info[0]
        hp = int(info[1])
        max_hp = int(info[2])
        block = int(info[3])
        powers = parse_powers(info[4])
        intent = info[5]
        enemy_list.append(Enemy(name=name, hp=hp, max_hp=max_hp, block=block, powers=powers, intent=intent))
    return tuple(enemy_list)

def serialize_enemies(enemies: tuple[Enemy | None, ...]) -> str:
    enemy_list = []

    start = None
    for i, enemy in enumerate(enemies):
        if enemy is not None:
            start = i
            break
    if start is None: return ""

    for i in range(start, const.MAX_ENEMIES):
        if(enemies[i] is None):
            enemy_list.append("Empty")
            continue
        enemy_info = enemies[i].name + ";" + str(enemies[i].hp) + ";" + str(enemies[i].max_hp) + ";"
        enemy_info += str(enemies[i].block) + ";" + serialize_powers(enemies[i].powers) + ";" + str(enemies[i].intent)
        enemy_list.append(enemy_info)

    return "\\".join(enemy_list)


def parse_turn_counters(section: str) -> tuple[tuple[str, int], ...]:
    section = section.replace(" ", "")
    if section == "": return ()
    turn_counters = []
    counters = section.split(",")
    for counter in counters:
        name, count = counter.split(":")
        turn_counters.append((name, int(count)))
    return tuple(sorted(turn_counters))

def serialize_turn_counters(counters: tuple[tuple[str, int], ...]) -> str:
    turn_counters = []
    for counter in counters:
        turn_counters.append(counter[0] + ":" + str(counter[1]))
    return ",".join(turn_counters)