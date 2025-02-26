import draw
import json
import inspect

def parse_data(data: str):
    parsed: dict[str, list[dict[str]]] = json.loads(data)
    game_obj = draw.Game()
    for player in parsed:
        game_obj.game_objects[player] = []
        for game_object in parsed.get(player):
            obj_class = str_to_obj[game_object["class"]]
            attributes = game_object["data"]

            # Get the constructor's parameter names (excluding 'self')
            init_params = inspect.signature(obj_class.__init__).parameters
            init_keys = [key for key in init_params if key != 'self']
            
            # Filter only the attributes that match the constructor parameters
            init_args = {key: attributes[key] for key in init_keys if key in attributes}

            # Create an instance using the filtered arguments
            instance = obj_class(**init_args)

            # Assign remaining attributes dynamically
            for key, value in attributes.items():
                if key not in init_args:  # Only assign attributes that weren't used in __init__
                    setattr(instance, key, value)
            
            game_obj.game_objects.append(instance)
    return game_obj

            

def game_to_data():
    data: dict[str, list]= {}
    for player in game.game_objects:
        data[player] = []
        for game_object in game.game_objects.get(player):
            object_dict = {}
            object_dict["class"] = type(game_object).__name__
            object_dict["data"] = "Do later"


str_to_obj = {
    "GameObject": draw.GameObject,
    "Building": draw.Building,
    "Troop": draw.Troop,
    "Vector2": draw.Vector2
}

game = draw.Game()
game.game_objects["player_1"] = []

GLOBAL_SCALE = (.25, .25)
# Load game objects
starship_grey = draw.Troop('imgs/black_ship.png', (600, 450), 400, 2)
starship_grey.scale(GLOBAL_SCALE)
game.game_objects["player_1"].append(starship_grey)

command_center = draw.Building('imgs/command_center.png', (100, 100), 3000)
command_center.scale(GLOBAL_SCALE)
game.game_objects["player_1"].append(command_center)

barracks = draw.Building('imgs/barracks.png', (400, 150), 1250)
barracks.scale(GLOBAL_SCALE)
game.game_objects["player_1"].append(barracks)

starport = draw.Building('imgs/starport.png', (150, 450), 750)
starport.scale(GLOBAL_SCALE)
game.game_objects["player_1"].append(starport)

depot = draw.Building('imgs/vehicle_deop.png', (375, 350), 1500)
depot.scale(GLOBAL_SCALE)
game.game_objects["player_1"].append(depot)

red_troop = draw.Troop('imgs/red_soildger.png', (1200, 700), 75, 20)
red_troop.scale(GLOBAL_SCALE)
game.game_objects["player_1"].append(red_troop)

blue_troop = draw.Troop('imgs/blue_soildger.png', (300, 200), 75, 5)
blue_troop.scale(GLOBAL_SCALE)
game.game_objects["player_1"].append(blue_troop)

game_to_data()