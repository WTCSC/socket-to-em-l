import socket
import manager
from threading import Thread

# Start a server instance
def host_game():
    return Server()

# Start a client and connect it to the server
def connect(ip):
    return Client(ip)

class Client:
    def __init__(self, ip):
        # Initialize the connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((ip, 1212))
        self.client = self.socket
        print("Connected to server")

        self.recieving_thread = Thread(target=self.receive)
        self.recieving_thread.start()
    
    def receive(self):
        try:
            while True:
                data = self.client.recv(10000).decode()
                if data == "close" or not data:
                    break
                manager.parse_data(data)
        finally:
            self.close()
    
    def send(self, data: str):
        if self.client.fileno() != -1:
            self.client.send(data.encode())
    
    def close(self):
        if self.socket.fileno() != -1:
            self.socket.close()
            # manager.end_game()

class Server(Client):
    def __init__(self):
        # Initialize the server's socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("0.0.0.0", 1212))
        self.socket.listen(1)

        # Show some information before connecting the clients
        hostname = socket.gethostname()
        print(f"Your IP address is {socket.gethostbyname_ex(hostname)[-1][-1]}\n")

        # Connect each player and start a thread to listen to each of them
        self.client, _ = self.socket.accept()
        self.thread = Thread(target=self.receive)
        self.thread.start()

        print("All players connected")
        self.send("All players connected")