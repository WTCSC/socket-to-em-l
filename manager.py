import draw
import json
import inspect

# A class to convert all the game objects to json
class GameObjParser(json.JSONEncoder):
    # Override the default function, which is responsible for converting objects to a JSON-compatible format
    def default(self, o):
        # If the object's class is one that we know how to parse, parse it
        if type(o) in str_to_obj.values():
            return obj_to_data(o)
        # Otherwise try to convert it in the recular default function
        else:
            try:
                return json.JSONEncoder().default(o)
            # If it still hasn't been converted, mark it and it will be dealt with later
            except TypeError:
                return "z"

# Receives a JSON string and turns it into a game sate
def parse_data(data: str):
    try:
        # Load the JSON
        parsed: dict[str, list[dict[str, dict]]] = json.loads(data)
        # For every category (troops, buidings, bullets) in the dictionary
        for list_obj in parsed:
            # Clear the game's memory of the category so it can be reconstructed
            game[list_obj].clear()
            # For each individual object
            for game_object in parsed.get(list_obj):
                # Get the class from the data
                obj_class = str_to_obj[game_object["class"]]
                # Get the recieved data about the object
                attributes = {k: v for k, v in game_object["data"].items() if v != "z"}
                # Turn the data back into an object and add it back to the object list
                game[list_obj].append(data_to_obj(obj_class, attributes))
    except json.decoder.JSONDecodeError:
        return

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
    

def game_to_data(player: str):
    data: dict[str, list]= {}
    for obj_list in game:
        if player not in obj_list:
            continue
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

game: dict[str, list[draw.GameObject]] = {"p1_troops": [], "p2_troops": [], "p1_buildings": [], "p2_buildings": [], "p1_bullets": [], "p2_bullets": []}

GLOBAL_SCALE = (.25, .25)

def main():
    draw.main(game, "p1")

if __name__ == "__main__":
    main()