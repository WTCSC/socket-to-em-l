import socket

def host_game(num_players):
    return Server(socket.socket(socket.AF_INET, socket.SOCK_STREAM), num_players)

def connect(ip):
    return Client(socket.socket(socket.AF_INET, socket.SOCK_STREAM), ip)

class Client:
    def __init__(self, sock, ip):
        self.socket = sock
        self.socket.connect((ip, 1212))
        print("Connected to server")

class Server:
    def __init__(self, sock, player_count):
        self.socket = sock
        self.socket.bind(("0.0.0.0", 1212))
        self.socket.listen(player_count)
        print(f"Players connected 1/{player_count}")
        for i in range(1, player_count):
            conn, addr = self.socket.accept()
            print(f"\nPlayer {i + 1} connected")
            print(f"Players connected {i + 1}/{player_count}")
        print("All players connected")