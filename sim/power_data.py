from .events import Event

POWER_LISTENERS = {
    ("Feel_No_Pain", Event.ON_EXHAUST): feel_no_pain_listener,
}

POWER_QUERIES = {
    ("Corruption", Event.GET_CARD_COST): corruption_cost,
}