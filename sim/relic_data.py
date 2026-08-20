from .engine import register, RELIC_QUERY_ADD, RELIC_QUERY_OVER, RELIC_EMIT
from .events import Event
from dataclasses import replace
from .helpers import replace_at
from .card import Card
from .gamestate import GameState


def vambrace_commit(state, relic=None, relic_ind=None, source=None, **kwargs) -> GameState:
    if(_vambrace_active(relic, source)):
        new_relic = replace(relic, counter=0)
        new_list = replace_at(state.relics, relic_ind, new_relic)
        state = replace(state, relics=new_list)
        return state
    return state

def _vambrace_active(relic, source) -> bool:
    return (relic.counter == 1 and isinstance(source, Card))
    
def vambrace(state, value, relic=None, source=None, **kwargs) -> int:
    if(_vambrace_active(relic, source)):
        return value * 2
    return value

register(RELIC_QUERY_OVER, "Vambrace", Event.GET_BLOCK, vambrace)
register(RELIC_EMIT, "Vambrace", Event.ON_BLOCK_GAINED, vambrace_commit)