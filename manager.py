import draw
import json
import inspect
import random


class GameObjParser(json.JSONEncoder):
    def default(self, o):
        if type(o) in str_to_obj.values():
            return obj_to_data(o)
        else:
            try:
                return json.JSONEncoder().default(o)
            except TypeError:
                return "z"

def parse_data(data: str):
    parsed: dict[str, list[dict[str, str | dict]]] = json.loads(data)
    game_objects = {}
    for player in parsed:
        game_objects[player] = []
        for game_object in parsed.get(player):
            obj_class = str_to_obj[game_object["class"]]
            attributes = {k: v for k, v in game_object["data"].items() if v != "z"}
            game_objects[player].append(data_to_obj(obj_class, attributes))
    return game_objects

def data_to_obj(obj_class, data):
    for key in data:
        attribute = data[key]
        if isinstance(attribute, dict):
            if "class" in attribute.keys():
                data[key] = data_to_obj(str_to_obj[attribute["class"]], attribute["data"])
    # Get the __init__ parameter names (excluding 'self')
    init_params = inspect.signature(obj_class.__init__).parameters
    init_keys = [key for key in init_params if key != 'self']
    
    # Filter only the attributes that match __init__ parameters
    init_args = {key: data[key] for key in init_keys if key in data}

    # Create an instance using the filtered arguments
    instance = obj_class(**init_args)

    # Assign remaining attributes
    for key, value in data.items():
        # If the attribute wasn't already assigned through __init__
        if key not in init_args:
            setattr(instance, key, value)
    
    return instance
    

def game_to_data():
    data: dict[str, list]= {}
    for player in game.game_objects:
        data[player] = []
        for game_object in game.game_objects.get(player):
            data[player].append(obj_to_data(game_object))
    return json.dumps(data, skipkeys=True, cls=GameObjParser)

def obj_to_data(game_object):
    object_dict = {}
    object_dict["class"] = type(game_object).__name__
    object_dict["data"] = game_object.__dict__
    return object_dict


str_to_obj = {
    "GameObject": draw.GameObject,
    "Building": draw.Building,
    "Troop": draw.Troop,
    "Vector2": draw.Vector2
}

game: dict[str, list[draw.GameObject]] = {"p1_troops": [], "p2_troops": [], "p1_buildings": [], "p2_buildings": [], "bullets": []}

GLOBAL_SCALE = (.25, .25)

# Load game objects
starship_grey = draw.Troop('imgs/black_ship.png', (600, 450), 700, 2, random.randint(80, 100))
starship_grey.scale(GLOBAL_SCALE)
game["p1_troops"].append(starship_grey)

starship_red = draw.Troop('imgs/red_ship.png', (600, 1000), 700, 2, random.randint(80, 100))
starship_red.scale(GLOBAL_SCALE)
game["p1_troops"].append(starship_red)

command_center = draw.Building('imgs/command_center.png', (100, 100), 2000)
command_center.scale((.5, .5))
game["p1_buildings"].append(command_center)

red_troop = draw.Troop('imgs/red_soildger.png', (1200, 700), 150, 10, int(40-50))
red_troop.scale(GLOBAL_SCALE)
game["p1_troops"].append(red_troop)

blue_troop = draw.Troop('imgs/blue_soildger.png', (300, 200), 150, 10, int(40-50))
blue_troop.scale(GLOBAL_SCALE)
game["p1_troops"].append(blue_troop)

# print(parse_data(game_to_data()))

draw.main(game, "p1")