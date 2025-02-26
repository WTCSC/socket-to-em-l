import connector
import manager
from threading import Thread
from time import sleep

def get_input():
    while True:
        # Get the player input and send it to the server
        turn = input()
        player.send(turn)

# Prompts the user and validates their input based on options
def prompt(text = "", options = [], error = ""):
    print()
    print(text)
    user_input = input()
    if options and (user_input not in options):
        print(error if error else "\nPlease choose a valid option\n")
        user_input = prompt(text, options)
    return user_input


print("Welcome to ____\n")

is_hosting = prompt("Are you hosting or joining a game?\n1. Hosting\n2. Joining", ["1", "2"]) == "1"

# Make the player either a host or a client
if is_hosting:
    player_count = 2 #int(prompt("How many people are playing? Choose a number between 2 and 4", ["2", "3", "4"], "\nPlease chose a player count between 2 and 4\n"))
    player = connector.host_game(player_count)
else:
    print("What IP address do you want to connect to?")
    ip = input()
    player = connector.connect(ip)

try:
    game_loop = Thread(target=get_input, daemon=True)
    game_loop.start()
    while True:
        sleep(1)
    # draw.main()
except KeyboardInterrupt:
    print("Ending game...")
except Exception as e:
    print(f"Error: {e}")
finally:
    player.close()
    print("Disconnected")