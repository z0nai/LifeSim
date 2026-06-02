from random import choices, choice
from string import ascii_uppercase, ascii_lowercase

from effects import Effect
from position import Position
from os import system as os_system, name as os_name


def generate_color():
    return ''.join(choices('0123465789abcdef', k=6))


clear = lambda: os_system('cls' if os_name == 'nt' else 'clear')

agent_emoji = {'S': 'v|', 'N': '^|', 'W': '<-', 'E': '->', 'NE': '/\'', 'SE': '\\,', 'NW': '`\\', 'SW': ',/'}

food_emoji = ('()', '°°', '~~', '[]', '||', '()', '{}', '--', '..', '■■', '●●', '◎◎', '◉◉')
routes = {
    'N': Position(0, 1),  # Вверх (Y увеличивается)
    'S': Position(0, -1),  # Вниз (Y уменьшается)
    'E': Position(1, 0),  # Вправо
    'W': Position(-1, 0),  # Влево
    'NE': Position(1, 1),  # Вправо-вверх
    'NW': Position(-1, 1),  # Влево-вверх
    'SE': Position(1, -1),  # Вправо-вниз
    'SW': Position(-1, -1)  # Влево-вниз
}

multiplier = {
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
    'energy_per_step': None,
    'energy_to_breeding': None,
    'fov': 1,
    'view_range': 1,
    'speed': 1,
    'power': 1,
    'is_herbivores': 0,
    'is_predator': 0,
    'is_friendly_predator': 0,
    'immunities': 0,
}


def list_effects():
    return Effect.__subclasses__()


def default_effects():
    effects_dict = {}
    for effect_cls in list_effects():
        try:
            effects_dict[effect_cls(duration=10)] = False
        except TypeError:
            effects_dict[effect_cls()] = False
    return effects_dict


def default_immunities():
    return {effect: False for effect in list_effects()}


def generate_name(r):
    return choice(ascii_uppercase) + ''.join(choices(ascii_lowercase, k=max(1, r - 1)))


def generate_available(name, r):
    if not name:
        import main
        while True:
            name = generate_name(r)
            if name not in main.pool.names:
                return name
    return name

