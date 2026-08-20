###Used AI to create tests after creating a few myself to check:


"""
Tests for SudoSpire.

Run from the project root:
    pytest tests/ -v

Place this file at:
    SudoSpire/tests/test_engine.py

Requires an (empty) SudoSpire/tests/__init__.py, or pytest's rootdir
conftest discovery, so that `sim` resolves as a top-level package.
"""

import pytest

from sim.serialize import from_string, to_string
from sim.engine import gain_block
from sim.card import Card
from sim.relics import Relic
from sim.enemies import Enemy
from sim import helpers
from sim import constants as const

import sim.relic_data  # noqa: F401  -- side effect: populates listener tables


# ---------------------------------------------------------------------------
# Fixtures / state builders
# ---------------------------------------------------------------------------

# 19 sections:
#  0 hand | 1 draw | 2 discard | 3 exhaust | 4 hp | 5 max_hp | 6 osty_hp
#  7 osty_max_hp | 8 gold | 9 block | 10 energy | 11 max_energy | 12 stars
#  13 powers | 14 relics | 15 potions | 16 enemies | 17 turn | 18 turn_counters
BASE = (
    "Defend;Strike;Ascenders_Bane;Defend;Strike"
    "/Bash;Defend;Defend;Strike;Strike;Strike"
    "//"
    "/64/80/0/0/249/0/3/3/0"
    "/"
    "/Burning_Blood:1,Golden_Pearl:1,Vambrace:1"
    "/"
    "/Seapunk;49;49;0;;Sea_Kick"
    "/1/"
)

VAMBRACE_SPENT = BASE.replace("Vambrace:1", "Vambrace:0")
NO_VAMBRACE = BASE.replace(",Vambrace:1", "")

A_CARD = Card(name="Defend")


@pytest.fixture
def state():
    return from_string(BASE)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def test_section_count_guard():
    with pytest.raises(ValueError):
        from_string("a/b/c")


def test_scalars_land_in_the_right_fields(state):
    assert state.player_hp == 64
    assert state.player_max_hp == 80
    assert state.osty_hp == 0
    assert state.osty_max_hp == 0
    assert state.gold == 249
    assert state.player_block == 0
    assert state.energy == 3
    assert state.max_energy == 3
    assert state.stars == 0
    assert state.turn_number == 1


def test_piles_parse(state):
    assert len(state.hand) == 5
    assert len(state.draw) == 6
    assert state.discard == ()
    assert state.exhaust == ()
    assert state.hand[0].name == "Defend"
    assert state.hand[2].name == "Ascenders_Bane"
    assert state.draw[0].name == "Bash"


def test_empty_bags_parse_empty(state):
    assert state.player_powers == ()
    assert state.potions == ()
    assert state.turn_counters == ()
    assert state.pending_choice is None


def test_relics_parse_with_counters(state):
    assert [r.name for r in state.relics] == [
        "Burning_Blood", "Golden_Pearl", "Vambrace"
    ]
    assert all(r.counter == 1 for r in state.relics)


def test_enemies_are_right_aligned(state):
    assert len(state.enemies) == const.MAX_ENEMIES
    assert state.enemies[:const.MAX_ENEMIES - 1] == (None,) * (const.MAX_ENEMIES - 1)
    last = state.enemies[-1]
    assert last.name == "Seapunk"
    assert last.hp == 49
    assert last.max_hp == 49
    assert last.block == 0
    assert last.intent == "Sea_Kick"
    assert last.powers == ()


def test_card_modifiers_parse():
    s = BASE.replace("Defend;Strike;Ascenders_Bane", "Defend+,key:Retain;Strike,count:bonus:4;Bash,ench:Sharp:3", 1)
    st = from_string(s)
    upgraded, counted, enchanted = st.hand[0], st.hand[1], st.hand[2]
    assert upgraded.name == "Defend" and upgraded.upgraded is True
    assert upgraded.keywords == ("Retain",)
    assert counted.counters == (("bonus", 4),)
    assert enchanted.enchantment == ("Sharp", 3)


def test_roundtrip_is_stable(state):
    """to_string -> from_string reproduces an equal state."""
    assert from_string(to_string(state)) == state


def test_roundtrip_survives_a_gap_between_enemies(state):
    gapped = state.__class__(**{
        **state.__dict__,
        "enemies": (None, None, None,
                    Enemy(name="A", hp=10, max_hp=10, block=0, intent="X", powers=()),
                    None,
                    Enemy(name="B", hp=20, max_hp=20, block=0, intent="Y", powers=())),
    })
    assert from_string(to_string(gapped)).enemies == gapped.enemies


def test_roundtrip_preserves_enemy_powers(state):
    e = Enemy(name="A", hp=10, max_hp=10, block=2,
              intent="X", powers=(("Vulnerable", 2), ("Weak", 1)))
    gapped = state.__class__(**{**state.__dict__, "enemies": (None,) * 5 + (e,)})
    assert from_string(to_string(gapped)).enemies[-1] == e


# ---------------------------------------------------------------------------
# helpers: pair bags
# ---------------------------------------------------------------------------

def test_get_pair_finds_and_defaults():
    bag = (("Strength", 3), ("Vulnerable", 2))
    assert helpers.get_pair(bag, "Strength") == 3
    assert helpers.get_pair(bag, "Vulnerable") == 2
    assert helpers.get_pair(bag, "Weak") == 0
    assert helpers.get_pair((), "Anything") == 0


