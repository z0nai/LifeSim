from random import choices, choice
from string import ascii_uppercase, ascii_lowercase
from sys import stdout

from position import Position


def generate_color() -> str:
    return ''.join(choices('0123456789abcdef', k=6))


clear = lambda: stdout.write('\033[2J\033[H\033[3J')

agent_emoji: dict[str, str] = {
    'S': 'v|', 'N': '^|', 'W': '<-', 'E': '->',
    'NE': '/\'', 'SE': '\\,', 'NW': '`\\', 'SW': ',/'
}

food_emoji: tuple[str, ...] = (
    '()', '°°', '~~', '[]', '||', '()', '{}', '--',
    '..', '■■', '●●', '◎◎', '◉◉'
)

routes: dict[str, Position] = {
    'N':  Position(0,  1),
    'S':  Position(0, -1),
    'E':  Position(1,  0),
    'W':  Position(-1, 0),
    'NE': Position(1,  1),
    'NW': Position(-1, 1),
    'SE': Position(1, -1),
    'SW': Position(-1,-1),
}

# Fields where None means "skip mutation entirely"
multiplier: dict[str, int | None] = {
    'name': None,
    'position': None,
    'color': None,
    'species': None,
    'change_chance': 0,
    'base_health': 1,
    'base_energy': 1,
    'health': None,
    'energy': None,
    'base_energy_to_breeding': 1,
    'energy_per_step': 1,
    'energy_to_breeding': None,
    'fov': 1,
    'view_range': 1,
    'speed': 1,
    'power': 1,
    'is_herbivores': 0,
    'is_predator': 0,
    'is_friendly_predator': 0,
    'generation': None,
}



def generate_name(r: int) -> str:
    return choice(ascii_uppercase) + ''.join(choices(ascii_lowercase, k=max(1, r - 1)))


def generate_available(name: str, r: int) -> str:
    if not name:
        import main
        while True:
            name = generate_name(r)
            if name not in main.pool.names:
                return name
    return name


order: dict[str, int] = {
    'name': 1, 'generation': 2, 'color': 3, 'species': 4,
    'health': 10, 'energy': 11, 'energy_to_breeding': 12,
    'base_health': 20, 'base_energy': 21, 'base_energy_to_breeding': 22, 'energy_per_step': 23,
    'speed': 30, 'power': 31, 'fov': 32, 'view_range': 33,
    'is_herbivores': 40, 'is_predator': 41, 'is_friendly_predator': 42,
    'change_chance': 50,
}


def get_field_priority(tag: str) -> int:
    return order.get(tag, 999)
