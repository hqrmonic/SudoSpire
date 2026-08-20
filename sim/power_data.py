"""
Powers.

POWER_DATA declares two independent axes. Listeners declare behaviour.

stack — how repeated applications combine:
    intensity  effect scales with the number of stacks   (Strength, Vulnerable*)
    duration   lasts as many turns as it has stacks      (Vulnerable, Weak, Frail)
    none       on/off for the whole combat; reapplying does nothing

decay — what happens as the owner's turn passes:
    permanent    never ticks, and cannot be removed by any means
    conserved    never ticks, but can be removed by effects
    decremented  loses one stack
    removed      loses all stacks with no effect

* Vulnerable is duration-stacked: the multiplier is fixed, the stack count is
  how many turns it lasts.
"""

from dataclasses import replace

from . import helpers as h
from .events import Event
from .engine import (register, POWER_QUERY_ADD, POWER_QUERY_OVER, POWER_EMIT,
                     apply_status, is_alive)


POWER_DATA = {
    "Strength":   {"stack": "intensity", "decay": "permanent"},
    "Dexterity":  {"stack": "intensity", "decay": "permanent"},
    "Vulnerable": {"stack": "duration",  "decay": "decremented"},
    "Weak":       {"stack": "duration",  "decay": "decremented"},
    "Frail":      {"stack": "duration",  "decay": "decremented"},

    # Player debuff from Shrinker Beetle. Only bites while a Shrinker Beetle
    # is still alive, so it is left in the bag and the listener checks.
    "Shrink":     {"stack": "none",      "decay": "conserved"},

    # Corpse Slug passive. The amount is the Strength gained per corpse.
    "Ravenous":   {"stack": "intensity", "decay": "conserved"},

    # Skips the owner's next turn, then clears.
    "Stunned":    {"stack": "none",      "decay": "removed"},
}


# Strength — attacker side, additive, once per hit

def strength(state, value, power_pair=None, **kwargs):
    return value + power_pair[1]


register(POWER_QUERY_ADD, "Strength", Event.GET_DAMAGE_GIVEN, strength)


# Dexterity — additive block

def dexterity(state, value, power_pair=None, **kwargs):
    return value + power_pair[1]


register(POWER_QUERY_ADD, "Dexterity", Event.GET_BLOCK, dexterity)


# Vulnerable — target side, x1.5 damage received

def vulnerable(state, value, **kwargs):
    return value * 1.5


register(POWER_QUERY_OVER, "Vulnerable", Event.GET_DAMAGE_RECEIVED, vulnerable)


# Weak — attacker side, x0.75 damage dealt

def weak(state, value, **kwargs):
    return value * 0.75


register(POWER_QUERY_OVER, "Weak", Event.GET_DAMAGE_GIVEN, weak)


# Frail — x0.75 block gained

def frail(state, value, **kwargs):
    return value * 0.75


register(POWER_QUERY_OVER, "Frail", Event.GET_BLOCK, frail)


# Shrink — while a Shrinker Beetle lives, the player deals 30% less damage

def shrink(state, value, **kwargs):
    for i, enemy in enumerate(state.enemies):
        if enemy is not None and enemy.hp > 0 and enemy.name == "Shrinker_Beetle":
            return value * 0.7
    return value


register(POWER_QUERY_OVER, "Shrink", Event.GET_DAMAGE_GIVEN, shrink)


# Ravenous — when another enemy dies, this one is stunned and eats the corpse

def ravenous(state, power_pair=None, enemy_ind=None, target=None, **kwargs):
    if target == enemy_ind:
        return state                       # it was this creature that died
    if target is None:
        return state                       # the player died, not a corpse
    amount = power_pair[1]
    state = apply_status(state, enemy_ind, "Stunned", 1, applier=enemy_ind)
    state = apply_status(state, enemy_ind, "Strength", amount, applier=enemy_ind)
    return state


register(POWER_EMIT, "Ravenous", Event.ON_KILL, ravenous)