import pygame
import sys
import random
import math
import socket
import threading
import pickle  # used for serializing network events
from pygame.locals import *

# =======================
#       CONSTANTS
# =======================
WORLD_WIDTH, WORLD_HEIGHT = 2000, 2000
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
CAMERA_BORDER = 20       # When mouse is near the edge, pan camera
CAMERA_SPEED = 300       # Pixels per second

# Costs (all in minerals)
COST_BARRACKS      = 150       
COST_SCV           = 50             
COST_MARINE        = 50          
COST_TANK          = 150           
COST_WRAITH        = 200         
COST_TANK_FACTORY  = 300   
COST_WRAITH_FACTORY= 350 
COST_TURRET        = 200         
COST_BUNKER        = 250         

# Mining and production settings
MINING_CYCLE   = 4          # Seconds per mining cycle
MINING_YIELD   = 8          # Minerals per cycle
MINERAL_AMOUNT = 1500     
PRODUCTION_TIME = 8.0     # Seconds per unit spawn
MAX_QUEUE       = 5             

# Combat settings (not fully implemented here)
MARINE_SHOOT_COOLDOWN = 0.5   
PROJECTILE_SPEED      = 300        
PROJECTILE_DAMAGE     = 15        
SCV_ATTACK_DAMAGE     = 5         

# Engagement & separation settings
ENGAGEMENT_RADIUS  = 100       
SEPARATION_DISTANCE = 15      
SEPARATION_FORCE    = 20         

# Turret and bunker settings
TURRET_SHOOT_INTERVAL    = 1.0   
TURRET_PROJECTILE_SPEED  = 400 
TURRET_PROJECTILE_DAMAGE = 10  
TURRET_RANGE             = 150             
BUNKER_SHOOT_INTERVAL    = 3.0   
BUNKER_PROJECTILE_SPEED  = 250 
BUNKER_PROJECTILE_DAMAGE = 25 
BUNKER_RANGE             = 100             
BUNKER_MAX_HEALTH        = 1200       

# Upgrade system
UPGRADE_COST = 100            
player_damage_multiplier = 1.0  

# Host state snapshot interval in seconds
SNAPSHOT_INTERVAL = 10.0

# =======================
#     UNIQUE ID SYSTEM
# =======================
global_uid = 1
def get_next_id():
    global global_uid
    uid = global_uid
    global_uid += 1
    return uid

# =======================
#    NETWORKING SETUP
# =======================
network_mode = None   # "host" or "client"
network_socket = None # Host: accepted connection; Client: connection socket.
incoming_events = []  # Will store network events

net_lock = threading.Lock()

def network_send(event):
    """Send a network event, serialized with pickle."""
    global network_socket
    try:
        data = pickle.dumps(event)
        data = len(data).to_bytes(4, byteorder='big') + data
        network_socket.sendall(data)
    except Exception as e:
        print("Network send error:", e)

def recvall(conn, n):
    """Helper function: receive n bytes from the socket or return None."""
    data = b''
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def network_receive_thread(conn):
    """Thread to constantly receive network events."""
    global incoming_events
    while True:
        try:
            raw_len = recvall(conn, 4)
            if not raw_len:
                print("Network connection closed.")
                break
            msg_len = int.from_bytes(raw_len, byteorder='big')
            data = recvall(conn, msg_len)
            if not data:
                break
            event = pickle.loads(data)
            with net_lock:
                incoming_events.append(event)
        except Exception as e:
            print("Network receive error:", e)
            break

