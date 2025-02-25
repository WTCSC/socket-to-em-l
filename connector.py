import socket
from threading import Thread

# Start a server instance
def host_game(num_players):
    return Server(socket.socket(socket.AF_INET, socket.SOCK_STREAM), num_players)

# Start a client and connect it to the server
def connect(ip):
    return Client(socket.socket(socket.AF_INET, socket.SOCK_STREAM), ip)

class Client:
    def __init__(self, sock: socket.socket, ip):
        # Connect to the server
        self.socket = sock
        self.socket.connect((ip, 1212))
        print("Connected to server")

        # Start a thread to listen to the server
        self.receive_thread = Thread(target=self.receive)
        self.receive_thread.start()

        self.is_processing = True
    
    # Send data to the server
    def send(self, data: str):
        self.socket.send(data.encode())
    
    # Waits for data from the server
    def receive(self):
        try:
            while True:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                self.parse_data(data)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            print("Disconnecting...")
            self.close()
    
    def parse_data(self, data: str):
        print(data)

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.is_processing = False
        print("Disconnected from server")

class Server:
    def __init__(self, sock: socket.socket, player_count):
        # Open a connection and listen for a number of players
        self.socket = sock
        self.socket.bind(("0.0.0.0", 1212))
        self.socket.listen(player_count)
        hostname = socket.gethostname()
        print(f"Your IP address is {socket.gethostbyname(hostname)}\n")
        print(f"Players connected 1/{player_count}")

        # Wait for connection from each player
        self.clients : list[socket.socket] = []
        for i in range(1, player_count):
            conn, _ = self.socket.accept()
            self.clients.append(conn)

            self.clients[-1].send(f"You are player {i + 1}\n".encode())

            print(f"\nPlayer {i + 1} connected")
            self.brodcast(f"Players connected {i + 1}/{player_count}")

        print("All players connected")
        
        # Start a thread for each player to listen to them
        self.threads: list[Thread] = []
        for client in self.clients:
            self.threads.append(Thread(target=self.recieve, args=[client]))
            self.threads[-1].start()
        
        self.is_processing = True

    def recieve(self, sock: socket.socket):
        try:
            while True:
                data = sock.recv(1024).decode()
                if not data:
                    break
                self.brodcast(data)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.disconnect(sock)

    # Send data to each client
    def brodcast(self, data):
        self.parse_data(data)
        for client in self.clients:
            client.send(data.encode())

    def parse_data(self, data):
        print(data)
    
    # Close all the clients, then close the server
    def close(self):
        for client in self.clients:
            client.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.is_processing = False
    
    def disconnect(self, client: socket.socket):
        client.close()
        self.clients.remove(client)
        if len(self.clients) == 0:
            self.close()