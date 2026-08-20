"""
Core engine: dispatch, choke points, turn loop.

Everything here is mutually recursive through the event system, so it lives
in one module. Content modules (card_data, power_data, relic_data, enemy_data)
import THIS file and call register() at import time. This file imports none
of them, which is what keeps the dependency graph acyclic.
"""

from dataclasses import replace
from enum import Flag, auto

from .gamestate import GameState
from .card import Card
from .events import Event
from . import constants as const
from . import helpers as h


# Value props

class Prop(Flag):
    NONE = 0
    UNBLOCKABLE = auto()   # ignores block
    UNPOWERED = auto()     # ignores Strength/Vulnerable/Weak etc.


# Listener tables

RELIC_EMIT = {}
POWER_EMIT = {}
CARD_EMIT = {}

RELIC_QUERY_ADD = {}
RELIC_QUERY_OVER = {}
POWER_QUERY_ADD = {}
POWER_QUERY_OVER = {}
CARD_QUERY_ADD = {}
CARD_QUERY_OVER = {}


def register(table, name, event, handler):
    inner = table.setdefault(event, {})
    if name in inner:
        raise ValueError(f"{name} already registered under {event}")
    inner[name] = handler


# Dispatch

def emit(event, state, **kwargs) -> GameState:
    """Announce that something happened. Listeners return a new state."""
    relic_table = RELIC_EMIT.get(event, {})
    power_table = POWER_EMIT.get(event, {})
    card_table = CARD_EMIT.get(event, {})
    if not relic_table and not power_table and not card_table:
        return state

    for i, relic in enumerate(state.relics):
        handler = relic_table.get(relic.name)
        if handler:
            state = handler(state, relic=relic, relic_ind=i, **kwargs)
    for i, power in enumerate(state.player_powers):
        handler = power_table.get(power[0])
        if handler:
            state = handler(state, power_pair=power, power_ind=i, **kwargs)
    for i, card in enumerate(state.hand):
        handler = card_table.get(card.name)
        if handler:
            state = handler(state, card=card, card_ind=i, **kwargs)
    return state


def emit_enemy(event, state, enemy_ind, **kwargs) -> GameState:
    """Announce something on an enemy's side. Only that enemy's powers listen."""
    power_table = POWER_EMIT.get(event, {})
    if not power_table:
        return state
    enemy = state.enemies[enemy_ind]
    if enemy is None:
        return state
    for i, power in enumerate(enemy.powers):
        handler = power_table.get(power[0])
        if handler:
            state = handler(state, power_pair=power, power_ind=i,
                            enemy_ind=enemy_ind, **kwargs)
    return state


def emit_broadcast(event, state, **kwargs) -> GameState:
    """
    Announce something every creature can react to. The player's relics,
    powers and hand hear it first, then each living enemy's own powers.
    """
    state = emit(event, state, **kwargs)
    for i in range(const.MAX_ENEMIES):
        if is_alive(state, i):
            state = emit_enemy(event, state, i, **kwargs)
    return state


def _walk(relic_table, power_table, card_table, state, value,
          powers, player_side, **kwargs):
    """
    One pass over one creature's powers (plus the player's relics and hand,
    when the creature in question is the player).
    """
    if player_side:
        for i, relic in enumerate(state.relics):
            handler = relic_table.get(relic.name)
            if handler:
                value = handler(state, value, relic=relic, relic_ind=i, **kwargs)
    for i, power in enumerate(powers):
        handler = power_table.get(power[0])
        if handler:
            value = handler(state, value, power_pair=power, power_ind=i, **kwargs)
    if player_side:
        for i, card in enumerate(state.hand):
            handler = card_table.get(card.name)
            if handler:
                value = handler(state, value, card=card, card_ind=i, **kwargs)
    return value


def query(event, state, value, powers=None, player_side=True, **kwargs):
    """
    Ask a question. Listeners transform `value` and must not touch state.

    `powers` is whose power bag to consult; defaults to the player's.
    Additive listeners resolve first, then overrides.
    """
    if powers is None:
        powers = state.player_powers

    value = _walk(RELIC_QUERY_ADD.get(event, {}),
                  POWER_QUERY_ADD.get(event, {}),
                  CARD_QUERY_ADD.get(event, {}),
                  state, value, powers, player_side, **kwargs)
    value = _walk(RELIC_QUERY_OVER.get(event, {}),
                  POWER_QUERY_OVER.get(event, {}),
                  CARD_QUERY_OVER.get(event, {}),
                  state, value, powers, player_side, **kwargs)
    return value


# Creature access
#   target is None  -> the player
#   target is int   -> that enemy slot

def get_hp(state, target):
    return state.player_hp if target is None else state.enemies[target].hp