def init_network():
    """Initialize network connection automatically.
       - In host mode, wait for a connection.
       - In client mode, automatically connect to 10.103.1.51.
    """
    global network_mode, network_socket
    # Here we use a command line argument or default; for simplicity,
    # you can edit the following variable manually:
    MODE = input("Enter network mode (host/client): ").strip().lower()
    if MODE == "host":
        network_mode = "host"
        host_ip = ''  # Listen on all interfaces
        port = 9999
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((host_ip, port))
            server.listen(1)
            print("Hosting game... waiting for connection on port", port)
            network_socket, addr = server.accept()
            print("Client connected from:", addr)
        except Exception as e:
            print("Error initializing host:", e)
            sys.exit()
    else:
        network_mode = "client"
        # Automatically set host address to 10.103.1.51
        host_address = "10.103.1.51"
        port = 9999
        network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        network_socket.settimeout(10)  # timeout set to 10 seconds
        attempt = 0
        connected = False
        while attempt < 3 and not connected:
            try:
                print(f"Attempting to connect to {host_address}:{port} (Attempt {attempt+1})...")
                network_socket.connect((host_address, port))
                connected = True
            except Exception as e:
                print("Connection error:", e)
                attempt += 1
                if attempt < 3:
                    print("Retrying...")
        if not connected:
            print("Failed to connect after several attempts. Please check your network settings.")
            sys.exit()
        print("Connected to host at", host_address)
    # Start the receiver thread
    threading.Thread(target=network_receive_thread, args=(network_socket,), daemon=True).start()

# =======================
#    GAME CLASSES
# =======================
class ResourceDrop:
    def __init__(self, x, y, amount=100):
        self.x = x
        self.y = y
        self.amount = amount

class Building:
    def __init__(self, b_type, x, y, owner, complete=False):
        self.uid = get_next_id()
        self.type = b_type
        self.x = x
        self.y = y
        self.owner = owner  # "player1" or "player2"
        if b_type == "Command Center":
            self.health = 2500
            self.max_health = 2500
        elif b_type == "Bunker":
            self.health = BUNKER_MAX_HEALTH
            self.max_health = BUNKER_MAX_HEALTH
        elif b_type == "Turret":
            self.health = 800
            self.max_health = 800
        else:
            self.health = 1000
            self.max_health = 1000
        self.progress = 100 if complete else 0
        self.complete = complete
        self.builder = None  # The SCV constructing the building
        if b_type in ["Command Center", "Barracks", "Tank Factory", "Wraith Factory", "Bunker"]:
            self.production_queue = []
            self.production_timer = 0.0
        else:
            self.production_queue = None
            self.production_timer = None
        if b_type == "Turret":
            self.turret_shoot_timer = 0.0
        if b_type == "Bunker":
            self.bunker_shoot_timer = 0.0

    def update(self, dt):
        if not self.complete:
            if self.builder is not None:
                d = math.hypot(self.builder.x - self.x, self.builder.y - self.y)
                if d < 5:
                    self.progress += 20 * dt
            else:
                self.progress += 20 * dt
            if self.progress >= 100:
                self.progress = 100
                self.complete = True
                print(f"{self.owner.capitalize()}'s {self.type} construction complete!")
                if self.builder:
                    self.builder.state = "idle"
                    self.builder.target_building = None

class Unit:
    def __init__(self, u_type, x, y, owner):
        self.uid = get_next_id()
        self.type = u_type
        self.x = x
        self.y = y
        self.owner = owner  # "player1" or "player2"
        self.health = 50
        self.move_target = None   # (x, y)
        if u_type == "SCV":
            self.state = "idle"   # states: idle, to_mineral, mining, to_depot, building, repairing, moving, etc.
            self.mine_timer = 0
            self.target_mineral = None
            self.deposit_target = None
            self.target_building = None
            self.attack_target = None
            self.attack_timer = 0
            self.cargo = 0
        elif u_type == "Marine":
            self.state = "idle"
            self.target_enemy = None
            self.shoot_timer = 0
        elif u_type in ["Tank", "Wraith"]:
            self.state = "idle"
            self.target_enemy = None
            self.shoot_timer = 0

class Mineral:
    def __init__(self, x, y, amount=MINERAL_AMOUNT):
        self.x = x
        self.y = y
        self.amount = amount
        self.mining_scvs = []

class Projectile:
    def __init__(self, x, y, target, speed, damage, owner):
        self.x = x
        self.y = y
        self.target = target  # Should have x, y, and health attributes
        self.speed = speed
        self.damage = damage
        self.owner = owner

    def update(self, dt):
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return True
        move_dist = self.speed * dt
        if move_dist >= dist:
            self.x, self.y = self.target.x, self.target.y
        else:
            self.x += (dx / dist) * move_dist
            self.y += (dy / dist) * move_dist
        if math.hypot(self.x - self.target.x, self.y - self.target.y) < 10:
            return True
        return False

