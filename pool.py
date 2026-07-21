from time import sleep, time
from typing import TYPE_CHECKING
from rich.console import Console
from rich.text import Text
from collections import Counter
from position import Position
from utils import clear, get_field_priority, order

if TYPE_CHECKING:
    from creatures import Creature, Agent, Food

console = Console()

# Fields that define a species "signature" — static traits only.
# Excluded: dynamic runtime values (health, energy, energy_to_breeding),
#           identity fields (name, color, species, position),
#           lineage (generation), internal flags.
_SPECIES_SIGNATURE_FIELDS: frozenset[str] = frozenset(
    {
        "base_health",
        "base_energy",
        "base_energy_to_breeding",
        "speed",
        "fov",
        "view_range",
        "power",
        "change_chance",
        "is_herbivores",
        "is_predator",
        "is_friendly_predator",
    }
)


def _agent_signature(agent: "Agent") -> tuple:
    """Return a hashable snapshot of an agent's static traits."""
    parts = []
    for field in sorted(_SPECIES_SIGNATURE_FIELDS):
        value = getattr(agent, field, None)
        parts.append(value)
    return tuple(parts)


class Cell:
    __slots__ = ("pawn",)

    def __init__(self, pawn: "Agent | Food | None" = None):
        self.pawn = pawn

    def __repr__(self) -> str:
        return "· " if self.pawn is None else str(self.pawn)

    __str__ = __repr__


