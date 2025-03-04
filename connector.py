import socket
import manager
from threading import Thread

# Start a server instance
def host_game(num_players):
    return Server(num_players)

# Start a client and connect it to the server
def connect(ip):
    return Client(ip)

class Client:
    def __init__(self, ip):
        # Initialize the connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((ip, 1212))
        print("Connected to server")

        self.recieving_thread = Thread(target=self.recieve)
        self.recieving_thread.start()
    
    def recieve(self):
        try:
            while True:
                data = self.socket.recv(1024).decode()
                if data == "close" or not data:
                    break
                manager.parse_data(data)
        finally:
            self.close()
    
    def send(self, data: str):
        if self.socket.fileno() != -1:
            self.socket.send(data.encode())
    
    def close(self):
        if self.socket.fileno() != -1:
            self.socket.close()
            # manager.end_game()

class Server:
    def __init__(self, num_players):
        # Initialize the server's socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("0.0.0.0", 1212))
        self.socket.listen(num_players - 1)

        # Show some information before connecting the clients
        hostname = socket.gethostname()
        print(f"Your IP address is {socket.gethostbyname_ex(hostname)[-1][-1]}\n")
        print(f"Players connected 1/{num_players}")

        # Connect each player and start a thread to listen to each of them
        self.clients : list[tuple[socket.socket, int]] = []
        self.threads: list[Thread] = []

        for i in range(1, num_players):
            # Accept the player connection
            conn, _ = self.socket.accept()
            self.clients.append((conn, i))

            # Start a thread to listen to the player
            receiving_thread = Thread(target=self.recieve, args=[conn])
            receiving_thread.start()
            self.threads.append(receiving_thread)

            # Tell the player which player they are
            conn.send(f"You are player {i + 1}\n".encode())

            print(f"\nPlayer {i + 1} connected")
            print(f"Players connected {i + 1}/{num_players}")
            self.broadcast(f"Players connected {i + 1}/{num_players}")

    # Listen to a client for data
    def recieve(self, client: socket.socket):
        try:
            while True:
                # Get the data and decode it
                data = client.recv(1024).decode()
                # If there is no data, the connection was closed
                if not data:
                    break
                # Parse the data and send it to all clients
                self.send(data)
        finally:
            self.socket.close()
    
    # "Send" data to the server and broadcast the data to all clients
    def send(self, data: str):
        self.broadcast(data)
    
    # Send data to all clients
    def broadcast(self, data: str):
        for client in self.clients:
            client[0].send(data.encode())
    
    # Close a single client
    def close_client(self, client: socket.socket):
        # Check if the connection is open
        if client.fileno() != -1:
            # Get which client to close
            client_index = [i[0] for i in self.clients].index(client)

            # Close the client and remove it from the list
            self.clients.pop(client_index)[0].close()
            print(f"Player {client_index + 1} has left the game")
            if len(self.clients) == 0:
                self.close_all()

    def close(self):
        self.broadcast("close")
        self.socket.close()