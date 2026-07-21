from math import sqrt


class Position:
    __slots__ = ('x', 'y', 'rot')

    def __init__(self, x: int = 0, y: int = 0, rot: int | float = 0):
        self.x = x
        self.y = y
        self.rot = rot % 360

    def __add__(self, other: 'Position') -> 'Position':
        return Position(self.x + other.x, self.y + other.y, self.rot + other.rot)

    def __iadd__(self, other: 'Position') -> 'Position':
        self.x += other.x
        self.y += other.y
        self.rot = (self.rot + other.rot) % 360
        return self

    def __sub__(self, other: 'Position') -> 'Position':
        return Position(self.x - other.x, self.y - other.y)

    def __matmul__(self, other: 'Position') -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return sqrt(dx * dx + dy * dy)

    def __repr__(self) -> str:
        rot_part = f', {round(self.rot, 3)}' if self.rot else ''
        return f'<{round(self.x, 3)}, {round(self.y, 3)}{rot_part}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Position):
            return NotImplemented
        return self.x == other.x and self.y == other.y and self.rot == other.rot

    def __iter__(self):
        yield self.x
        yield self.y

    @staticmethod
    def from_list(lst: list | tuple) -> 'Position':
        keys = ('x', 'y', 'rot')
        return Position(**{k: v for k, v in zip(keys, lst)})

    def to_list(self) -> tuple:
        return self.x, self.y, self.rot

    __str__ = __repr__
    __radd__ = __add__
    get_distance = __matmul__
