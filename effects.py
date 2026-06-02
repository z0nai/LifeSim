from random import randint
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import creatures


class Effect:
    def __init__(self, duration: float | int, level: int = 1):
        self.duration = duration
        self.level = level

    @property
    def is_expired(self) -> bool:
        return self.duration <= 0

    def tick(self) -> None:
        import main
        self.duration -= main.pool.delta_time

    def apply(self, target: creatures.Creature) -> None:
        pass

    def __add__(self, other: Effect):
        if self.__class__ != other.__class__:
            raise TypeError

        self_vars = vars(self)
        other_vars = vars(other)
        new_fields = {}
        if self.level == other.level:
            for field in self_vars:
                new_fields[field] = self_vars[field] + other_vars[field]
        else:
            for field in self_vars:
                new_fields[field] = max(self_vars[field], other_vars[field])
        return self.__class__(**new_fields)

    def __repr__(self):
        return f'{self.__class__.__name__}({", ".join((f"{key}: {value}" for key, value in vars(self).items()))})'

    __str__ = __repr__


class Poison(Effect):
    def __init__(self, damage_per_tick: float | int = 5, **kwargs):
        super().__init__(**kwargs)
        self.damage_per_tick = damage_per_tick

    def apply(self, target: creatures.Creature) -> None:
        target.health -= self.damage_per_tick


class InstantHeal(Effect):
    def __init__(self, amount: float | int = 25):
        super().__init__(duration=0)
        self.amount = amount

    def apply(self, target: creatures.Creature) -> None:
        target.health += self.amount


class InstantDamage(Effect):
    def __init__(self, amount: float | int = 25):
        super().__init__(duration=0)
        self.amount = amount

    def apply(self, target: creatures.Creature) -> None:
        target.health -= self.amount


class Nausea(Effect):
    def __init__(self, max_rotation: int = 45, **kwargs):
        super().__init__(**kwargs)
        self.max_rotation = max_rotation

    def apply(self, target: creatures.Creature) -> None:
        target.position.rot += randint(-self.max_rotation, self.max_rotation)
