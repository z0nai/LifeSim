from math import sqrt


class Position:
    def __init__(self, x: int = 0, y: int = 0, rot: int | float = 0):
        self.x = x
        self.y = y
        self.rot = rot % 360

    def __add__(self, other: Position):
        return Position(self.x + other.x, self.y + other.y, self.rot + other.rot)

    def __iadd__(self, other: Position):
        self.x += other.x
        self.y += other.y
        self.rot = (self.rot + other.rot) % 360
        return self

    def __sub__(self, other: Position):
        return Position(self.x - other.x, self.y - other.y)

    def __matmul__(self, other: Position) -> float:
        diff = self - other
        matching_squared = diff.x ** 2 + diff.y ** 2
        return sqrt(matching_squared)

    def __repr__(self):
        return f'<{round(self.x, 3)}, {round(self.y, 3)}{f", {round(self.rot, 3)}" if self.rot else ""}>'

    def __eq__(self, other: Position):
        return self.x == other.x and self.y == other.y and self.rot == other.rot

    def __iter__(self):
        yield self.x
        yield self.y
        # yield self.rot

    @staticmethod
    def from_list(lst: list | tuple):
        keys = ['x', 'y', 'rot']
        return Position(**{var: val for var, val in zip(keys, lst)})

    def to_list(self):
        return self.x, self.y, self.rot

    __str__ = __repr__
    __radd__ = __add__
    get_distance = __matmul__

