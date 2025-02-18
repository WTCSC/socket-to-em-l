import connector
import graphics
import manager

def prompt(text = "", options = []):
    print(text)
    user_input = input()
    if options and (user_input not in options):
        print("\nPlease choose a valid option\n")
        user_input = prompt(text, options)
    return user_input


print("Welcome to ____\n")
is_hosting = prompt("Are you hosting or joining a game?\n1. Hosting\n2. Joining", ["1", "2"]) == "1"

if is_hosting:
    player = connector.host_game()