from .gamestate import GameState



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
    if name in inner: raise ValueError(name + " already registered under " + event)
    inner[name] = handler


def emit(event, state, **kwargs) -> GameState:
    relic_table = RELIC_EMIT.get(event, {})
    power_table = POWER_EMIT.get(event, {})
    card_table = CARD_EMIT.get(event, {})

    if not relic_table and not power_table and not card_table:
        return state
    
    for relic in state.relics:
        handler = relic_table.get(relic.name)
        if handler:
            state = handler(state, **kwargs)
    for power, _ in state.player_powers:
        handler = power_table.get(power)
        if handler:
            state = handler(state, **kwargs)
    for card in state.hand:
        handler = card_table.get(card.name)
        if handler:
            state = handler(state, **kwargs)
    return state