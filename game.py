import connector
import graphics
import manager

def prompt(text = "", options = [], error = ""):
    print(text)
    user_input = input()
    if options and (user_input not in options):
        print(error if error else "\nPlease choose a valid option\n")
        user_input = prompt(text, options)
    return user_input


print("Welcome to ____\n")
is_hosting = prompt("Are you hosting or joining a game?\n1. Hosting\n2. Joining", ["1", "2"]) == "1"

if is_hosting:
    player_count = int(prompt("How many people are playing? Choose a number between 2 and 4", ["2", "3", "4"], "\nPlease chose a player count between 2 and 4\n"))
    player = connector.host_game(player_count)
else:
    print("What IP address do you want to connect to?")
    ip = input()
    player = connector.connect(ip)