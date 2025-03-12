import connector
import manager
import draw
from threading import Thread
from time import sleep


# Prompts the user and validates their input based on options
def prompt(text = "", options = [], error = ""):
    print()
    print(text)
    user_input = input()
    if options and (user_input not in options):
        print(error if error else "\nPlease choose a valid option\n")
        user_input = prompt(text, options)
    return user_input

def send_game():
    # print(manager.game_to_data())
    player.send(manager.game_to_data(player_number))

print("Welcome to ____\n")

is_hosting = prompt("Are you hosting or joining a game?\n1. Hosting\n2. Joining", ["1", "2"]) == "1"

# Make the player either a host or a client
if is_hosting:
    player = connector.host_game()
else:
    print("What IP address do you want to connect to?")
    ip = input()
    player = connector.connect(ip)

player_number = "p1" if is_hosting else "p2"

try:
    draw_thread = Thread(target=draw.main, args=[manager.game, player_number])
    # draw_thread = Thread(target=manager.main)
    draw_thread.start()
    while True:
        send_game()
        sleep(1/10)
except KeyboardInterrupt:
    print("Ending game...")
finally:
    player.close()
    print("Disconnected")