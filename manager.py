import draw
import json
import inspect


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

game = draw.initialize("player_1")

GLOBAL_SCALE = (.25, .25)
# Load game objects
starship_grey = draw.Troop('imgs/black_ship.png', (600, 450), 400, 2, 200)
starship_grey.scale(GLOBAL_SCALE)
game.game_objects["player_1"]["troops"].append(starship_grey)

command_center = draw.Building('imgs/command_center.png', (100, 100), 3000)
command_center.scale(GLOBAL_SCALE)
game.game_objects["player_1"]["buildings"].append(command_center)

barracks = draw.Building('imgs/barracks.png', (400, 150), 1250)
barracks.scale(GLOBAL_SCALE)
game.game_objects["player_1"]["buildings"].append(barracks)

starport = draw.Building('imgs/starport.png', (150, 450), 750)
starport.scale(GLOBAL_SCALE)
game.game_objects["player_1"]["buildings"].append(starport)

depot = draw.Building('imgs/vehicle_depot.png', (375, 350), 1500)
depot.scale(GLOBAL_SCALE)
game.game_objects["player_1"]["buildings"].append(depot)

red_troop = draw.Troop('imgs/red_soildger.png', (1200, 700), 75, 20, 40)
red_troop.scale(GLOBAL_SCALE)
game.game_objects["player_1"]["troops"].append(red_troop)

blue_troop = draw.Troop('imgs/blue_soildger.png', (300, 200), 75, 5, 40)
blue_troop.scale(GLOBAL_SCALE)
game.game_objects["player_1"]["troops"].append(blue_troop)

# print(parse_data(game_to_data()))

clock = draw.pygame.time.Clock()

while True:
    draw.process_frame(game)
    clock.tick(60)