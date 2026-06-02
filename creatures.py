from math import atan2, degrees
from random import choice, random

from pool import Pool
from position import Position
from utils import generate_color, default_effects, default_immunities, multiplier, generate_available, food_emoji, \
    agent_emoji, routes


class Creature:
    def __init__(self,
                 name: str = '',
                 position: Position = None,
                 color: str = None,
                 species: str = None,
                 change_chance: float = None):
        self.position = position if position is not None else Position()
        self.color = color if color is not None else generate_color()
        self.change_chance = change_chance if change_chance is not None else 0.01

        import main
        self.name = generate_available(name, main.pool.name_len)
        self.species = generate_available(species, main.pool.species_len)
        main.pool.add_to_board(self)

    def __eq__(self, other: Creature):
        if not isinstance(other, Creature):
            return False
        return self.species == other.species and self.color == other.color

    @classmethod
    def create_random(cls, **kwargs):
        from random import random, choice, randint

        if cls.__name__ == 'Agent':
            import main
            original_add = main.pool.add_to_board
            main.pool.add_to_board = lambda x: None
            try:
                dummy_agent = Agent()
                new_fields = vars(dummy_agent).copy()
            finally:
                main.pool.add_to_board = original_add

            new_fields.update(kwargs)

            change_chance = new_fields['change_chance']
            has_mutation = False

            for field in list(new_fields.keys()):
                value = new_fields[field]
                if isinstance(value, (float, int)) and field != 'energy_per_step':
                    if random() <= change_chance and multiplier.get(field) is not None:
                        k = 1 if random() >= 0.5 else -1
                        if isinstance(value, float):
                            new_fields[field] = value + round(value * 0.1, 3) * k
                        else:
                            new_fields[field] = value + int(round(value * 0.1, 0)) * k
                        has_mutation = True

            immunities = new_fields['immunities'].copy()
            for k, v in immunities.items():
                if random() <= change_chance:
                    immunities[k] = not v
                    has_mutation = True
            new_fields['immunities'] = immunities

            if has_mutation:
                new_fields['species'] = None
                new_fields['color'] = None
            else:
                if 'species' not in kwargs:
                    new_fields['species'] = None
                if 'color' not in kwargs:
                    new_fields['color'] = None

            if new_fields['position'] is not None:
                new_fields['position'] += Position().from_list(
                    choice([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]))

            new_fields.pop('health', None)
            new_fields.pop('energy', None)
            new_fields.pop('name', None)
            new_fields.pop('energy_per_step', None)
            new_fields.pop('energy_to_breeding', None)

            return cls(**new_fields)

        elif cls.__name__ == 'Food':
            new_fields = {
                'saturation': randint(1, 10),
                'position': Position()
            }
            new_fields.update(kwargs)
            return cls(**new_fields)
        else:
            return cls(**kwargs)


