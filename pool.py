from time import sleep
from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

from position import Position
from utils import clear

if TYPE_CHECKING:
    from creatures import Creature, Agent, Food

console = Console()


class Cell:
    def __init__(self, pawn: Agent | Food | None = None):
        self.pawn = pawn

    def __repr__(self):
        if self.pawn is None:
            return '· '
        return str(self.pawn)

    __str__ = __repr__


class Pool:
    def __init__(self, size_x: int = 1000, size_y: int = 1000, delta_time: float | int = 1,
                 name_len: int = 3, species_len: int = 4, food_per_generation: int = 5,
                 ticks_to_generation: int = 10,
                 debug: bool = False):
        self.size_x = size_x
        self.size_y = size_y
        self.board = [[Cell() for _ in range(self.size_x)] for _ in range(self.size_y)]

        self.delta_time = delta_time
        self.name_len = name_len
        self.species_len = species_len

        self.creatures = []
        self.names = set()
        self.debug = debug

        self.tick = 0
        self.ticks_to_generation = ticks_to_generation
        self.food_per_generation = food_per_generation

    def add_to_board(self, creature: Creature):
        pool_position = self.get_pool_position(creature.position)
        if 0 <= pool_position.y < self.size_y and 0 <= pool_position.x < self.size_x:
            self.board[pool_position.y][pool_position.x] = Cell(creature)

        self.creatures.append(creature)
        self.names.add(creature.name)
        if creature.species:
            self.names.add(creature.species)

    def display(self):
        if not self.debug:
            for row in self.board:
                row_text = Text()
                for cell in row:
                    if cell.pawn is None:
                        row_text.append(' ·', style='#444444')
                    else:
                        row_text.append(f'{cell.pawn}', style=f'#{cell.pawn.color}')
                console.print(row_text)
        from creatures import Agent
        console.print(*sorted(x.energy for x in self.creatures if isinstance(x, Agent)))
        sleep(self.delta_time)
        clear()

    def move_to(self, position_from: Position, position_to: Position):
        if any(abs(pos.x) > self.size_x // 2 or abs(pos.y) > self.size_y // 2 for pos in (position_from, position_to)):
            return False

        position_from = self.get_pool_position(position_from)
        position_to = self.get_pool_position(position_to)

        if self.board[position_to.y][position_to.x].pawn is not None:
            return False

        self.board[position_from.y][position_from.x], self.board[position_to.y][position_to.x] = \
            self.board[position_to.y][position_to.x], self.board[position_from.y][position_from.x]
        return True

    def get_pool_position(self, position: Position):
        return Position(self.size_x // 2 + position.x, self.size_y // 2 - position.y)

    def destroy(self, creature: Creature):
        transformed_position = self.get_pool_position(creature.position)
        self.board[transformed_position.y][transformed_position.x] = Cell()
        self.creatures.remove(creature)

    def run(self):
        while True:
            self.step()

    def step(self):
        self.display()
        self.food_generator()
        from creatures import Agent
        if not self.creatures:
            return

        max_speed = max([x.speed for x in self.creatures if isinstance(x, Agent)], default=1)
        for cur_step in range(max_speed):
            for creature in self.creatures:
                if not isinstance(creature, Agent):
                    continue

                if creature.speed > cur_step:
                    creature.step()

    def random_position(self):
        from random import randint
        while True:
            target_idx_x = randint(0, self.size_x - 1)
            target_idx_y = randint(0, self.size_y - 1)
            if self.board[target_idx_y][target_idx_x].pawn is None:
                game_x = target_idx_x - (self.size_x // 2)
                game_y = (self.size_y // 2) - target_idx_y

                return Position(game_x, game_y)

    def food_generator(self):
        from creatures import Food
        self.tick += 1
        if self.tick % self.ticks_to_generation == 0:
            for _ in range(self.food_per_generation):
                Food.create_random(position=self.random_position())
            self.tick = 0
