"""
Enemies.

ENEMY_DATA[name]:
    hp       (min, max) inclusive; rolled at spawn
    powers   starting powers, as a tuple of (name, amount) pairs
    moves    {move_name: {damage, hits, block, status, self_status}}
                 status      -> applied to the player
                 self_status -> applied to this enemy
    ai       one of the three structures below

AI structures
    fixed     cycles a pattern.
                  pattern  list of move names
                  loop     index the pattern returns to at the end (default 0);
                           set to len(pattern)-1 for "then X forever"
    weighted  samples from weights, optionally never repeating.
                  weights    {move: relative weight}
                  first      optional separate weights for the opening move
                  no_repeat  exclude the move just performed
    custom    choose(state, enemy_ind, rng) -> move name

Opening move
    start(pos, count, group_roll, rng) -> move name picks the telegraphed move
    at spawn. pos is the index within that enemy's own group (0 = leftmost),
    count is how many of it there are, and group_roll is one random int shared
    by the whole group so members can be staggered against each other.
    Defaults to the first pattern entry, or a weighted sample.
"""

from dataclasses import replace

from . import helpers as h
from . import engine
from . import constants as const
from .enemies import Enemy
from .events import Event


def _weighted_choice(weights, rng):
    total = sum(weights.values())
    roll = rng.random() * total
    upto = 0.0
    for move, w in weights.items():
        upto += w
        if roll < upto:
            return move
    return next(iter(weights))


# Opening-move rules

def nibbit_start(pos, count, group_roll, rng):
    # Alone it opens with Butt. As a pair the front takes Hesitant Slice and
    # the back takes Hiss.
    if count == 1:
        return "Butt"
    return "Hesitant_Slice" if pos == 0 else "Hiss"


CORPSE_SLUG_CYCLE = ["Whip_Slap", "Glomp", "Goop"]


def corpse_slug_start(pos, count, group_roll, rng):
    # Random opener, staggered so no two slugs share a move.
    return CORPSE_SLUG_CYCLE[(group_roll + pos) % len(CORPSE_SLUG_CYCLE)]


ENEMY_DATA = {

    "Seapunk": {
        "hp": (47, 49),
        "moves": {
            "Sea_Kick":      {"damage": 13},
            "Spinning_Kick": {"damage": 2, "hits": 4},
            "Bubble_Burp":   {"block": 8, "self_status": {"Strength": 2}},
        },
        "ai": {
            "kind": "fixed",
            "pattern": ["Sea_Kick", "Spinning_Kick", "Bubble_Burp"],
            "loop": 0,
        },
    },

    "Shrinker_Beetle": {
        "hp": (40, 42),
        "moves": {
            "Shrinker": {"status": {"Shrink": 1}},
            "Chomp":    {"damage": 8},
            "Stomp":    {"damage": 14},
        },
        "ai": {
            # Opens with Shrinker, then alternates Chomp / Stomp forever.
            "kind": "fixed",
            "pattern": ["Shrinker", "Chomp", "Stomp"],
            "loop": 1,
        },
    },

    "Nibbit": {
        "hp": (44, 48),
        "moves": {
            "Butt":           {"damage": 13},
            "Hesitant_Slice": {"damage": 7, "block": 6},
            "Hiss":           {"self_status": {"Strength": 3}},
        },
        "ai": {
            "kind": "fixed",
            "pattern": ["Butt", "Hesitant_Slice", "Hiss"],
            "loop": 0,
        },
        "start": nibbit_start,
    },

    "Corpse_Slug": {
        "hp": (27, 29),
        "powers": (("Ravenous", 5),),
        "moves": {
            "Whip_Slap": {"damage": 3, "hits": 2},
            "Glomp":     {"damage": 9},
            "Goop":      {"status": {"Frail": 2}},
        },
        "ai": {
            "kind": "fixed",
            "pattern": CORPSE_SLUG_CYCLE,
            "loop": 0,
        },
        "start": corpse_slug_start,
    },

    "Flyconid": {
        "hp": (51, 53),
        "moves": {
            "Weakening_Spores": {"status": {"Vulnerable": 2}},
            "Frail_Spores":     {"damage": 9, "status": {"Frail": 2}},
            "Smash":            {"damage": 12},
        },
        "ai": {
            "kind": "weighted",
            # Turn one cannot roll Weakening Spores: 2/3 and 1/3.
            "first": {"Frail_Spores": 2, "Smash": 1},
            # Thereafter 1/2, 1/3, 1/6.
            "weights": {"Weakening_Spores": 3, "Frail_Spores": 2, "Smash": 1},
            "no_repeat": True,
        },
    },
}


