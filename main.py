from pool import Pool
from position import Position
from creatures import Agent

pool = Pool(size_x=51, size_y=51, delta_time=0, food_per_generation=50,
            ticks_to_generation=1, name_len=8, species_len=8)
for _ in range(100):
    Agent(position=pool.random_position(), base_energy_to_breeding=5, base_energy=50,
          change_chance=0.9, speed=1, view_range=10, fov=90, power=2, base_health=50)
pool.run()