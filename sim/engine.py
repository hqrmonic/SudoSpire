from .gamestate import GameState
from dataclasses import replace
from .events import Event

# Emit handles all the cases where relics give additional affects upon something being triggered
RELIC_EMIT = {}
POWER_EMIT = {}
CARD_EMIT = {}

#Query handles any instance that modifies numbers on cards. So dex giving extra block on a block card is handled by this. ADD handles the additive increases, and OVER the multipliative ones.
RELIC_QUERY_ADD = {}
RELIC_QUERY_OVER = {}
POWER_QUERY_ADD = {}
POWER_QUERY_OVER = {}
CARD_QUERY_ADD = {}
CARD_QUERY_OVER = {}

def register(table, name, event, handler):
    inner = table.setdefault(event, {})
    if name in inner: raise ValueError(name + " already registered under " + event)
    inner[name] = handler


def emit(event, state, **kwargs) -> GameState:
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

def _walk(relic_table, power_table, card_table, state, value, **kwargs):

    if not relic_table and not power_table and not card_table:
        return value

    for i, relic in enumerate(state.relics):
        handler = relic_table.get(relic.name)
        if handler:
            value = handler(state, value, relic=relic, relic_ind=i, **kwargs)
    for i, power in enumerate(state.player_powers):
        handler = power_table.get(power[0])
        if handler:
            value = handler(state, value, power_pair=power, power_ind=i, **kwargs)
    for i, card in enumerate(state.hand):
        handler = card_table.get(card.name)
        if handler:
            value = handler(state, value, card=card, card_ind=i, **kwargs)
    return value

def query(event, state, value, **kwargs):
    relic_table = RELIC_QUERY_ADD.get(event, {})
    power_table = POWER_QUERY_ADD.get(event, {})
    card_table = CARD_QUERY_ADD.get(event, {})

    value = _walk(relic_table, power_table, card_table, state, value, **kwargs)

    relic_table = RELIC_QUERY_OVER.get(event, {})
    power_table = POWER_QUERY_OVER.get(event, {})
    card_table = CARD_QUERY_OVER.get(event, {})   

    value = _walk(relic_table, power_table, card_table, state, value, **kwargs)

    return value





def gain_block(state, amount, source=None) -> GameState:
    amount = query(Event.GAIN_BLOCK, state, amount)
    amount = max(0, amount)
    state = replace(state, player_block=state.player_block + amount)
    if (amount > 0):
        state = emit(Event.ON_BLOCK_GAINED, state, amount=amount, source=source)
    return state