def get_block(state, target):
    return state.player_block if target is None else state.enemies[target].block


def get_powers(state, target):
    return state.player_powers if target is None else state.enemies[target].powers


def is_alive(state, target) -> bool:
    if target is None:
        return state.player_hp > 0
    e = state.enemies[target]
    return e is not None and e.hp > 0


def _set_creature(state, target, hp=None, block=None, powers=None) -> GameState:
    """Write hp/block/powers to whichever creature `target` names."""
    if target is None:
        fields = {}
        if hp is not None:
            fields["player_hp"] = hp
        if block is not None:
            fields["player_block"] = block
        if powers is not None:
            fields["player_powers"] = powers
        return replace(state, **fields)

    enemy = state.enemies[target]
    fields = {}
    if hp is not None:
        fields["hp"] = hp
    if block is not None:
        fields["block"] = block
    if powers is not None:
        fields["powers"] = powers
    new_enemy = replace(enemy, **fields)
    return replace(state, enemies=h.replace_at(state.enemies, target, new_enemy))


# Choke point: block

def gain_block(state, amount, target=None, source=None,
               props=Prop.NONE) -> GameState:
    if not is_alive(state, target):
        return state

    if Prop.UNPOWERED not in props:
        amount = query(Event.GET_BLOCK, state, amount,
                       powers=get_powers(state, target),
                       player_side=(target is None),
                       source=source, target=target)
    amount = int(max(0, amount))
    if amount == 0:
        return state

    state = _set_creature(state, target, block=get_block(state, target) + amount)
    state = emit(Event.ON_BLOCK_GAINED, state, amount=amount,
                 source=source, target=target)
    return state


# Choke point: damage

def calculate_damage(state, base, attacker, target, source=None,
                     props=Prop.NONE) -> int:
    """
    Power scaling (Strength, Vulnerable, Weak) is skipped for unpowered
    damage. Damage *reduction* on the target's side always applies, so a
    Poison tick is still capped by a reduce-to-1 effect.
    """
    value = float(base)

    if Prop.UNPOWERED not in props:
        value = query(Event.GET_DAMAGE_GIVEN, state, value,
                      powers=get_powers(state, attacker),
                      player_side=(attacker is None),
                      source=source, attacker=attacker, target=target)
        value = query(Event.GET_DAMAGE_RECEIVED, state, value,
                      powers=get_powers(state, target),
                      player_side=(target is None),
                      source=source, attacker=attacker, target=target)

    value = int(max(0, value))          # floor once, after all scaling

    value = query(Event.GET_DAMAGE_FINAL, state, value,
                  powers=get_powers(state, target),
                  player_side=(target is None),
                  source=source, attacker=attacker, target=target, props=props)
    return int(max(0, value))


def apply_damage(state, target, amount, attacker=None, source=None,
                 props=Prop.NONE, precomputed=False) -> GameState:
    """
    Deal `amount` damage to `target`.

    precomputed=True skips the power pipeline — used when a caller already
    ran calculate_damage (e.g. a multi-hit attack computing once).
    """
    if not is_alive(state, target):
        return state

    dmg = amount if precomputed else calculate_damage(
        state, amount, attacker, target, source, props)
    if dmg <= 0:
        return state

    block = get_block(state, target)
    if Prop.UNBLOCKABLE in props:
        absorbed = 0
    else:
        absorbed = min(block, dmg)
    hp_loss = dmg - absorbed

    if hp_loss > 0:
        hp_loss = int(max(0, query(Event.GET_HP_LOSS, state, hp_loss,
                                   powers=get_powers(state, target),
                                   player_side=(target is None),
                                   source=source, attacker=attacker,
                                   target=target, props=props)))

    state = _set_creature(state, target,
                          hp=get_hp(state, target) - hp_loss,
                          block=block - absorbed)

    state = emit(Event.ON_DAMAGE_TAKEN, state, amount=dmg, hp_loss=hp_loss,
                 attacker=attacker, target=target, source=source)
    if hp_loss > 0:
        state = emit(Event.ON_HP_LOST, state, amount=hp_loss,
                     attacker=attacker, target=target, source=source)
    if get_hp(state, target) <= 0:
        state = emit_broadcast(Event.ON_KILL, state, attacker=attacker,
                               target=target, source=source)
    return state


def lose_hp(state, target, amount, source=None) -> GameState:
    """Direct HP loss: ignores block and all scaling."""
    return apply_damage(state, target, amount, source=source,
                        props=Prop.UNBLOCKABLE | Prop.UNPOWERED)


# Choke point: powers