def generate_minerals_cshape(center):
    cx, cy = center
    mines = []
    start_angle = math.radians(30)
    end_angle = math.radians(270)
    total_angle = end_angle - start_angle
    count = 10
    for i in range(count):
        angle = start_angle + (total_angle * i / (count - 1))
        x = cx + 200 * math.cos(angle)
        y = cy + 200 * math.sin(angle)
        mines.append(Mineral(x, y))
    return mines

# =======================
#       GAME CLASS
# =======================
class Game:
    def __init__(self):
        self.buildings = []
        self.units = []
        self.projectiles = []
        # Resources for both players:
        self.resources = {"player1": 50, "player2": 50}
        self.game_over = False
        self.winner = None
        self.player1_minerals = []
        self.player2_minerals = []
        self.resource_drops = []  # Extra mineral drops
        self.elapsed_time = 0

    def count_units(self, owner, unit_type):
        return sum(1 for u in self.units if u.owner == owner and u.type == unit_type)

    def add_building(self, b_type, x, y, owner, complete=False):
        b = Building(b_type, x, y, owner, complete)
        self.buildings.append(b)
        return b

    def add_unit(self, u_type, x, y, owner):
        u = Unit(u_type, x, y, owner)
        self.units.append(u)
        return u

    def add_production_order(self, building):
        if building.type == "Command Center":
            unit_type = "SCV"
            cost = COST_SCV
            if self.count_units(building.owner, "SCV") >= 18:
                print(f"{building.owner.capitalize()} already has 18 SCVs; cannot produce more.")
                return False
        elif building.type == "Barracks":
            unit_type = "Marine"
            cost = COST_MARINE
        elif building.type == "Tank Factory":
            unit_type = "Tank"
            cost = COST_TANK
        elif building.type == "Wraith Factory":
            unit_type = "Wraith"
            cost = COST_WRAITH
        else:
            return False
        if len(building.production_queue) < MAX_QUEUE:
            if self.resources[building.owner] < cost:
                print("Not enough resources for production!")
                return False
            self.resources[building.owner] -= cost
            building.production_queue.append(unit_type)
            print(f"Queued {unit_type} at {building.type} for {building.owner}.")
            return True
        else:
            print("Production queue is full!")
        return False

    def process_production(self, building, dt):
        if building.production_queue and building.complete:
            building.production_timer += dt
            if building.production_timer >= PRODUCTION_TIME:
                order = building.production_queue.pop(0)
                offset_x = random.uniform(-20, 20)
                offset_y = random.uniform(-20, 20)
                self.add_unit(order, building.x + offset_x, building.y + offset_y, building.owner)
                print(f"{building.owner.capitalize()} {order} spawned from {building.type}.")
                building.production_timer = 0

    def move_towards(self, unit, target_x, target_y, dt):
        speed = 100
        dx = target_x - unit.x
        dy = target_y - unit.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        move_dist = speed * dt
        if move_dist >= dist:
            unit.x, unit.y = target_x, target_y
        else:
            unit.x += (dx / dist) * move_dist
            unit.y += (dy / dist) * move_dist

    def update(self, dt):
        self.elapsed_time += dt
        for b in self.buildings:
            b.update(dt)
            if b.production_queue is not None:
                self.process_production(b, dt)
        for p in self.projectiles[:]:
            if p.update(dt):
                p.target.health -= p.damage
                self.projectiles.remove(p)
        if random.random() < dt / 30:
            drop = ResourceDrop(random.randint(0, WORLD_WIDTH), random.randint(0, WORLD_HEIGHT), amount=100)
            self.resource_drops.append(drop)
        for drop in self.resource_drops[:]:
            for u in self.units:
                if u.type == "SCV" and u.owner in ["player1", "player2"]:
                    if math.hypot(u.x - drop.x, u.y - drop.y) < 10:
                        self.resources[u.owner] += drop.amount
                        self.resource_drops.remove(drop)
                        break
        for u in self.units:
            if u.type == "SCV":
                if u.state == "idle" and u.target_mineral is None:
                    minerals = self.player1_minerals if u.owner == "player1" else self.player2_minerals
                    available = [m for m in minerals if m.amount > 0]
                    if available:
                        u.target_mineral = random.choice(available)
                        u.state = "to_mineral"
                if u.state == "moving" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if math.hypot(u.x - u.move_target[0], u.y - u.move_target[1]) < 5:
                        u.state = "idle"
                        u.move_target = None
                if u.state == "to_mineral" and u.target_mineral:
                    self.move_towards(u, u.target_mineral.x, u.target_mineral.y, dt)
                    if math.hypot(u.x - u.target_mineral.x, u.y - u.target_mineral.y) < 5:
                        u.state = "mining"
                        u.mine_timer = 0
                elif u.state == "mining":
                    u.mine_timer += dt
                    if u.mine_timer >= MINING_CYCLE:
                        if u.target_mineral and u.target_mineral.amount > 0:
                            u.target_mineral.amount -= MINING_YIELD
                            u.cargo = MINING_YIELD
                        u.mine_timer = 0
                        u.state = "to_depot"
                elif u.state == "to_depot" and u.deposit_target:
                    self.move_towards(u, u.deposit_target.x, u.deposit_target.y, dt)
                    if math.hypot(u.x - u.deposit_target.x, u.y - u.deposit_target.y) < 5:
                        self.resources[u.owner] += u.cargo
                        u.cargo = 0
                        if u.target_mineral and u.target_mineral.amount > 0:
                            u.state = "to_mineral"
                        else:
                            u.state = "idle"
        self.units = [u for u in self.units if u.health > 0]
        self.buildings = [b for b in self.buildings if b.health > 0]

    def get_building(self, b_type, owner):
        for b in self.buildings:
            if b.type == b_type and b.owner == owner and b.complete:
                return b
        return None

