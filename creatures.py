from math import atan2, degrees, ceil
from random import choice, random, randint

from position import Position
from utils import (
    generate_color,
    multiplier,
    generate_available,
    food_emoji,
    agent_emoji,
    routes,
)

# Pre-built offset list used for child/food placement
_SPAWN_OFFSETS = [
    Position(-1, -1),
    Position(-1, 0),
    Position(-1, 1),
    Position(0, -1),
    Position(0, 1),
    Position(1, -1),
    Position(1, 0),
    Position(1, 1),
]

# Fields stripped from create_child / create_random before passing to constructor
_CHILD_STRIP = frozenset(
    {
        "health",
        "energy",
        "name",
        "energy_per_step",
        "energy_to_breeding",
        "_bred_this_tick",
    }
)


class Creature:
    def __init__(
        self,
        name: str = "",
        position: Position = None,
        color: str = None,
        species: str = None,
        change_chance: float = None,
    ):
        import main

        self.position = position if position is not None else Position()
        self.color = color if color is not None else generate_color()
        self.change_chance = max(
            0.0, min(1.0, change_chance if change_chance is not None else 0.01)
        )
        self.name = generate_available(name, main.pool.name_len)
        self.species = generate_available(species, main.pool.species_len)
        main.pool.add_to_board(self)

    @classmethod
    def create_random(cls, **kwargs):
        from random import randint

        if cls.__name__ == "Agent":
            import main

            # Create a dummy agent without registering it, to snapshot defaults
            orig_add = main.pool.add_to_board
            orig_names = main.pool.names.copy()
            main.pool.add_to_board = lambda x: None
            try:
                dummy = Agent()
                new_fields = vars(dummy).copy()
            finally:
                main.pool.add_to_board = orig_add
                main.pool.names = orig_names

            new_fields.update(kwargs)
            change_chance = new_fields["change_chance"]
            has_mutation = False

            for field, value in list(new_fields.items()):
                if isinstance(value, (float, int)) and field != "energy_per_step":
                    if random() <= change_chance and multiplier.get(field) is not None:
                        k = 1 if random() >= 0.5 else -1
                        if isinstance(value, float):
                            new_fields[field] = round(value + value * 0.1 * k, 3)
                        else:
                            new_fields[field] = value + int(round(value * 0.1)) * k
                        has_mutation = True

            if has_mutation:
                new_fields["species"] = None
                new_fields["color"] = None
            else:
                if "species" not in kwargs:
                    new_fields["species"] = None
                if "color" not in kwargs:
                    new_fields["color"] = None

            if new_fields["position"] is not None:
                new_fields["position"] = new_fields["position"] + choice(_SPAWN_OFFSETS)

            for key in _CHILD_STRIP:
                new_fields.pop(key, None)

            return cls(**new_fields)

        elif cls.__name__ == "Food":
            new_fields = {"saturation": randint(1, 10), "position": Position()}
            new_fields.update(kwargs)
            return cls(**new_fields)

        return cls(**kwargs)


class Food(Creature):
    def __init__(
        self, saturation: float | int = 5, **kwargs
    ):
        super().__init__(**kwargs)
        self.saturation = saturation
        self.printable = choice(food_emoji)

    def __repr__(self) -> str:
        import main

        return f"Food at {self.position}" if main.pool.debug else self.printable

    __str__ = __repr__


