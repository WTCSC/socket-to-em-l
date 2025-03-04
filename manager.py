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
    print(data)
    global game
    parsed: dict[str, list[dict[str, str | dict]]] = json.loads(data)
    game_objects = {}
    for list_obj in parsed:
        game_objects[list_obj] = []
        for game_object in parsed.get(list_obj):
            obj_class = str_to_obj[game_object["class"]]
            attributes = {k: v for k, v in game_object["data"].items() if v != "z"}
            game_objects[list_obj].append(data_to_obj(obj_class, attributes))
    game = game_objects

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
    for obj_list in game:
        data[obj_list] = []
        for game_object in game.get(obj_list):
            data[obj_list].append(obj_to_data(game_object))
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

def main():

    print(parse_data(game_to_data()))

    draw.main(game, "p1")

if __name__ == "__main__":
    main()