def get_game_snapshot(game):
    """Create a minimal snapshot of game state for resynchronization."""
    snapshot = {
        "buildings": [{"uid": b.uid, "type": b.type, "x": b.x, "y": b.y, "owner": b.owner,
                        "health": b.health, "complete": b.complete, "progress": b.progress} for b in game.buildings],
        "units": [{"uid": u.uid, "type": u.type, "x": u.x, "y": u.y, "owner": u.owner,
                   "health": u.health, "state": u.state} for u in game.units],
        "resources": game.resources
    }
    return snapshot

def apply_game_snapshot(game, snapshot):
    """Update local game state with a snapshot (here we simply update resources)."""
    game.resources = snapshot.get("resources", game.resources)
    print("State snapshot applied.")

# =======================
#   MAIN SETUP (No Starting Screen)
# =======================
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("RTS Multiplayer")
clock = pygame.time.Clock()

# Automatically initialize networking without a starting screen.
init_network()

cam_offset = [0, 0]
waiting_for_build_key = False
build_mode = None   # Options: "Barracks", "Tank Factory", "Wraith Factory", "Turret", "Bunker"
builder_unit = None

# Create game instance.
game = Game()
# Set up Command Centers and mineral fields for both players.
p1_cc = game.add_building("Command Center", 300, 300, "player1", complete=True)
p2_cc = game.add_building("Command Center", 1700, 1700, "player2", complete=True)
game.player1_minerals = generate_minerals_cshape((p1_cc.x, p1_cc.y))
game.player2_minerals = generate_minerals_cshape((p2_cc.x, p2_cc.y))
# Add starting SCVs.
for i in range(4):
    scv = game.add_unit("SCV", p1_cc.x + 20 + i * 15, p1_cc.y + 20, "player1")
    scv.state = "idle"
    scv.deposit_target = p1_cc
for i in range(4):
    scv = game.add_unit("SCV", p2_cc.x + 20 + i * 15, p2_cc.y + 20, "player2")
    scv.state = "idle"
    scv.deposit_target = p2_cc

selecting = False
selection_start = (0, 0)
selection_rect = pygame.Rect(0, 0, 0, 0)
selected_units = []
attack_command_active = False

snapshot_timer = 0.0  # For host to send periodic snapshots

# =======================
#       MAIN LOOP
# =======================
running = True
game_time = 0  # overall game time in seconds