class Food(Creature):
    def __init__(self,
                 saturation: float | int = 5,
                 effects_on_eat: dict = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.saturation = saturation
        self.effects_on_eat = effects_on_eat if effects_on_eat is not None else default_effects()
        self.printable = choice(food_emoji)

    def __repr__(self):
        import main
        if main.pool.debug:
            return f'Food at {self.position}'
        else:
            return self.printable

    __str__ = __repr__


class Agent(Creature):
    def __init__(self,
                 base_health: float | int = 100,
                 base_energy: float | int = 100,
                 base_energy_to_breeding: float | int = 50,
                 energy_per_step: float | int = 1,
                 speed: float | int = 5,
                 fov: float | int = 178,
                 view_range: float | int = 25,
                 is_herbivores: bool = True,
                 is_predator: bool = True,
                 is_friendly_predator: bool = True,
                 power: float | int = 10,
                 immunities: dict = None,
                 effects: dict = None,
                 **kwargs):

        super().__init__(**kwargs)
        self.base_health = base_health
        self.health = base_health

        self.base_energy = base_energy
        self.energy = base_energy
        self.energy_per_step = energy_per_step
        self.base_energy_to_breeding = base_energy_to_breeding
        self.energy_to_breeding = base_energy_to_breeding

        self.fov = fov
        self.view_range = view_range
        self.speed = speed
        self.immunities = immunities if immunities is not None else default_immunities()
        self.effects = effects if effects is not None else default_effects()

        self.power = power
        self.is_predator = is_predator
        self.is_friendly_predator = is_friendly_predator
        self.is_herbivores = is_herbivores

    def filter_creatures(self, creature: Creature):
        if self is creature:
            return False
        if self.position @ creature.position > self.view_range:
            return False

        diff = creature.position - self.position
        target_angle = degrees(atan2(diff.y, diff.x))

        angle_diff = target_angle - self.position.rot
        angle_diff = (angle_diff + 180) % 360 - 180

        return round(abs(angle_diff), 4) <= (self.fov / 2)

    def see_creatures(self):
        import main
        return list(filter(self.filter_creatures, main.pool.creatures))

    def food_sources(self):

        def food_filter(source: Creature):
            flag = False
            if isinstance(source, Food) and self.is_herbivores:
                flag = True
            if isinstance(source, Agent) and self.is_predator:
                flag = True
                if source.species == self.species and self.is_friendly_predator:
                    flag = False
            return flag

        return list(filter(food_filter, self.see_creatures()))

    def change_field(self, field, value):
        if random() > self.change_chance or multiplier.get(field) is None:
            return value
        k = 1 if random() >= 0.5 else -1

        if field == 'base_energy':
            self.energy_per_step += multiplier[field] * k

        if isinstance(value, float):
            return value + round(value * 0.1, 3) * k
        return value + int(round(value * 0.1, 0)) * k

    def create_child(self):
        fields = vars(self)
        new_fields = {}
        has_mutation = False

        for field, value in fields.items():
            if isinstance(value, (float, int)):
                new_value = self.change_field(field, value)
                new_fields[field] = new_value
                if new_value != value:
                    has_mutation = True
            elif field == 'position':
                new_fields[field] = Position(value.x, value.y, value.rot)
            elif field == 'effects':
                new_fields[field] = value.copy()
            else:
                new_fields[field] = value

        immunities = fields['immunities'].copy()
        for k, v in immunities.items():
            if random() <= self.change_chance:
                immunities[k] = not v
                has_mutation = True
        new_fields['immunities'] = immunities

        if has_mutation:
            new_fields['species'] = None
            new_fields['color'] = None
        else:
            new_fields['species'] = self.species

        new_fields.pop('health', None)
        new_fields.pop('energy', None)
        new_fields.pop('name', None)
        new_fields.pop('energy_per_step', None)
        new_fields.pop('energy_to_breeding', None)

        new_fields['position'] += Position().from_list(
            lst=choice([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]))

        return Agent(**new_fields)

    @property
    def direction(self):
        angle = self.position.rot % 360
        if angle < 22.5 or angle >= 337.5:
            return 'E'
        elif 22.5 <= angle < 67.5:
            return 'NE'
        elif 67.5 <= angle < 112.5:
            return 'N'
        elif 112.5 <= angle < 157.5:
            return 'NW'
        elif 157.5 <= angle < 202.5:
            return 'W'
        elif 202.5 <= angle < 247.5:
            return 'SW'
        elif 247.5 <= angle < 292.5:
            return 'S'
        else:
            return 'SE'

    @property
    def is_alive(self):
        return self.health > 0 and self.energy > 0

    def eat(self, food: Food):
        import main
        self.energy += food.saturation
        self.energy_to_breeding -= food.saturation
        target_pos = Position(food.position.x, food.position.y)
        main.pool.destroy(food)
        main.pool.move_to(self.position, target_pos)
        self.position.x = target_pos.x
        self.position.y = target_pos.y

    def try_to_breed(self):
        if self.energy_to_breeding <= 0:
            self.energy_to_breeding += self.base_energy_to_breeding
            self.create_child()

    def apply_effects(self):
        for effect in self.effects:
            if self.effects[effect] and effect.__class__ not in self.immunities:
                effect.apply(self)
                effect.tick()
            if effect.is_expired:
                self.effects[effect] = False

    def attack(self, agent: Agent):
        agent.health -= self.power
        import main
        if not agent.is_alive:
            target_pos = Position(agent.position.x, agent.position.y)
            main.pool.destroy(agent)
            main.pool.move_to(self.position, target_pos)
            self.position.x = target_pos.x
            self.position.y = target_pos.y

    def step(self):
        import main
        if not self.is_alive:
            target_pos = Position(self.position.x, self.position.y)
            main.pool.destroy(self)
            main.pool.move_to(self.position, target_pos)
            self.position.x = target_pos.x
            self.position.y = target_pos.y
            return
        self.try_to_breed()
        self.apply_effects()
        nearest = sorted(self.food_sources(), key=lambda x: self.position @ x.position)
        if nearest:
            nearest = nearest[0]
            self.position.rot = degrees(
                atan2(nearest.position.y - self.position.y, nearest.position.x - self.position.x))

            if nearest.position @ self.position >= 2:
                self.energy -= self.energy_per_step
                import main
                old_pos = Position(self.position.x, self.position.y, self.position.rot)
                move_vector = routes[self.direction]
                new_pos = Position(self.position.x + move_vector.x, self.position.y + move_vector.y,
                                   self.position.rot)

                if main.pool.move_to(old_pos, new_pos):
                    self.position.x = new_pos.x
                    self.position.y = new_pos.y
            else:
                if isinstance(nearest, Food):
                    self.eat(nearest)
                else:
                    self.attack(nearest)
        else:
            self.position.rot += self.fov * 1.5

    def __repr__(self):
        import main
        if main.pool.debug:
            return f'Agent at {self.position}'
        else:
            return agent_emoji[self.direction]

    __str__ = __repr__
