import socket


def host_game(num_players):
    return Server(socket.socket(socket.AF_INET, socket.SOCK_STREAM), num_players)


class Client:
    pass

class Server:
    def __init__(self, sock, player_count):
        self.socket = sock
        self.socket.bind(("0.0.0.0", 1212))
        self.socket.listen(player_count)