class Pool:
    def __init__(
        self,
        size_x: int = 1000,
        size_y: int = 1000,
        delta_time: float | int = 1,
        name_len: int = 3,
        species_len: int = 4,
        food_per_generation: int = 5,
        ticks_to_generation: float | int = 10,
        debug: bool = False,
    ):
        self.size_x = size_x
        self.size_y = size_y
        self.half_x = size_x // 2
        self.half_y = size_y // 2

        self.board: list[list[Cell]] = [
            [Cell() for _ in range(size_x)] for _ in range(size_y)
        ]

        self.frame_time: float = 0
        self.delta_time = delta_time
        self.name_len = name_len
        self.species_len = species_len
        self.sucess = True

        # Use list for ordered iteration; set for fast membership checks
        self.creatures: list["Creature"] = []
        self._creature_set: set[int] = set()  # id(creature) for O(1) lookup
        self.names: set[str] = set()
        self.debug = debug

        self.tick = 1
        self.ticks_to_generation = ticks_to_generation
        self.food_per_generation = food_per_generation

        # Caches invalidated when creatures list changes
        self._agents_cache: list["Agent"] | None = None
        self._food_cache: list["Food"] | None = None

        # Species registry: signature → species_name
        # Allows newly born agents to inherit an existing species
        # if their static traits exactly match a known one.
        self._species_registry: dict[tuple, str] = {}

        # Statistics
        self.births: int = 0
        self.deaths: int = 0
        self.start_time: float = time()



    # ------------------------------------------------------------------
    # Internal cache helpers
    # ------------------------------------------------------------------
    def _invalidate_cache(self) -> None:
        self._agents_cache = None
        self._food_cache = None

    def get_agents(self) -> list["Agent"]:
        if self._agents_cache is None:
            from creatures import Agent

            self._agents_cache = [c for c in self.creatures if isinstance(c, Agent)]
        return self._agents_cache

    def get_food(self) -> list["Food"]:
        if self._food_cache is None:
            from creatures import Agent

            self._food_cache = [c for c in self.creatures if not isinstance(c, Agent)]
        return self._food_cache

    # ------------------------------------------------------------------
    # Board coordinate helpers
    # ------------------------------------------------------------------
    def to_board_xy(self, position: Position) -> tuple[int, int]:
        """Convert game coordinates → board (col, row) indices."""
        return self.half_x + position.x, self.half_y - position.y

    def get_pool_position(self, position: Position) -> Position:
        bx, by = self.to_board_xy(position)
        return Position(bx, by)

    # ------------------------------------------------------------------
    # Existence / membership
    # ------------------------------------------------------------------
    def contains(self, creature: "Creature") -> bool:
        return id(creature) in self._creature_set

    # ------------------------------------------------------------------
    # Species registry
    # ------------------------------------------------------------------
    def resolve_species(self, agent: "Agent") -> str:
        """Return an existing species name if the agent's static traits
        match a known species, otherwise register the agent's own species
        name under its signature and return it.

        Called from add_to_board only for Agent instances.
        """
        sig = _agent_signature(agent)
        if sig in self._species_registry:
            # Known genotype → reuse existing species label
            return self._species_registry[sig]
        # New genotype → register under the agent's own species name
        self._species_registry[sig] = agent.species
        return agent.species

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def add_to_board(self, creature: "Creature") -> bool:
        bx, by = self.to_board_xy(creature.position)
        if 0 <= by < self.size_y and 0 <= bx < self.size_x:
            if self.board[by][bx].pawn is not None:
                return False
            self.board[by][bx] = Cell(creature)

        self.creatures.append(creature)
        self._creature_set.add(id(creature))
        self.names.add(creature.name)
        if creature.species:
            self.names.add(creature.species)

        # Resolve species for agents: inherit existing label if traits match
        from creatures import Agent

        if isinstance(creature, Agent):
            resolved = self.resolve_species(creature)
            if resolved != creature.species:
                creature.species = resolved  # adopt the canonical species name

        self._invalidate_cache()
        return True

    # ------------------------------------------------------------------
    # Removalа
    # ------------------------------------------------------------------
    def destroy(self, creature: "Creature") -> None:
        if not self.contains(creature):
            return
        from creatures import Agent

        if isinstance(creature, Agent):
            self.deaths += 1
        bx, by = self.to_board_xy(creature.position)
        self.board[by][bx] = Cell()
        self.creatures.remove(creature)
        self._creature_set.discard(id(creature))
        self._invalidate_cache()

    # ------------------------------------------------------------------
    # Birth counter (called by Agent.try_to_breed on successful birth)
    # ------------------------------------------------------------------
    def register_birth(self) -> None:
        self.births += 1

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------
    def move_to(self, pos_from: Position, pos_to: Position) -> bool:
        if not self.is_avaliable(pos_from) or not self.is_avaliable(pos_to):
            return False
        fx, fy = self.to_board_xy(pos_from)
        tx, ty = self.to_board_xy(pos_to)
        if self.board[ty][tx].pawn is None:
            self.board[ty][tx].pawn = self.board[fy][fx].pawn
            self.board[fy][fx].pawn = None
            return True
        return False

    # ------------------------------------------------------------------
    # Bounds / vacancy checks
    # ------------------------------------------------------------------
    def is_avaliable(self, position: Position) -> bool:
        return abs(position.x) <= self.half_x and abs(position.y) <= self.half_y

    def is_cell_empty(self, position: Position) -> bool:
        if abs(position.x) > self.half_x or abs(position.y) > self.half_y:
            return False
        bx, by = self.to_board_xy(position)
        return self.board[by][bx].pawn is None

    # ------------------------------------------------------------------
    # Random empty position
    # ------------------------------------------------------------------
    def random_position(self) -> Position | None:
        from random import randint

        for _ in range(100):
            bx = randint(0, self.size_x - 1)
            by = randint(0, self.size_y - 1)
            rot = randint(0, 360)
            if self.board[by][bx].pawn is None:
                return Position(bx - self.half_x, self.half_y - by, rot)
        return None

    # ------------------------------------------------------------------
    # Elapsed time helper
    # ------------------------------------------------------------------
    @property
    def elapsed(self) -> str:
        """Return simulation running time as 'HH:MM:SS'."""
        total = int(time() - self.start_time)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def display(self) -> None:
        from creatures import Agent

        clear()
        agents = self.get_agents()
        for var in sorted(order.keys(), key=get_field_priority):
            if var in ("name", "color"):
                continue
            length = 100
            if var in ("energy", "health", "energy_to_breeding", "species"):
                length = 6
                # printable = sorted(set(getattr(a, var) for a in agents))
                # step = max(1, len(printable) // 10)
                # console.print(f'{var:31}\t{len(printable)}\t{printable[::step]}')
                # continue
            try:
                counter = Counter(getattr(a, var) for a in agents if hasattr(a, var))
                console.print(
                    # f'{f'{len(set(counter))}':7}{f'{var}':30}',
                    f"{f'{var}':30}",
                    *[
                        f"{k}: {v}"
                        for k, v in sorted(
                            counter.items(), key=lambda x: (-x[1], x[0])
                        )[:length]
                    ],
                    sep="\t",
                )
            except TypeError:
                pass

        food_count = len(self.creatures) - len(agents)
        console.print(f'{"Current step":32}{self.tick}')
        console.print(f'{"Frame time":32}{self.frame_time:.4f}s')
        console.print(f'{"Elapsed time":32}{self.elapsed}')
        console.print(f'{"Births / Deaths":32}{self.births} / {self.deaths}')
        console.print(f'{"Species known":32}{len(self._species_registry)}')
        console.print(f'{"Agents on pool":32}{len(agents)}')
        console.print(f'{"Food on pool":32}{food_count}')
        console.print(f'{"Creatures on pool":32}{len(self.creatures)}')

        if not self.debug:
            full_board_text = Text()
            for row in self.board:
                for cell in row:
                    if cell.pawn is None:
                        full_board_text.append(" ·", style="#333333")
                    else:
                        full_board_text.append(
                            str(cell.pawn), style=f"#{cell.pawn.color}"
                        )
                full_board_text.append("\n")
            console.print(full_board_text)


    def command_input(self) -> str:
        print()
        lines = []
        while True:
            line = input(">>> ")
            if not line:
                break
            lines.append(line)

        return "\n".join(lines)


    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------
    def food_generator(self) -> None:
        if len(self.get_food()) > 5000:
            return
        from creatures import Food

        self.tick += 1
        if self.tick % self.ticks_to_generation == 0:
            for _ in range(self.food_per_generation):
                pos = self.random_position()
                if pos is None:
                    continue
                Food.create_random(position=pos)

    def step(self,agents:list[Agent]|None=None,cur_step:int|None=None) -> None:
        try:
            if agents is None:
                agents = self.get_agents()
            if cur_step is None:
                cur_step = 0
            start_time = time()
            if not self.debug:
                sleep(self.delta_time)
                self.display()
            self.food_generator()
            if not self.creatures:
                return

            # Reset per-tick breeding gate
            if self.sucess:
                for agent in agents:
                    agent._bred_this_tick = False

            max_speed = max((a.speed for a in agents), default=1)

            for cur_step in range(cur_step, max_speed):
                for creature in list(self.creatures):
                    if not self.contains(creature):
                        continue
                    from creatures import Agent as _Agent

                    if isinstance(creature, _Agent) and creature.speed > cur_step:
                        creature.step()
            self.frame_time = time() - start_time
            self.sucess = True
            return {'agents': None, 'cur_step': 0}
        except KeyboardInterrupt:
            self.sucess = False
            exec(self.command_input())
            return {'agents':agents, 'cur_step': cur_step}


    def run(self, s: float = 0) -> None:
        if s:
            self.display()
            sleep(s)
        state = {'agents': None, 'cur_step': 0}
        while self.get_agents():
            state = self.step(**state)
