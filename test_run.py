import random
from sim.enemy_data import spawn_encounter, ENCOUNTERS
from sim.actions import run_fight, legal_actions
from dataclasses import replace
from sim.serialize import from_string
import time


rng = random.Random(0)
state = from_string("Defend;Strike;Ascenders_Bane;Defend;Strike/Bash;Defend;Defend;Strike;Strike;Strike///64/80/0/0/249/0/3/3/0//Burning_Blood:1,Golden_Pearl:1,Vambrace:1/Empty,Empty//1/")
state = replace(state, enemies=spawn_encounter(["Corpse_Slug", "Corpse_Slug"], rng))

def randAct(state, mask):
    return rng.choice([i for i, ok in enumerate(mask) if ok])

print(state.enemies)
t0 = time.perf_counter()
final = run_fight(state, randAct, rng)
print(final)
print(f"{time.perf_counter() - t0:.4f}s")