def apply_status(state, target, name, amount, applier=None, source=None) -> GameState:
    if not is_alive(state, target) or amount == 0:
        return state

    amount = query(Event.GET_STATUS_GIVEN, state, amount,
                   powers=get_powers(state, applier),
                   player_side=(applier is None),
                   status=name, target=target, source=source)
    amount = query(Event.GET_STATUS_RECEIVED, state, amount,
                   powers=get_powers(state, target),
                   player_side=(target is None),
                   status=name, applier=applier, source=source)
    amount = int(amount)
    if amount == 0:
        return state

    powers = get_powers(state, target)

    # Non-stacking powers (typically from Power cards) are on/off for the
    # whole combat; a second application is a no-op rather than an increase.
    from .power_data import POWER_DATA
    stack = POWER_DATA.get(name, {}).get("stack", "intensity")
    if stack == "none":
        if h.get_pair(powers, name) != 0:
            return state
        new_powers = h.set_power(powers, name, 1)
    else:
        new_powers = h.add_power(powers, name, amount)

    state = _set_creature(state, target, powers=new_powers)
    state = emit(Event.ON_POWER_APPLIED, state, status=name, amount=amount,
                 target=target, applier=applier, source=source)
    return state


# Piles

def shuffle_discard_into_draw(state, rng) -> GameState:
    cards = list(state.draw) + list(state.discard)
    rng.shuffle(cards)
    return replace(state, draw=tuple(cards), discard=())


def draw_cards(state, n, rng) -> GameState:
    for _ in range(n):
        if len(state.hand) >= const.HAND_SIZE:
            break
        if not state.draw:
            if not state.discard:
                break
            state = shuffle_discard_into_draw(state, rng)
        card = state.draw[0]
        state = replace(state,
                        draw=h.remove_at(state.draw, 0),
                        hand=h.add_to(state.hand, card))
        state = emit(Event.ON_DRAW, state, card=card)
    return state


def discard_hand(state) -> GameState:
    kept, moved = [], []
    for card in state.hand:
        if has_keyword(state, card, "Retain"):
            kept.append(card)
        else:
            moved.append(card)
    state = replace(state, hand=tuple(kept),
                    discard=state.discard + tuple(moved))
    for card in moved:
        state = emit(Event.ON_DISCARD, state, card=card)
    return state


def exhaust_card(state, card_ind) -> GameState:
    card = state.hand[card_ind]
    state = replace(state,
                    hand=h.remove_at(state.hand, card_ind),
                    exhaust=h.add_to(state.exhaust, card))
    state = bump_turn_counter(state, "Cards_Exhausted", 1)
    return emit(Event.ON_EXHAUST, state, card=card)


# Card data access

def card_prop(card, key, default=None):
    """Read a property off CARD_DATA, honouring the card's upgrade overrides."""
    from .card_data import CARD_DATA
    entry = CARD_DATA[card.name]
    if card.upgraded and key in entry.get("upgrade", {}):
        return entry["upgrade"][key]
    return entry.get(key, default)


def has_keyword(state, card, keyword) -> bool:
    """Printed keyword, or granted on this instance, or granted by an active effect."""
    if keyword in card_prop(card, "keywords", ()):
        return True
    if keyword in card.keywords:
        return True
    return bool(query(Event.GET_KEYWORD, state, False, card=card, keyword=keyword))


def get_card_cost(state, card) -> int:
    base = card_prop(card, "cost", 0)
    if base < 0:
        return base                                    # unplayable sentinel
    cost = base + h.get_pair(card.counters, "cost_mod")
    cost = query(Event.GET_CARD_COST, state, cost, card=card)
    return int(max(0, cost))


def can_play(state, card) -> bool:
    if card_prop(card, "cost", 0) < 0:
        return False
    if has_keyword(state, card, "Unplayable"):
        return False
    if get_card_cost(state, card) > state.energy:
        return False
    return bool(query(Event.GET_CAN_PLAY, state, True, card=card))


# Turn counters

def bump_turn_counter(state, key, delta=1) -> GameState:
    return replace(state,
                   turn_counters=h.add_counter(state.turn_counters, key, delta))


# Playing cards

_MAX_PLAY_DEPTH = 50


def play_card(state, card_ind, target, rng, pay_cost=True, _depth=0) -> GameState:
    if _depth > _MAX_PLAY_DEPTH:
        raise RecursionError("card play recursion limit hit")

    card = state.hand[card_ind]
    # max(0, ...) so the -1 unplayable sentinel can never refund energy when
    # a card is force-played.
    cost = max(0, get_card_cost(state, card)) if pay_cost else 0

    state = replace(state, hand=h.remove_at(state.hand, card_ind))
    if pay_cost:
        state = replace(state, energy=state.energy - cost)

    state = resolve_card(state, card, target, rng, _depth=_depth)

    ctype = card_prop(card, "type", "Skill")
    state = bump_turn_counter(state, "Cards_Played", 1)
    state = bump_turn_counter(state, f"{ctype}s_Played", 1)

    if has_keyword(state, card, "Exhaust"):
        state = replace(state, exhaust=h.add_to(state.exhaust, card))
        state = emit(Event.ON_EXHAUST, state, card=card)
        state = bump_turn_counter(state, "Cards_Exhausted", 1)
    else:
        state = replace(state, discard=h.add_to(state.discard, card))

    state = emit(Event.ON_CARD_PLAYED, state, card=card, target=target)
    return state