class Agent(Creature):
    def __init__(
        self,
        base_health: float | int = 100,
        base_energy: float | int = 100,
        base_energy_to_breeding: float | int = 50,
        speed: float | int = 5,
        fov: float | int = 178,
        view_range: float | int = 25,
        is_herbivores: bool = True,
        is_predator: bool = True,
        is_friendly_predator: bool = True,
        power: float | int = 10,

        generation: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_health = base_health
        self.health = base_health

        self.base_energy = base_energy
        self.energy = base_energy
        self.base_energy_to_breeding = base_energy_to_breeding
        self.energy_to_breeding = base_energy_to_breeding

        self.fov = max(1, min(360, fov))
        self.view_range = view_range
        self.speed = speed

        self.power = power
        self.is_predator = is_predator
        self.is_friendly_predator = is_friendly_predator
        self.is_herbivores = is_herbivores
        self.generation = generation

        if not is_predator and not is_herbivores:
            if random() >= 0.5:
                self.is_herbivores = True
            else:
                self.is_predator = True

        # Cached energy cost; recomputed whenever relevant stats change
        self._energy_per_step_cache: int | None = None
        self._bred_this_tick: bool = False

    # ------------------------------------------------------------------
    # Energy cost cache — invalidated by any stat mutation
    # ------------------------------------------------------------------
    def _invalidate_energy_cache(self) -> None:
        self._energy_per_step_cache = None

    def _compute_energy_per_step(self) -> int:
        base_cost = 2
        total = (
            (self.speed / 5.0) ** 2
            + (self.power / 10.0) ** 2
            + (self.view_range / 25.0) ** 1.5
            + (self.fov / 180.0) ** 1.5
            + (self.base_health / 100.0) ** 1.2
            + (self.base_energy / 100.0) ** 1.2
        )
        return max(1, ceil(base_cost + base_cost * 0.2 * total))

    @property
    def energy_per_step(self) -> int:
        if self._energy_per_step_cache is None:
            self._energy_per_step_cache = self._compute_energy_per_step()
        return self._energy_per_step_cache

    # ------------------------------------------------------------------
    # Vision
    # ------------------------------------------------------------------
    def filter_creatures(self, creature: Creature) -> bool:
        if self is creature:
            return False
        if self.position @ creature.position > self.view_range:
            return False
        diff = creature.position - self.position
        angle_diff = degrees(atan2(diff.y, diff.x)) - self.position.rot
        angle_diff = (angle_diff + 180) % 360 - 180
        return round(abs(angle_diff), 4) <= self.fov / 2

    def see_creatures(self) -> list["Creature"]:
        import main

        return [c for c in main.pool.creatures if self.filter_creatures(c)]

    def food_sources(self) -> list["Creature"]:
        is_herb = self.is_herbivores
        is_pred = self.is_predator
        own_species = self.species
        friendly = self.is_friendly_predator

        result = []
        for c in self.see_creatures():
            if isinstance(c, Food):
                if is_herb:
                    result.append(c)
            elif isinstance(c, Agent):
                if is_pred and not (c.species == own_species and friendly):
                    result.append(c)
        return result

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------
    def change_field(self, field: str, value):
        if random() > self.change_chance or multiplier.get(field) is None:
            return value
        k = 1 if random() >= 0.5 else -1

        if field == "change_chance":
            new_value = round(value + k * 10 ** randint(-3, -1), 3)
        elif isinstance(value, bool):
            return not value
        elif isinstance(value, float):
            new_value = round(value + value * 0.1 * k, 3)
        else:
            change = int(round(value * 0.1)) or 1
            new_value = value + change * k

        if field in (
            "base_energy_to_breeding",
            "base_health",
            "base_energy",
            "speed",
            "view_range",
            "energy_per_step",
        ):
            return max(1, new_value)
        if field == "fov":
            return max(1, min(360, new_value))
        if field == "change_chance":
            return max(0.0, min(1.0, new_value))
        return new_value

    # ------------------------------------------------------------------
    # Reproduction
    # ------------------------------------------------------------------
    def create_child(self) -> "Agent | None":
        fields = vars(self).copy()
        new_fields: dict = {}
        has_mutation = False
        new_gen = fields.pop("generation")

        for field, value in fields.items():
            if field in _CHILD_STRIP or field.startswith("_"):
                continue
            if isinstance(value, (float, int)):
                new_value = self.change_field(field, value)
                new_fields[field] = new_value
                if new_value != value:
                    has_mutation = True
                    self._invalidate_energy_cache()
            elif field == "position":
                new_fields[field] = Position(value.x, value.y, value.rot)
            else:
                new_fields[field] = value

        if has_mutation:
            new_fields["species"] = None
            new_fields["color"] = None
        else:
            new_fields["species"] = self.species

        import main

        for _ in range(8):
            new_pos = self.position + choice(_SPAWN_OFFSETS)
            if main.pool.is_cell_empty(new_pos):
                break
        else:
            return None

        new_fields["position"] = new_pos
        new_fields["generation"] = new_gen + 1
        return Agent(**new_fields)

    # ------------------------------------------------------------------
    # Direction property
    # ------------------------------------------------------------------
    @property
    def direction(self) -> str:
        angle = self.position.rot % 360
        if angle < 22.5 or angle >= 337.5:
            return "E"
        if angle < 67.5:
            return "NE"
        if angle < 112.5:
            return "N"
        if angle < 157.5:
            return "NW"
        if angle < 202.5:
            return "W"
        if angle < 247.5:
            return "SW"
        if angle < 292.5:
            return "S"
        return "SE"

    @property
    def is_dead(self) -> bool:
        return self.health <= 0 or self.energy <= 0

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def eat(self, food: "Food") -> None:
        import main

        self.energy += food.saturation
        if self.energy > self.base_energy:
            overflow = self.energy - self.base_energy
            self.health = min(self.health + overflow, self.base_health)
            self.energy = self.base_energy
        self.energy_to_breeding = max(self.energy_to_breeding - food.saturation, 0)
        target_pos = Position(food.position.x, food.position.y)
        main.pool.destroy(food)
        if main.pool.move_to(self.position, target_pos):
            self.position.x = target_pos.x
            self.position.y = target_pos.y

    def try_to_breed(self) -> None:
        if self.energy_to_breeding <= 0:
            birth_cost = self.base_energy_to_breeding
            if self.energy > birth_cost + 10:
                self.energy -= birth_cost
                self.energy_to_breeding = self.base_energy_to_breeding
                # self._bred_this_tick = True
                child = self.create_child()
                if child is None:
                    self.energy += birth_cost  # refund if no space
                else:
                    import main

                    main.pool.register_birth()

    def attack(self, agent: "Agent") -> None:
        import main

        agent.health -= self.power
        if agent.is_dead:
            self.energy = min(self.energy + agent.base_health, self.base_energy)
            saturation = min(self.power * 2, agent.base_health)
            self.energy_to_breeding = max(self.energy_to_breeding - saturation, 0)
            target_pos = Position(agent.position.x, agent.position.y)
            main.pool.destroy(agent)
            if main.pool.move_to(self.position, target_pos):
                self.position.x = target_pos.x
                self.position.y = target_pos.y

    def step(self) -> None:
        import main

        if self.is_dead:
            main.pool.destroy(self)
            return

        self.energy -= self.energy_per_step
        if self.is_dead:
            main.pool.destroy(self)
            return

        if not self._bred_this_tick:
            self.try_to_breed()

        # Find nearest target (pre-sort only the visible set, not all creatures)
        sources = self.food_sources()
        if sources:
            nearest = min(sources, key=lambda c: self.position @ c.position)
            self.position.rot = degrees(
                atan2(
                    nearest.position.y - self.position.y,
                    nearest.position.x - self.position.x,
                )
            )

            if nearest.position @ self.position >= 2:
                move_vector = routes[self.direction]
                new_pos = Position(
                    self.position.x + move_vector.x,
                    self.position.y + move_vector.y,
                    self.position.rot,
                )
                if main.pool.move_to(self.position, new_pos):
                    self.position.x = new_pos.x
                    self.position.y = new_pos.y
            else:
                if isinstance(nearest, Food):
                    self.eat(nearest)
                else:
                    self.attack(nearest)
        else:
            self.position.rot += self.fov * 1.5

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        import main

        return (
            f"Agent at {self.position}"
            if main.pool.debug
            else agent_emoji[self.direction]
        )

    __str__ = __repr__