while running:
    dt = clock.tick(60) / 1000.0
    game_time += dt

    # Host sends state snapshots periodically.
    if network_mode == "host":
        snapshot_timer += dt
        if snapshot_timer >= SNAPSHOT_INTERVAL:
            snap = get_game_snapshot(game)
            network_send({"action": "state_snapshot", "snapshot": snap})
            snapshot_timer = 0.0

    # Update camera based on mouse position.
    mx, my = pygame.mouse.get_pos()
    if mx < CAMERA_BORDER:
        cam_offset[0] = max(0, cam_offset[0] - CAMERA_SPEED * dt)
    if mx > SCREEN_WIDTH - CAMERA_BORDER:
        cam_offset[0] = min(WORLD_WIDTH - SCREEN_WIDTH, cam_offset[0] + CAMERA_SPEED * dt)
    if my < CAMERA_BORDER:
        cam_offset[1] = max(0, cam_offset[1] - CAMERA_SPEED * dt)
    if my > SCREEN_HEIGHT - CAMERA_BORDER:
        cam_offset[1] = min(WORLD_HEIGHT - SCREEN_HEIGHT, cam_offset[1] + CAMERA_SPEED * dt)
    
    # Process local input events.
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False
            if event.key == K_p:
                if selected_units and len(selected_units) == 1 and selected_units[0].type == "SCV":
                    waiting_for_build_key = True
                    builder_unit = selected_units[0]
                    print("Build mode activated. Press B, F, W, T, or N.")
            elif waiting_for_build_key:
                if event.key == K_b:
                    build_mode = "Barracks"
                elif event.key == K_f:
                    build_mode = "Tank Factory"
                elif event.key == K_w:
                    build_mode = "Wraith Factory"
                elif event.key == K_t:
                    build_mode = "Turret"
                elif event.key == K_n:
                    build_mode = "Bunker"
                waiting_for_build_key = False
                cost = 0
                if build_mode == "Barracks":
                    cost = COST_BARRACKS
                elif build_mode == "Tank Factory":
                    cost = COST_TANK_FACTORY
                elif build_mode == "Wraith Factory":
                    cost = COST_WRAITH_FACTORY
                elif build_mode == "Turret":
                    cost = COST_TURRET
                elif build_mode == "Bunker":
                    cost = COST_BUNKER
                owner = selected_units[0].owner
                if game.resources[owner] < cost:
                    print("Not enough minerals!")
                    build_mode = None
                else:
                    game.resources[owner] -= cost
                    print(f"{build_mode} build mode activated. A green preview will appear.")
            if event.key == K_r:
                for unit in selected_units:
                    if unit.type == "SCV":
                        unit.state = "repairing"
                        print("Repair command issued.")
                        network_send({"action": "repair", "unit_id": unit.uid})
            if event.key == K_s:
                for obj in selected_units:
                    if hasattr(obj, "production_queue") and obj.production_queue is not None:
                        if len(obj.production_queue) < MAX_QUEUE:
                            if obj.type == "Command Center":
                                unit_type = "SCV"
                                cost = COST_SCV
                                if game.resources[obj.owner] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources[obj.owner] -= cost
                            elif obj.type == "Barracks":
                                unit_type = "Marine"
                                cost = COST_MARINE
                                if game.resources[obj.owner] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources[obj.owner] -= cost
                            elif obj.type == "Tank Factory":
                                unit_type = "Tank"
                                cost = COST_TANK
                                if game.resources[obj.owner] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources[obj.owner] -= cost
                            elif obj.type == "Wraith Factory":
                                unit_type = "Wraith"
                                cost = COST_WRAITH
                                if game.resources[obj.owner] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources[obj.owner] -= cost
                            else:
                                continue
                            obj.production_queue.append(unit_type)
                            print(f"Queued {unit_type} at {obj.type}.")
                            network_send({"action": "queue_production", "building_id": obj.uid, "unit": unit_type})
            if event.key == K_x:
                owner = selected_units[0].owner if selected_units else ("player1" if network_mode=="host" else "player2")
                if game.resources[owner] >= UPGRADE_COST:
                    game.resources[owner] -= UPGRADE_COST
                    player_damage_multiplier += 0.1
                    print(f"Upgraded weapon damage. New multiplier: {player_damage_multiplier:.1f}")
                    network_send({"action": "upgrade", "owner": owner})
                else:
                    print("Not enough minerals for upgrade!")
            if event.key == K_a:
                attack_command_active = True
                print("Attack command active. Click on target location.")
        if event.type == MOUSEBUTTONDOWN:
            wx = event.pos[0] + cam_offset[0]
            wy = event.pos[1] + cam_offset[1]
            if event.button == 3:  # Right-click: Move command.
                if selected_units:
                    for u in selected_units:
                        if u.state not in ["building", "repairing"]:
                            u.state = "moving"
                            u.move_target = (wx, wy)
                    print("Units moving to", (wx, wy))
                    network_send({"action": "move", "units": [u.uid for u in selected_units], "target": (wx, wy)})
            if event.button == 1:  # Left-click.
                if build_mode is not None and builder_unit:
                    new_b = game.add_building(build_mode, wx, wy, builder_unit.owner, complete=False)
                    new_b.builder = builder_unit
                    builder_unit.state = "building"
                    builder_unit.target_building = new_b
                    print(f"{builder_unit.owner} placed {build_mode} at ({wx}, {wy}).")
                    build_mode = None
                    selected_units = []
                    network_send({"action": "build", "building_type": new_b.type, "pos": (wx, wy), "owner": builder_unit.owner})
                elif attack_command_active and selected_units:
                    for u in selected_units:
                        if u.type in ["Marine", "SCV", "Tank", "Wraith"]:
                            u.state = "attack_move"
                            u.move_target = (wx, wy)
                    attack_command_active = False
                    network_send({"action": "attack_move", "units": [u.uid for u in selected_units], "target": (wx, wy)})
                else:
                    selecting = True
                    selection_start = (wx, wy)
                    selection_rect = pygame.Rect(wx, wy, 0, 0)
        if event.type == MOUSEMOTION:
            if selecting:
                wx = event.pos[0] + cam_offset[0]
                wy = event.pos[1] + cam_offset[1]
                x0, y0 = selection_start
                selection_rect.left = min(x0, wx)
                selection_rect.top = min(y0, wy)
                selection_rect.width = abs(wx - x0)
                selection_rect.height = abs(wy - y0)
        if event.type == MOUSEBUTTONUP:
            if event.button == 1 and selecting:
                selecting = False
                if selection_rect.width < 10 and selection_rect.height < 10:
                    found = False
                    for u in game.units:
                        r = 10 if u.type == "SCV" else 8 if u.type == "Marine" else 5
                        if math.hypot(u.x - selection_rect.centerx, u.y - selection_rect.centery) < r:
                            if u.owner == ("player1" if network_mode=="host" else "player2"):
                                selected_units = [u]
                                found = True
                                print(f"Selected {u.owner}'s {u.type}.")
                                break
                    if not found:
                        selected_units = []
                else:
                    selected_units = []
                    for u in game.units:
                        if u.owner == ("player1" if network_mode=="host" else "player2"):
                            if selection_rect.collidepoint(u.x, u.y):
                                selected_units.append(u)
                                if len(selected_units) >= 15:
                                    break
                    if selected_units:
                        print(f"Selected {len(selected_units)} units.")
    
    # Process network events.
    with net_lock:
        while incoming_events:
            net_ev = incoming_events.pop(0)
            print("Received network event:", net_ev)
            if net_ev.get("action") == "state_snapshot":
                if network_mode == "client":
                    apply_game_snapshot(game, net_ev.get("snapshot", {}))
            # Additional events can be processed here.
    
    # Update game simulation.
    game.update(dt)
    
    # Draw the game world.
    screen.fill((0, 0, 0))
    for x in range(0, WORLD_WIDTH, 100):
        pygame.draw.line(screen, (20,20,20),
                         (x - cam_offset[0], 0 - cam_offset[1]),
                         (x - cam_offset[0], WORLD_HEIGHT - cam_offset[1]))
    for y in range(0, WORLD_HEIGHT, 100):
        pygame.draw.line(screen, (20,20,20),
                         (0 - cam_offset[0], y - cam_offset[1]),
                         (WORLD_WIDTH - cam_offset[0], y - cam_offset[1]))
    # Draw minerals.
    for m in game.player1_minerals:
        if m.amount > 0:
            pygame.draw.circle(screen, (255,255,0),
                               (int(m.x - cam_offset[0]), int(m.y - cam_offset[1])), 8)
    for m in game.player2_minerals:
        if m.amount > 0:
            pygame.draw.circle(screen, (200,200,0),
                               (int(m.x - cam_offset[0]), int(m.y - cam_offset[1])), 8)
    for drop in game.resource_drops:
        pygame.draw.circle(screen, (0,255,0),
                           (int(drop.x - cam_offset[0]), int(drop.y - cam_offset[1])), 6)
    # Draw buildings.
    for b in game.buildings:
        if b.type == "Command Center":
            col = (0,0,255) if b.owner=="player1" else (255,0,0)
        elif b.type == "Barracks":
            col = (255,165,0)
        elif b.type in ["Tank Factory", "Wraith Factory", "Bunker"]:
            col = (150,150,150)
        elif b.type == "Turret":
            col = (0,255,255)
        else:
            col = (128,128,128)
        if not b.complete:
            col = (100,100,100)
        rect = pygame.Rect(b.x - 15 - cam_offset[0], b.y - 15 - cam_offset[1], 30, 30)
        pygame.draw.rect(screen, col, rect)
        # Health bar.
        bar_w, bar_h = 30, 4
        ratio = b.health / b.max_health
        pygame.draw.rect(screen, (255,0,0), (rect.left, rect.top-6, bar_w, bar_h))
        pygame.draw.rect(screen, (0,255,0), (rect.left, rect.top-6, int(bar_w*ratio), bar_h))
        if not b.complete:
            font_mid = pygame.font.SysFont(None, 24)
            txt = font_mid.render(f"{int(b.progress)}%", True, (255,255,255))
            screen.blit(txt, (b.x-15-cam_offset[0], b.y-15-cam_offset[1]))
        if b.production_queue is not None:
            font_small = pygame.font.SysFont(None, 20)
            prod_text = font_small.render(f"{b.production_timer:.1f}s / {len(b.production_queue)}", True, (255,255,255))
            screen.blit(prod_text, (b.x - cam_offset[0] - 20, b.y - cam_offset[1] - 20))
        if b in selected_units:
            pygame.draw.rect(screen, (0,255,0), rect, 2)
    # Draw units.
    for u in game.units:
        pos = (int(u.x - cam_offset[0]), int(u.y - cam_offset[1]))
        if u.type == "SCV":
            pygame.draw.circle(screen, (173,216,230), pos, 10)
            if u.cargo > 0 and u.state == "to_depot":
                cargo_pos = (pos[0] + 8, pos[1] - 8)
                pygame.draw.circle(screen, (255,255,0), cargo_pos, 4)
        elif u.type == "Marine":
            pygame.draw.circle(screen, (255,255,255), pos, 8)
            pygame.draw.line(screen, (0,0,0), (pos[0]+4, pos[1]), (pos[0]+10, pos[1]), 2)
        elif u.type == "Tank":
            rect_unit = pygame.Rect(pos[0]-10, pos[1]-5, 20, 10)
            pygame.draw.ellipse(screen, (139,0,0), rect_unit)
            pygame.draw.line(screen, (0,0,0), (pos[0]+5, pos[1]), (pos[0]+15, pos[1]), 3)
        elif u.type == "Wraith":
            rect_unit = pygame.Rect(pos[0]-10, pos[1]-5, 20, 10)
            pygame.draw.ellipse(screen, (218,165,32), rect_unit)
            pygame.draw.line(screen, (0,0,0), (pos[0]+5, pos[1]), (pos[0]+15, pos[1]), 3)
        # Unit health bar.
        bw, bh = 20, 3
        ratio = u.health / 50
        pygame.draw.rect(screen, (255,0,0), (pos[0]-10, pos[1]-15, bw, bh))
        pygame.draw.rect(screen, (0,255,0), (pos[0]-10, pos[1]-15, int(bw*ratio), bh))
        if u in selected_units:
            pygame.draw.circle(screen, (0,255,0), pos, 12, 1)
    for p in game.projectiles:
        ppos = (int(p.x - cam_offset[0]), int(p.y - cam_offset[1]))
        pygame.draw.circle(screen, (255,255,0), ppos, 4)
    if selecting:
        s_rect = pygame.Rect(selection_rect.left - cam_offset[0],
                             selection_rect.top - cam_offset[1],
                             selection_rect.width, selection_rect.height)
        pygame.draw.rect(screen, (0,255,0), s_rect, 1)
    if build_mode is not None and builder_unit:
        mx2, my2 = pygame.mouse.get_pos()
        preview_rect = pygame.Rect(mx2 - 15, my2 - 15, 30, 30)
        pygame.draw.rect(screen, (0,255,0), preview_rect, 2)
        font_mid = pygame.font.SysFont(None, 32)
        letter = ""
        if build_mode == "Barracks":
            letter = "B"
        elif build_mode == "Tank Factory":
            letter = "F"
        elif build_mode == "Wraith Factory":
            letter = "W"
        elif build_mode == "Turret":
            letter = "T"
        elif build_mode == "Bunker":
            letter = "N"
        if letter:
            txt = font_mid.render(letter, True, (0,255,0))
            screen.blit(txt, (mx2 - 10, my2 - 12))
    font = pygame.font.SysFont(None, 32)
    my_owner = "player1" if network_mode=="host" else "player2"
    res_text = font.render(f"Player Minerals: {game.resources[my_owner]}", True, (255,255,255))
    screen.blit(res_text, (10, 10))
    selected_counts = {"M":0, "S":0, "T":0, "W":0}
    for u in selected_units:
        if u.type == "Marine":
            selected_counts["M"] += 1
        elif u.type == "SCV":
            selected_counts["S"] += 1
        elif u.type == "Tank":
            selected_counts["T"] += 1
        elif u.type == "Wraith":
            selected_counts["W"] += 1
    troop_text = font.render(f"(Troops: {selected_counts['M']}M {selected_counts['S']}S {selected_counts['T']}T {selected_counts['W']}W)", True, (255,255,255))
    screen.blit(troop_text, (10, 50))
    # Draw mini-map.
    mini_w, mini_h = 100, 100
    minimap = pygame.Surface((mini_w, mini_h))
    minimap.fill((50,50,50))
    scale_x = mini_w / WORLD_WIDTH
    scale_y = mini_h / WORLD_HEIGHT
    for b in game.buildings:
        bx = int(b.x * scale_x)
        by = int(b.y * scale_y)
        col = (0,255,0) if b.owner == ("player1" if network_mode=="host" else "player2") else (255,0,0)
        pygame.draw.rect(minimap, col, (bx, by, 3, 3))
    for u in game.units:
        ux = int(u.x * scale_x)
        uy = int(u.y * scale_y)
        pygame.draw.circle(minimap, (255,255,255), (ux,uy), 1)
    cam_rect = pygame.Rect(int(cam_offset[0]*scale_x), int(cam_offset[1]*scale_y), int(SCREEN_WIDTH*scale_x), int(SCREEN_HEIGHT*scale_y))
    pygame.draw.rect(minimap, (255,255,0), cam_rect, 1)
    screen.blit(minimap, (10, SCREEN_HEIGHT - mini_h - 10))
    # Display help overlay if C is held.
    if pygame.key.get_pressed()[pygame.K_c]:
        def draw_controls(surface):
            font = pygame.font.SysFont(None, 32)
            overlay = pygame.Surface((600, 300))
            overlay.set_alpha(230)
            overlay.fill((0, 0, 0))
            controls = [
                "Controls:",
                "Left Click: Select / Place buildings",
                "Right Click: Move command for SCVs and troops",
                "P: Build mode. Then press:",
                "   B - Barracks, F - Tank Factory, W - Wraith Factory, T - Turret, N - Bunker",
                "S: Queue production order for selected building",
                "R: Repair command (with SCV selected)",
                "X: Upgrade weapon damage (cost 100 minerals)",
                "A: Attack command (target location)",
                "C: Hold to view this help overlay"
            ]
            for i, line in enumerate(controls):
                text = font.render(line, True, (255,255,255))
                overlay.blit(text, (20, 20 + i * 32))
            surface.blit(overlay, (SCREEN_WIDTH//2 - 300, SCREEN_HEIGHT//2 - 150))
        draw_controls(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()