ENCOUNTERS = {
    "Seapunk_Weak":          ["Seapunk"],
    "Shrinker_Beetle_Weak":  ["Shrinker_Beetle"],
    "Nibbit_Weak":           ["Nibbit"],
    "Nibbit_Normal":         ["Nibbit", "Nibbit"],
    "Corpse_Slugs_Normal":   ["Corpse_Slug", "Corpse_Slug", "Corpse_Slug"],
    "Flyconid_Normal":       ["Flyconid"],
}


# Spawning

def spawn_encounter(names, rng) -> tuple:
    """Build a right-aligned enemies tuple from a list of enemy names."""
    if len(names) > const.MAX_ENEMIES:
        raise ValueError(f"{len(names)} enemies exceeds MAX_ENEMIES")

    counts = {}
    for n in names:
        counts[n] = counts.get(n, 0) + 1
    group_rolls = {n: rng.randrange(64) for n in counts}
    seen = {n: 0 for n in counts}

    built = []
    for name in names:
        data = ENEMY_DATA[name]
        lo, hi = data["hp"]
        hp = rng.randint(lo, hi)

        pos = seen[name]
        seen[name] += 1

        starter = data.get("start")
        if starter:
            intent = starter(pos, counts[name], group_rolls[name], rng)
        else:
            ai = data["ai"]
            if ai["kind"] == "weighted":
                intent = _weighted_choice(ai.get("first", ai["weights"]), rng)
            elif ai["kind"] == "fixed":
                intent = ai["pattern"][0]
            else:
                intent = ai["choose"](None, None, rng)

        built.append(Enemy(name=name, hp=hp, max_hp=hp, block=0,
                           intent=intent, powers=data.get("powers", ())))

    pad = (None,) * (const.MAX_ENEMIES - len(built))
    return pad + tuple(built)


# Resolving one move

def perform_move(state, enemy_ind, move_name, rng):
    enemy = state.enemies[enemy_ind]
    move = ENEMY_DATA[enemy.name]["moves"][move_name]

    damage = move.get("damage")
    if damage is not None:
        for _ in range(move.get("hits", 1)):
            if state.player_hp <= 0 or not engine.is_alive(state, enemy_ind):
                break
            state = engine.apply_damage(state, None, damage,
                                        attacker=enemy_ind, source=enemy.name)

    block = move.get("block")
    if block:
        state = engine.gain_block(state, block, target=enemy_ind,
                                  source=enemy.name)

    for sname, samount in move.get("status", {}).items():
        state = engine.apply_status(state, None, sname, samount,
                                    applier=enemy_ind, source=enemy.name)

    for sname, samount in move.get("self_status", {}).items():
        state = engine.apply_status(state, enemy_ind, sname, samount,
                                    applier=enemy_ind, source=enemy.name)

    return state


# Choosing the next move

def next_intent(state, enemy_ind, rng) -> str:
    enemy = state.enemies[enemy_ind]
    ai = ENEMY_DATA[enemy.name]["ai"]
    kind = ai["kind"]

    if kind == "custom":
        return ai["choose"](state, enemy_ind, rng)

    if kind == "weighted":
        weights = dict(ai["weights"])
        if ai.get("no_repeat"):
            weights.pop(enemy.intent, None)
        return _weighted_choice(weights, rng)

    pattern = ai["pattern"]
    if enemy.intent not in pattern:
        return pattern[0]
    i = pattern.index(enemy.intent) + 1
    if i >= len(pattern):
        i = ai.get("loop", 0)
    return pattern[i]


# One enemy's turn

def take_enemy_turn(state, enemy_ind, rng):
    state = engine.emit_enemy(Event.ON_ENEMY_TURN_START, state, enemy_ind)
    if not engine.is_alive(state, enemy_ind):
        return state

    stunned = h.get_pair(state.enemies[enemy_ind].powers, "Stunned") > 0
    if stunned:
        # Skip the move and hold the telegraphed intent for next turn.
        state = engine.emit_enemy(Event.ON_ENEMY_TURN_END, state, enemy_ind)
        if not engine.is_alive(state, enemy_ind):
            return state
        return engine.decay_enemy_powers(state, enemy_ind)

    enemy = state.enemies[enemy_ind]
    state = perform_move(state, enemy_ind, enemy.intent, rng)
    if state.player_hp <= 0:
        return state

    state = engine.emit_enemy(Event.ON_ENEMY_TURN_END, state, enemy_ind)
    if not engine.is_alive(state, enemy_ind):
        return state

    state = engine.decay_enemy_powers(state, enemy_ind)

    upcoming = next_intent(state, enemy_ind, rng)
    new_enemy = replace(state.enemies[enemy_ind], intent=upcoming)
    return replace(state,
                   enemies=h.replace_at(state.enemies, enemy_ind, new_enemy))