def resolve_card(state, card, target, rng, _depth=0) -> GameState:
    """Generic executor. Cards with a `custom` entry take over entirely."""
    custom = card_prop(card, "custom")
    if custom:
        from .card_data import CUSTOM_EFFECTS
        return CUSTOM_EFFECTS[custom](state, card, target, rng, _depth=_depth)

    targets = _resolve_targets(state, card, target, rng)

    damage = card_prop(card, "damage")
    if damage is not None:
        hits = card_prop(card, "hits", 1)
        for _ in range(hits):
            for t in targets:
                state = apply_damage(state, t, damage, attacker=None, source=card)

    block = card_prop(card, "block")
    if block is not None:
        state = gain_block(state, block, source=card)

    status = card_prop(card, "status")
    if status:
        for sname, samount in status.items():
            for t in targets:
                state = apply_status(state, t, sname, samount, source=card)

    self_status = card_prop(card, "self_status")
    if self_status:
        for sname, samount in self_status.items():
            state = apply_status(state, None, sname, samount, source=card)

    draw = card_prop(card, "draw")
    if draw:
        state = draw_cards(state, draw, rng)

    return state


def _resolve_targets(state, card, target, rng):
    kind = card_prop(card, "target", "Self")
    if kind == "AnyEnemy":
        return [target] if target is not None else []
    if kind == "AllEnemies":
        return list(h.find_enemy_inds(state.enemies))
    if kind == "RandomEnemy":
        living = h.find_enemy_inds(state.enemies)
        return [rng.choice(living)] if living else []
    return []          # Self / None


# Power decay

def _decay(powers) -> tuple:
    """
    Apply between-turn behaviour to one creature's power bag.

        permanent   - never ticks, and cannot be removed by any means
        conserved   - never ticks, but can be removed by effects
        decremented - loses one stack as the turn passes
        removed     - loses all stacks with no effect as the turn passes
    """
    from .power_data import POWER_DATA
    out = []
    for name, amount in powers:
        rule = POWER_DATA.get(name, {}).get("decay", "permanent")
        if rule == "removed":
            continue
        if rule == "decremented":
            amount -= 1 if amount > 0 else -1
        if amount != 0:
            out.append((name, amount))
    return tuple(out)


# Turn loop

def start_of_turn(state, rng) -> GameState:
    state = replace(state, turn_counters=())

    keep = query(Event.GET_TURN_START_BLOCK, state, 0)
    state = replace(state, player_block=int(max(0, keep)))

    energy = query(Event.GET_TURN_START_ENERGY, state, state.max_energy)
    state = replace(state, energy=int(energy))

    draw = query(Event.GET_TURN_START_DRAW, state, const.CARDS_PER_TURN)
    state = draw_cards(state, int(max(0, draw)), rng)

    state = emit(Event.ON_TURN_START, state)
    return state


def end_of_turn(state) -> GameState:
    state = emit(Event.ON_TURN_END, state)

    # Ethereal cards exhaust rather than discard. Walk backwards so indices
    # stay valid as cards are removed.
    for i in range(len(state.hand) - 1, -1, -1):
        if has_keyword(state, state.hand[i], "Ethereal"):
            state = exhaust_card(state, i)

    state = discard_hand(state)
    state = replace(state, player_powers=_decay(state.player_powers))
    return state


def enemy_turn(state, rng) -> GameState:
    from .enemy_data import take_enemy_turn
    for i in range(const.MAX_ENEMIES):
        if not is_alive(state, i):
            continue
        state = _set_creature(state, i, block=0)
        state = take_enemy_turn(state, i, rng)
        if state.player_hp <= 0:
            return state
    return state


def decay_enemy_powers(state, enemy_ind) -> GameState:
    enemy = state.enemies[enemy_ind]
    if enemy is None:
        return state
    return _set_creature(state, enemy_ind, powers=_decay(enemy.powers))


# Win / loss

def combat_over(state) -> bool:
    return state.player_hp <= 0 or not h.find_enemy_inds(state.enemies)


def player_won(state) -> bool:
    return state.player_hp > 0 and not h.find_enemy_inds(state.enemies)