def test_set_power_preserves_insertion_order():
    bag = (("Zeal", 1), ("Artifact", 2))
    out = helpers.set_power(bag, "Zeal", 9)
    assert out == (("Zeal", 9), ("Artifact", 2)), "resolution order must not change"


def test_set_power_appends_when_absent():
    bag = (("Zeal", 1),)
    assert helpers.set_power(bag, "Artifact", 2) == (("Zeal", 1), ("Artifact", 2))
    assert helpers.set_power((), "Strength", 1) == (("Strength", 1),)


def test_set_counter_sorts_for_canonical_equality():
    a = helpers.set_counter((), "b_key", 1)
    a = helpers.set_counter(a, "a_key", 2)
    b = helpers.set_counter((), "a_key", 2)
    b = helpers.set_counter(b, "b_key", 1)
    assert a == b, "counter bags must be order-independent"
    assert a == (("a_key", 2), ("b_key", 1))


def test_add_power_and_add_counter():
    bag = (("Strength", 3),)
    assert helpers.add_power(bag, "Strength", 2) == (("Strength", 5),)
    assert helpers.add_power(bag, "Dexterity", 2) == (("Strength", 3), ("Dexterity", 2))
    assert helpers.add_power(bag, "Strength", -5) == (("Strength", -2),)
    assert helpers.add_counter((), "played", 1) == (("played", 1),)


# ---------------------------------------------------------------------------
# helpers: tuple splicing
# ---------------------------------------------------------------------------

def test_pile_operations():
    a, b, c = Card(name="A"), Card(name="B"), Card(name="C")
    pile = (a, b)
    assert helpers.add_to(pile, c) == (a, b, c)
    assert helpers.remove_at(pile, 0) == (b,)
    assert helpers.remove_at(pile, 1) == (a,)
    assert helpers.replace_at(pile, 1, c) == (a, c)
    assert pile == (a, b), "originals must not be mutated"


def test_pile_operations_are_generic():
    bag = (("x", 1), ("y", 2))
    assert helpers.replace_at(bag, 0, ("x", 9)) == (("x", 9), ("y", 2))


# ---------------------------------------------------------------------------
# helpers: enemies
# ---------------------------------------------------------------------------

def _enemies(*specs):
    """specs: None for empty slot, int for an enemy at that hp."""
    out = []
    for i, hp in enumerate(specs):
        if hp is None:
            out.append(None)
        else:
            out.append(Enemy(name=f"E{i}", hp=hp, max_hp=50, block=0,
                             intent="X", powers=()))
    return tuple(out)


def test_find_enemies_excludes_none_and_corpses():
    es = _enemies(None, None, 0, 12, None, 30)
    assert helpers.find_enemy_inds(es) == (3, 5)
    assert [e.hp for e in helpers.find_enemies(es)] == [12, 30]


def test_find_enemies_on_empty_board():
    es = _enemies(None, None, None, None, None, None)
    assert helpers.find_enemy_inds(es) == ()
    assert helpers.find_enemies(es) == ()


def test_summon_slot_recycles_corpses_before_extending():
    es = _enemies(None, None, None, 0, 20, 30)
    assert helpers.find_summon_slot(es) == 3, "corpse at 3 should be reused"


def test_summon_slot_extends_leftward_when_no_corpses():
    es = _enemies(None, None, 10, 20, 30, 40)
    assert helpers.find_summon_slot(es) == 1


def test_summon_slot_returns_none_when_full():
    es = _enemies(1, 2, 3, 4, 5, 6)
    assert helpers.find_summon_slot(es) is None


# ---------------------------------------------------------------------------
# gain_block + Vambrace
# ---------------------------------------------------------------------------

def test_gain_block_without_relics():
    st = from_string(NO_VAMBRACE)
    st = gain_block(st, 5, source=A_CARD)
    assert st.player_block == 5


def test_gain_block_accumulates():
    st = from_string(NO_VAMBRACE)
    st = gain_block(st, 5, source=A_CARD)
    st = gain_block(st, 3, source=A_CARD)
    assert st.player_block == 8


def test_gain_block_zero_is_a_noop():
    st = from_string(NO_VAMBRACE)
    st = gain_block(st, 0, source=A_CARD)
    assert st.player_block == 0


def test_vambrace_doubles_card_block(state):
    out = gain_block(state, 5, source=A_CARD)
    assert out.player_block == 10


def test_vambrace_is_spent_after_firing(state):
    out = gain_block(state, 5, source=A_CARD)
    vambrace = next(r for r in out.relics if r.name == "Vambrace")
    assert vambrace.counter == 0


def test_vambrace_only_fires_once(state):
    out = gain_block(state, 5, source=A_CARD)
    out = gain_block(out, 5, source=A_CARD)
    assert out.player_block == 15, "10 from the doubled gain, then 5 undoubled"


def test_vambrace_ignores_non_card_sources(state):
    out = gain_block(state, 5)
    assert out.player_block == 5
    vambrace = next(r for r in out.relics if r.name == "Vambrace")
    assert vambrace.counter == 1, "must not be consumed by a non-card gain"


def test_spent_vambrace_does_not_double():
    st = from_string(VAMBRACE_SPENT)
    out = gain_block(st, 5, source=A_CARD)
    assert out.player_block == 5


def test_gain_block_does_not_mutate_the_input(state):
    before = state.player_block
    gain_block(state, 5, source=A_CARD)
    assert state.player_block == before
    assert next(r for r in state.relics if r.name == "Vambrace").counter == 1