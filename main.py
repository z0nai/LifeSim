# test config
from pool import Pool
from position import Position
from creatures import Agent, Food

pool = Pool(size_x=51, size_y=51, delta_time=1, debug=False, food_per_generation=2)
for i in range(3):
    Agent(species='Asdf', change_chance=0, is_friendly_predator=True, position=Position(-8 * i, -8 * i))
    Agent(species='Fdas', change_chance=0, is_friendly_predator=True, position=Position(-8 * i, 8 * i))
    Agent(species='Faaa', change_chance=0, is_friendly_predator=True, position=Position(8 * i, -8 * i))
    Agent(species='Zfff', change_chance=0, is_friendly_predator=True, position=Position(8 * i, 8 * i))

for _ in range(50):
    Food.create_random(position=pool.random_position())

pool.run()
