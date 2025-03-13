import pygame
import sys
import random
import math
from pygame.locals import *

# ----- Constants -----
WORLD_WIDTH, WORLD_HEIGHT = 2000, 2000
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
CAMERA_BORDER = 20       # pixels from edge to pan
CAMERA_SPEED = 300       # pixels per second

# Costs
COST_BARRACKS = 150
COST_SCV = 50
COST_MARINE = 50
COST_TANK = 100
COST_WRAITH = 150
COST_TANK_FACTORY = 200
COST_WRAITH_FACTORY = 250
COST_REFINERY = 100

# Mining settings
MINING_CYCLE = 4      # seconds per mining cycle
MINING_YIELD = 8      # minerals gathered per cycle

# Production cooldowns for enemy production buildings (in seconds)
production_cooldowns = {
    "Command Center": 10,
    "Barracks": 10,
    "Tank Factory": 25,
    "Wraith Factory": 30
}

# Shooting / attack settings
MARINE_SHOOT_COOLDOWN = 0.5  # seconds between shots
PROJECTILE_SPEED = 300       # pixels per second
PROJECTILE_DAMAGE = 15

SCV_ATTACK_DAMAGE = 5  # per second

# ----- New Classes -----
class VespaneGeyser:
    def __init__(self, x, y, amount=2000):
        self.x = x
        self.y = y
        self.amount = amount
        self.mining_scvs = []  # cap: max 3 SCVs per geyser

# ----- Modified Classes -----
class Building:
    def __init__(self, b_type, x, y, owner, complete=False):
        self.type = b_type
        self.x = x
        self.y = y
        self.owner = owner  # "player" or "enemy"
        # Health values: Command Center = 2500, Refinery = 500, others = 1000
        if b_type == "Command Center":
            self.health = 2500
        elif b_type == "Refinery":
            self.health = 500
        else:
            self.health = 1000
        self.progress = 100 if complete else 0
        self.complete = complete
        self.builder = None  # Assigned SCV during construction
        self.production_timer = 0  # For production buildings
        self.geyser = None  # For Refinery: link to a geyser

    def update(self, dt):
        if not self.complete:
            # If a builder is assigned, only add progress if it is close enough
            if self.builder is not None:
                d = math.hypot(self.builder.x - self.x, self.builder.y - self.y)
                if d < 5:
                    self.progress += 20 * dt
            else:
                # Without a builder, progress slowly on its own
                self.progress += 20 * dt
            if self.progress >= 100:
                self.progress = 100
                self.complete = True
                print(f"{self.owner.capitalize()}'s {self.type} construction complete!")
                # Reset builder state so it can resume its tasks
                if self.builder is not None:
                    self.builder.state = "idle"
                    self.builder.target_building = None

class Unit:
    def __init__(self, u_type, x, y, owner):
        self.type = u_type
        self.x = x
        self.y = y
        self.owner = owner  # "player" or "enemy"
        self.health = 50
        self.move_target = None  # For movement commands

        if u_type == "SCV":
            # SCVs spawn idle.
            self.state = "idle"  # States: idle, to_mineral, mining, to_depot, building, moving, attack_move, attacking, to_vespane, mining_vespane
            self.mine_timer = 0
            self.target_mineral = None
            self.target_geyser = None  # for vespane mining
            self.deposit_target = None
            self.target_building = None
            self.attack_target = None
            self.attack_timer = 0
            self.cargo = 0  # For carrying minerals
        elif u_type == "Marine":
            self.state = "idle"
            self.target_enemy = None
            self.shoot_timer = 0
        elif u_type in ["Tank", "Wraith"]:
            self.state = "idle"
            self.target_enemy = None
            self.shoot_timer = 0

class Mineral:
    def __init__(self, x, y, amount=1500):
        self.x = x
        self.y = y
        self.amount = amount
        self.mining_scvs = []  # Cap: max 2 SCVs per mineral

class Projectile:
    def __init__(self, x, y, target, speed, damage, owner):
        self.x = x
        self.y = y
        self.target = target  # Target with x, y, health attributes
        self.speed = speed
        self.damage = damage
        self.owner = owner  # "player" or "enemy"

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

def generate_minerals_cshape(center, owner):
    cx, cy = center
    mines = []
    if owner == "player":
        start_angle = math.radians(30)
        end_angle = math.radians(270)
    else:
        start_angle = math.radians(210)
        end_angle = math.radians(450)
    total_angle = end_angle - start_angle
    count = 10
    for i in range(count):
        angle = start_angle + (total_angle * i / (count - 1))
        x = cx + 200 * math.cos(angle)
        y = cy + 200 * math.sin(angle)
        mines.append(Mineral(x, y, amount=1500))
    return mines

# ----- Game Class (Enemy AI & Additional Features) -----
class Game:
    def __init__(self):
        self.buildings = []
        self.units = []
        self.projectiles = []
        # Resources: player and enemy minerals, plus vespane
        self.resources = {"player": 50, "enemy": 50, "vespane": 0}
        self.game_over = False
        self.winner = None
        self.player_minerals = []
        self.enemy_minerals = []
        self.geysers = []  # Vespane geysers

        # Enemy AI parameters
        # These control worker count, building orders, and later attacks.
        self.enemy_attack_threshold = 12  # Total combat units required to launch an attack
        self.enemy_attack_cooldown = 30     # Seconds between attack waves
        self.enemy_attack_timer = 0

        # Flags to help coordinate enemy production
        self.enemy_first_attack_done = False

    def add_building(self, b_type, x, y, owner, complete=False):
        b = Building(b_type, x, y, owner, complete)
        self.buildings.append(b)
        return b

    def add_unit(self, u_type, x, y, owner):
        u = Unit(u_type, x, y, owner)
        self.units.append(u)
        return u

    def spawn_unit(self, building):
        if not building.complete:
            print(f"{building.owner.capitalize()}'s {building.type} is under construction!")
            return
        if building.owner == "enemy":
            if building.type == "Command Center":
                enemy_scvs = len([u for u in self.units if u.owner=="enemy" and u.type=="SCV"])
                # Do not spawn additional SCVs until we have at least one Barracks built
                if enemy_scvs < 9:
                    if self.resources["enemy"] < COST_SCV:
                        return
                    self.resources["enemy"] -= COST_SCV
                    unit = self.add_unit("SCV", building.x + 10, building.y + 10, "enemy")
                    unit.state = "idle"
                    unit.deposit_target = building
                    print("Enemy SCV spawned.")
            elif building.type == "Barracks":
                if self.resources["enemy"] < COST_MARINE:
                    return
                self.resources["enemy"] -= COST_MARINE
                offset_x = random.uniform(-20, 20)
                offset_y = random.uniform(-20, 20)
                unit = self.add_unit("Marine", building.x + offset_x, building.y + offset_y, "enemy")
                print("Enemy Marine spawned.")
            elif building.type == "Tank Factory":
                if self.resources["enemy"] < COST_TANK:
                    return
                self.resources["enemy"] -= COST_TANK
                offset_x = random.uniform(-20, 20)
                offset_y = random.uniform(-20, 20)
                unit = self.add_unit("Tank", building.x + offset_x, building.y + offset_y, "enemy")
                print("Enemy Tank spawned.")
            elif building.type == "Wraith Factory":
                if self.resources["enemy"] < COST_WRAITH:
                    return
                self.resources["enemy"] -= COST_WRAITH
                offset_x = random.uniform(-20, 20)
                offset_y = random.uniform(-20, 20)
                unit = self.add_unit("Wraith", building.x + offset_x, building.y + offset_y, "enemy")
                print("Enemy Wraith spawned.")
        else:
            # Player production (unchanged)
            if building.type == "Command Center":
                if self.resources["player"] < COST_SCV:
                    print("Not enough minerals!")
                    return
                self.resources["player"] -= COST_SCV
                unit = self.add_unit("SCV", building.x + 10, building.y + 10, "player")
                unit.state = "idle"
                unit.deposit_target = building
                print("Player SCV spawned.")
            elif building.type == "Barracks":
                if self.resources["player"] < COST_MARINE:
                    print("Not enough minerals!")
                    return
                self.resources["player"] -= COST_MARINE
                offset_x = random.uniform(-20, 20)
                offset_y = random.uniform(-20, 20)
                unit = self.add_unit("Marine", building.x + offset_x, building.y + offset_y, "player")
                print("Player Marine spawned.")
            elif building.type == "Tank Factory":
                if self.resources["player"] < COST_TANK:
                    print("Not enough minerals!")
                    return
                self.resources["player"] -= COST_TANK
                offset_x = random.uniform(-20, 20)
                offset_y = random.uniform(-20, 20)
                unit = self.add_unit("Tank", building.x + offset_x, building.y + offset_y, "player")
                print("Player Tank spawned.")
            elif building.type == "Wraith Factory":
                if self.resources["player"] < COST_WRAITH:
                    print("Not enough minerals!")
                    return
                self.resources["player"] -= COST_WRAITH
                offset_x = random.uniform(-20, 20)
                offset_y = random.uniform(-20, 20)
                unit = self.add_unit("Wraith", building.x + offset_x, building.y + offset_y, "player")
                print("Player Wraith spawned.")
        return

    def move_towards(self, unit, target_x, target_y, dt):
        speed = 100  # pixels per second
        dx = target_x - unit.x
        dy = target_y - unit.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        move_dist = speed * dt
        if move_dist > dist:
            unit.x, unit.y = target_x, target_y
        else:
            unit.x += (dx / dist) * move_dist
            unit.y += (dy / dist) * move_dist

    def find_priority_target(self, attacker, enemy_owner="enemy", max_range=80):
        candidates = []
        for obj in self.units:
            if obj.owner == enemy_owner:
                if attacker.type == "Tank" and obj.type == "Wraith":
                    continue
                dist = math.hypot(attacker.x - obj.x, attacker.y - obj.y)
                if dist <= max_range:
                    if obj.type == "Marine":
                        prio = 1
                    elif obj.type == "SCV":
                        prio = 2
                    else:
                        prio = 4
                    candidates.append((obj, dist, prio))
        for b in self.buildings:
            if b.owner == enemy_owner:
                dist = math.hypot(attacker.x - b.x, attacker.y - b.y)
                if dist <= max_range:
                    candidates.append((b, dist, 3))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[2], x[1]))
        return candidates[0][0]

    def update(self, dt):
        # Update buildings
        for b in self.buildings:
            b.update(dt)
        # Production from production buildings (e.g., Command Center, Barracks, etc.)
        for b in self.buildings:
            if b.owner == "enemy" and b.complete and b.type in production_cooldowns:
                b.production_timer += dt
                if b.production_timer >= production_cooldowns[b.type]:
                    self.spawn_unit(b)
                    b.production_timer = 0
            if b.owner == "player" and b.complete and b.type in production_cooldowns:
                b.production_timer += dt
                if b.production_timer >= production_cooldowns[b.type]:
                    self.spawn_unit(b)
                    b.production_timer = 0

        # Update projectiles
        for p in self.projectiles[:]:
            if p.update(dt):
                p.target.health -= p.damage
                self.projectiles.remove(p)

        # Update units' individual behaviors
        for u in self.units:
            # --- Player SCV behavior (mining, moving, building) ---
            if u.type == "SCV" and u.owner == "player":
                if u.state == "idle" and not u.target_mineral:
                    available = [m for m in self.player_minerals if m.amount > 0 and math.hypot(u.x - m.x, u.y - m.y) <= 300]
                    for m in available:
                        if len(m.mining_scvs) < 2:
                            m.mining_scvs.append(u)
                            u.target_mineral = m
                            u.state = "to_mineral"
                            break
                if u.state == "to_mineral":
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
                        self.resources["player"] += u.cargo
                        u.cargo = 0
                        u.state = "idle"
                        available = [m for m in self.player_minerals if m.amount > 0 and math.hypot(u.x - m.x, u.y - m.y) <= 300]
                        if available:
                            u.target_mineral = random.choice(available)
                            u.state = "to_mineral"
                elif u.state == "moving" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if math.hypot(u.x - u.move_target[0], u.y - u.move_target[1]) < 5:
                        u.state = "idle"
                        u.move_target = None

            # --- Player Marine behavior (attack orders) ---
            if u.type == "Marine" and u.owner == "player":
                if u.state == "moving" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if math.hypot(u.x - u.move_target[0], u.y - u.move_target[1]) < 5:
                        u.state = "idle"
                        u.move_target = None
                if u.state == "attack_move" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if not u.target_enemy:
                        u.target_enemy = self.find_priority_target(u, enemy_owner="enemy", max_range=80)
                    if u.target_enemy:
                        u.state = "attacking"
                if u.state == "attacking" and u.target_enemy:
                    dist = math.hypot(u.x - u.target_enemy.x, u.y - u.target_enemy.y)
                    if dist < 20:
                        dx = u.x - u.target_enemy.x
                        dy = u.y - u.target_enemy.y
                        if dx == 0 and dy == 0:
                            dx, dy = 1, 0
                        u.x += (dx / dist) * 50 * dt
                        u.y += (dy / dist) * 50 * dt
                    elif dist > 30:
                        dx = u.target_enemy.x - u.x
                        dy = u.target_enemy.y - u.y
                        u.x += (dx / dist) * 50 * dt
                        u.y += (dy / dist) * 50 * dt
                    else:
                        u.shoot_timer += dt
                        if u.shoot_timer >= MARINE_SHOOT_COOLDOWN:
                            proj = Projectile(u.x, u.y, u.target_enemy, PROJECTILE_SPEED, PROJECTILE_DAMAGE, "player")
                            self.projectiles.append(proj)
                            u.shoot_timer = 0
                    if u.target_enemy.health <= 0:
                        u.state = "idle"
                        u.target_enemy = None

            # --- Enemy SCV behavior (mining, building) ---
            if u.type == "SCV" and u.owner == "enemy":
                if u.state == "idle" and not u.target_mineral:
                    chosen = None
                    for m in self.enemy_minerals:
                        if m.amount > 0 and math.hypot(u.x - m.x, u.y - m.y) <= 300:
                            if len(m.mining_scvs) < 2:
                                chosen = m
                                m.mining_scvs.append(u)
                                break
                    if chosen:
                        u.target_mineral = chosen
                        u.state = "to_mineral"
                if u.state == "to_mineral":
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
                        self.resources["enemy"] += u.cargo
                        u.cargo = 0
                        u.state = "idle"
                        available = [m for m in self.enemy_minerals if m.amount > 0 and math.hypot(u.x - m.x, u.y - m.y) <= 300]
                        if available:
                            u.target_mineral = random.choice(available)
                            u.state = "to_mineral"

            # --- Enemy combat units (Marine, Tank, Wraith) behavior ---
            if u.type in ["Marine", "Tank", "Wraith"] and u.owner == "enemy":
                if u.state == "idle":
                    target = self.find_priority_target(u, enemy_owner="player", max_range=80)
                    if target:
                        u.state = "attack_move"
                        u.target_enemy = target
                if u.state == "attack_move" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                if u.state == "attacking" and u.target_enemy:
                    dist = math.hypot(u.x - u.target_enemy.x, u.y - u.target_enemy.y)
                    if dist < 20:
                        dx = u.x - u.target_enemy.x
                        dy = u.y - u.target_enemy.y
                        if dx == 0 and dy == 0:
                            dx, dy = 1, 0
                        u.x += (dx / dist) * 50 * dt
                        u.y += (dy / dist) * 50 * dt
                    elif dist > 30:
                        dx = u.target_enemy.x - u.x
                        dy = u.target_enemy.y - u.y
                        u.x += (dx / dist) * 50 * dt
                        u.y += (dy / dist) * 50 * dt
                    else:
                        u.shoot_timer += dt
                        if u.shoot_timer >= MARINE_SHOOT_COOLDOWN:
                            proj = Projectile(u.x, u.y, u.target_enemy, PROJECTILE_SPEED, PROJECTILE_DAMAGE, "enemy")
                            self.projectiles.append(proj)
                            u.shoot_timer = 0
                    if u.target_enemy.health <= 0:
                        u.state = "idle"
                        u.target_enemy = None

        # --- Enemy Production / Build Decisions ---

        enemy_scvs = len([u for u in self.units if u.owner=="enemy" and u.type=="SCV"])
        # Check if a Barracks exists or is in progress
        barracks_exists = any(b for b in self.buildings if b.owner=="enemy" and b.type=="Barracks" and b.complete)
        barracks_in_progress = any(b for b in self.buildings if b.owner=="enemy" and b.type=="Barracks" and not b.complete)

        if enemy_scvs < 9:
            cc = self.get_building("Command Center", "enemy")
            if cc and self.resources["enemy"] >= COST_SCV:
                self.spawn_unit(cc)
        elif enemy_scvs >= 9:
            if not (barracks_exists or barracks_in_progress):
                cc = self.get_building("Command Center", "enemy")
                if cc and self.resources["enemy"] >= COST_BARRACKS:
                    idle_scvs = [u for u in self.units if u.owner=="enemy" and u.type=="SCV" and u.state=="idle"]
                    if idle_scvs:
                        scv = idle_scvs[0]
                        # Choose a build site roughly 100 pixels away from the Command Center
                        angle = random.uniform(0, 2 * math.pi)
                        bx = cc.x + math.cos(angle) * 100
                        by = cc.y + math.sin(angle) * 100
                        new_b = self.add_building("Barracks", bx, by, "enemy", complete=False)
                        new_b.builder = scv
                        scv.state = "building"
                        scv.target_building = new_b
                        self.resources["enemy"] -= COST_BARRACKS
                        print("Enemy begins building Barracks.")
            else:
                # Once a Barracks is complete, resume SCV production up to 21 workers
                if barracks_exists and enemy_scvs < 21:
                    cc = self.get_building("Command Center", "enemy")
                    if cc and self.resources["enemy"] >= COST_SCV:
                        self.spawn_unit(cc)

        # Additional enemy expansion: build additional production buildings after Barracks is built.
        if barracks_exists:
            tank_factory_exists = any(b for b in self.buildings if b.owner=="enemy" and b.type=="Tank Factory" and b.complete)
            if not tank_factory_exists and self.resources["enemy"] >= COST_TANK_FACTORY:
                cc = self.get_building("Command Center", "enemy")
                if cc:
                    bx = cc.x + random.randint(-50, 50)
                    by = cc.y + random.randint(-50, 50)
                    new_tf = self.add_building("Tank Factory", bx, by, "enemy", complete=False)
                    self.resources["enemy"] -= COST_TANK_FACTORY
                    print("Enemy begins building Tank Factory.")
            wraith_factory_exists = any(b for b in self.buildings if b.owner=="enemy" and b.type=="Wraith Factory" and b.complete)
            if tank_factory_exists and not wraith_factory_exists and self.resources["enemy"] >= COST_WRAITH_FACTORY:
                cc = self.get_building("Command Center", "enemy")
                if cc:
                    bx = cc.x + random.randint(-50, 50)
                    by = cc.y + random.randint(-50, 50)
                    new_wf = self.add_building("Wraith Factory", bx, by, "enemy", complete=False)
                    self.resources["enemy"] -= COST_WRAITH_FACTORY
                    print("Enemy begins building Wraith Factory.")

        # --- Enemy Attack Wave Logic ---
        # Combine enemy combat units (Marine, Tank, Wraith) into a troop count.
        enemy_troops = [u for u in self.units if u.owner=="enemy" and u.type in ["Marine", "Tank", "Wraith"]]
        if len(enemy_troops) >= self.enemy_attack_threshold and self.enemy_attack_timer <= 0:
            pc = self.get_building("Command Center", "player")
            if pc:
                for u in enemy_troops:
                    if u.state in ["idle", "attack_move"]:
                        u.state = "attack_move"
                        u.move_target = (pc.x, pc.y)
                print("Enemy is launching an attack!")
                self.enemy_attack_timer = self.enemy_attack_cooldown
        if self.enemy_attack_timer > 0:
            self.enemy_attack_timer -= dt

        # --- Check Win/Loss Conditions ---
        if not [b for b in self.buildings if b.owner=="player"]:
            self.game_over = True
            self.winner = "Enemy"
        if not [b for b in self.buildings if b.owner=="enemy"]:
            self.game_over = True
            self.winner = "Player"

    def get_building(self, b_type, owner):
        for b in self.buildings:
            if b.type == b_type and b.owner == owner and b.complete:
                return b
        return None

# ----- Controls Pop-Up Function -----
def draw_controls(surface):
    controls = [
        "Controls:",
        "Left Click: Select / Place buildings",
        "Right Click: Issue move, mine, or attack commands to SCVs",
        "B: Begin Build (then F: Tank Factory, W: Wraith Factory, R: Refinery)",
        "A: Attack command",
        "C: Hold to view controls"
    ]
    font = pygame.font.SysFont(None, 24)
    overlay = pygame.Surface((400, 150))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    for i, line in enumerate(controls):
        text = font.render(line, True, (255,255,255))
        overlay.blit(text, (10, 10 + i * 24))
    surface.blit(overlay, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 75))

# ----- Main Setup -----
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("RTS Expanded")
clock = pygame.time.Clock()

cam_offset = [0, 0]

waiting_for_build_key = False
build_mode = None   # "Barracks", "Tank Factory", "Wraith Factory", "Refinery"
builder_unit = None

game = Game()
player_cc = game.add_building("Command Center", 300, 300, "player", complete=True)
enemy_cc = game.add_building("Command Center", 1700, 1700, "enemy", complete=True)

game.player_minerals = generate_minerals_cshape((player_cc.x, player_cc.y), "player")
game.enemy_minerals = generate_minerals_cshape((enemy_cc.x, enemy_cc.y), "enemy")

game.geysers.append(VespaneGeyser(500, 500))
game.geysers.append(VespaneGeyser(1500, 1500))

# ---- Initial SCVs (with deposit targets set) ----
for i in range(4):
    scv = game.add_unit("SCV", player_cc.x + 20 + i * 15, player_cc.y + 20, "player")
    scv.state = "idle"
    scv.deposit_target = player_cc

for i in range(4):
    escv = game.add_unit("SCV", enemy_cc.x + 20 + i * 15, enemy_cc.y + 20, "enemy")
    escv.state = "idle"
    escv.deposit_target = enemy_cc

selecting = False
selection_start = (0, 0)
selection_rect = pygame.Rect(0, 0, 0, 0)
selected_units = []

attack_command_active = False

# ----- Main Loop -----
running = True
while running:
    dt = clock.tick(60) / 1000.0

    cam_offset[0] = max(0, min(WORLD_WIDTH - SCREEN_WIDTH, cam_offset[0] + (pygame.mouse.get_pos()[0] < CAMERA_BORDER and -CAMERA_SPEED*dt or (pygame.mouse.get_pos()[0] > SCREEN_WIDTH - CAMERA_BORDER and CAMERA_SPEED*dt or 0))))
    cam_offset[1] = max(0, min(WORLD_HEIGHT - SCREEN_HEIGHT, cam_offset[1] + (pygame.mouse.get_pos()[1] < CAMERA_BORDER and -CAMERA_SPEED*dt or (pygame.mouse.get_pos()[1] > SCREEN_HEIGHT - CAMERA_BORDER and CAMERA_SPEED*dt or 0))))

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False
            if event.key == K_b:
                if selected_units and len(selected_units) == 1 and selected_units[0].type == "SCV":
                    waiting_for_build_key = True
                    builder_unit = selected_units[0]
                    build_mode = "Barracks"
                    print("Press F for Tank Factory, W for Wraith Factory, R for Refinery, or any other key for Barracks.")
            elif waiting_for_build_key:
                if event.key == K_f:
                    build_mode = "Tank Factory"
                elif event.key == K_w:
                    build_mode = "Wraith Factory"
                elif event.key == K_r:
                    build_mode = "Refinery"
                waiting_for_build_key = False
                cost = (COST_BARRACKS if build_mode=="Barracks" else
                        COST_TANK_FACTORY if build_mode=="Tank Factory" else
                        COST_WRAITH_FACTORY if build_mode=="Wraith Factory" else
                        COST_REFINERY)
                if game.resources["player"] < cost:
                    print("Not enough minerals!")
                    build_mode = None
                else:
                    game.resources["player"] -= cost
                    print(f"{build_mode} build mode activated. Click on the map to place it.")
            if event.key == K_s:
                for obj in selected_units:
                    if hasattr(obj, "type") and obj.type in ["Command Center", "Barracks", "Tank Factory", "Wraith Factory"]:
                        game.spawn_unit(obj)
                        break
            if event.key == K_a:
                attack_command_active = True
                print("Attack command active. Click on target location.")

        # --- RIGHT CLICK for movement/command orders ---
        if event.type == MOUSEBUTTONDOWN and event.button == 3:
            wx = event.pos[0] + cam_offset[0]
            wy = event.pos[1] + cam_offset[1]
            # Check for mineral clicks to command SCVs to mine
            clicked_on_mineral = False
            for m in game.player_minerals:
                if m.amount > 0 and math.hypot(m.x - wx, m.y - wy) < 10:
                    if selected_units and any(u.type == "SCV" for u in selected_units):
                        for u in selected_units:
                            if u.type == "SCV":
                                u.target_mineral = m
                                u.state = "to_mineral"
                                print("Player SCV reverting to mining state.")
                        clicked_on_mineral = True
                        break
            if clicked_on_mineral:
                continue
            # Check for geyser clicks for vespane mining
            clicked_on_geyser = False
            for g in game.geysers:
                rct = pygame.Rect(g.x - 15, g.y - 15, 30, 30)
                if rct.collidepoint(wx, wy):
                    found_refinery = False
                    for b in game.buildings:
                        if b.type == "Refinery" and b.geyser == g and b.complete:
                            found_refinery = True
                            break
                    if found_refinery and selected_units and any(u.type == "SCV" for u in selected_units):
                        for u in selected_units:
                            if u.type == "SCV":
                                u.target_geyser = g
                                u.state = "to_vespane"
                                print("Player SCV directed to vespane geyser.")
                        clicked_on_geyser = True
                        break
            if clicked_on_geyser:
                continue
            # Check for enemy unit clicks for attack command
            clicked_on_enemy = False
            for u in game.units:
                if u.owner == "enemy" and math.hypot(u.x - wx, u.y - wy) < 15:
                    if selected_units and any(v.type == "SCV" for v in selected_units):
                        for v in selected_units:
                            if v.type == "SCV":
                                v.state = "attack_move"
                                v.move_target = (wx, wy)
                                v.attack_target = u
                                print("Player SCV directed to attack enemy.")
                        clicked_on_enemy = True
                        break
            if clicked_on_enemy:
                continue
            # Otherwise, issue a move order to selected SCVs
            if selected_units:
                for u in selected_units:
                    if u.type == "SCV":
                        u.state = "moving"
                        u.move_target = (wx, wy)
                        u.target_mineral = None
                        u.target_building = None
                print("Override: SCVs moving to", (wx, wy))

        # --- LEFT CLICK for selection & building placement (no move orders here) ---
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            wx = event.pos[0] + cam_offset[0]
            wy = event.pos[1] + cam_offset[1]
            # Check for mineral clicks to force SCV mining state
            clicked_on_mineral = False
            for m in game.player_minerals:
                if m.amount > 0 and math.hypot(m.x - wx, m.y - wy) < 10:
                    if selected_units and any(u.type == "SCV" for u in selected_units):
                        for u in selected_units:
                            if u.type == "SCV":
                                u.target_mineral = m
                                u.state = "to_mineral"
                                print("Player SCV reverting to mining state.")
                        clicked_on_mineral = True
                        break
            if clicked_on_mineral:
                continue
            # Check for geyser clicks for vespane mining
            clicked_on_geyser = False
            for g in game.geysers:
                rct = pygame.Rect(g.x - 15, g.y - 15, 30,30)
                if rct.collidepoint(wx, wy):
                    found_refinery = False
                    for b in game.buildings:
                        if b.type == "Refinery" and b.geyser == g and b.complete:
                            found_refinery = True
                            break
                    if found_refinery and selected_units and any(u.type == "SCV" for u in selected_units):
                        for u in selected_units:
                            if u.type == "SCV":
                                u.target_geyser = g
                                u.state = "to_vespane"
                                print("Player SCV directed to vespane geyser.")
                        clicked_on_geyser = True
                        break
            if clicked_on_geyser:
                continue
            # Check for unfinished building clicks
            clicked_on_building = False
            for b in game.buildings:
                rct = pygame.Rect(b.x - 15, b.y - 15, 30,30)
                if rct.collidepoint(wx, wy) and not b.complete:
                    if selected_units and any(u.type == "SCV" for u in selected_units):
                        for u in selected_units:
                            if u.type == "SCV":
                                u.target_building = b
                                u.state = "building"
                                print("Player SCV directed to finish building.")
                        clicked_on_building = True
                        break
            if clicked_on_building:
                continue
            # Check for enemy unit clicks for attack command
            clicked_on_enemy = False
            for u in game.units:
                if u.owner == "enemy" and math.hypot(u.x - wx, u.y - wy) < 15:
                    if selected_units and any(v.type == "SCV" for v in selected_units):
                        for v in selected_units:
                            if v.type == "SCV":
                                v.state = "attack_move"
                                v.move_target = (wx, wy)
                                v.attack_target = u
                                print("Player SCV directed to attack enemy.")
                        clicked_on_enemy = True
                        break
            if clicked_on_enemy:
                continue
            # Otherwise, begin selection
            if event.button == 1:
                if build_mode is not None and builder_unit:
                    cc = game.get_building("Command Center", "player")
                    if cc and build_mode == "Barracks":
                        dx = wx - cc.x
                        dy = wy - cc.y
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            dist = 1
                        bx = cc.x + (dx / dist) * 100
                        by = cc.y + (dy / dist) * 100
                    else:
                        bx, by = wx, wy
                    new_b = game.add_building(build_mode, bx, by, "player", complete=False)
                    new_b.builder = builder_unit
                    builder_unit.state = "building"
                    builder_unit.target_building = new_b
                    for g in game.geysers:
                        if pygame.Rect(g.x - 15, g.y - 15, 30, 30).collidepoint(wx, wy):
                            new_b.geyser = g
                            g.mining_scvs.append(builder_unit)
                            break
                    print(f"Player {build_mode} placed at ({bx}, {by}).")
                    build_mode = None
                    selected_units = []
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
                    for b in game.buildings:
                        rct = pygame.Rect(b.x - 15, b.y - 15, 30, 30)
                        if rct.collidepoint(selection_rect.center):
                            selected_units = [b]
                            found = True
                            print(f"Selected {b.owner}'s {b.type}.")
                            break
                    if not found:
                        for u in game.units:
                            if u.owner == "player" and u.type in ["SCV", "Marine", "Tank", "Wraith"]:
                                if math.hypot(u.x - selection_rect.centerx, u.y - selection_rect.centery) < 10:
                                    selected_units = [u]
                                    found = True
                                    print(f"Selected {u.owner}'s {u.type}.")
                                    break
                    if not found:
                        selected_units = []
                else:
                    selected_units = []
                    for u in game.units:
                        if u.owner == "player" and u.type in ["SCV", "Marine", "Tank", "Wraith"]:
                            if selection_rect.collidepoint(u.x, u.y):
                                selected_units.append(u)
                                if len(selected_units) >= 15:
                                    break
                    if selected_units:
                        print(f"Selected {len(selected_units)} units.")

    if not game.game_over:
        game.update(dt)
    else:
        print(f"Game Over! {game.winner} wins!")
        running = False

    screen.fill((0, 0, 0))
    for x in range(0, WORLD_WIDTH, 100):
        pygame.draw.line(screen, (20,20,20), (x - cam_offset[0], 0 - cam_offset[1]),
                         (x - cam_offset[0], WORLD_HEIGHT - cam_offset[1]))
    for y in range(0, WORLD_HEIGHT, 100):
        pygame.draw.line(screen, (20,20,20), (0 - cam_offset[0], y - cam_offset[1]),
                         (WORLD_WIDTH - cam_offset[0], y - cam_offset[1]))

    for m in game.player_minerals:
        if m.amount > 0:
            pygame.draw.circle(screen, (255,255,0),
                               (int(m.x - cam_offset[0]), int(m.y - cam_offset[1])), 8)
    for m in game.enemy_minerals:
        if m.amount > 0:
            pygame.draw.circle(screen, (200,200,0),
                               (int(m.x - cam_offset[0]), int(m.y - cam_offset[1])), 8)

    for g in game.geysers:
        color = (255,255,0)
        for b in game.buildings:
            if b.type == "Refinery" and b.geyser == g and b.complete:
                color = (255,165,0)
                break
        rct = pygame.Rect(g.x - 15 - cam_offset[0], g.y - 15 - cam_offset[1], 30,30)
        pygame.draw.rect(screen, color, rct)

    for b in game.buildings:
        if b.type == "Command Center":
            col = (0,0,255) if b.owner=="player" else (255,0,0)
        elif b.type == "Barracks":
            col = (255,165,0) if b.owner=="player" else (200,100,0)
        elif b.type in ["Tank Factory", "Wraith Factory"]:
            col = (150,150,150) if b.owner=="player" else (100,100,100)
        elif b.type == "Refinery":
            col = (128,0,128)
        else:
            col = (128,128,128)
        if not b.complete:
            col = (100,100,100)
        rct = pygame.Rect(b.x - 15 - cam_offset[0], b.y - 15 - cam_offset[1], 30,30)
        pygame.draw.rect(screen, col, rct)
        bar_w, bar_h = 30, 4
        ratio = b.health / (2500 if b.type=="Command Center" else 500 if b.type=="Refinery" else 1000)
        pygame.draw.rect(screen, (255,0,0), (rct.left, rct.top-6, bar_w, bar_h))
        pygame.draw.rect(screen, (0,255,0), (rct.left, rct.top-6, int(bar_w*ratio), bar_h))
        if not b.complete:
            font = pygame.font.SysFont(None, 20)
            txt = font.render(f"{int(b.progress)}%", True, (255,255,255))
            screen.blit(txt, (b.x-15-cam_offset[0], b.y-15-cam_offset[1]))
        if b in selected_units:
            pygame.draw.rect(screen, (0,255,0), rct, 2)

    for u in game.units:
        pos = (int(u.x - cam_offset[0]), int(u.y - cam_offset[1]))
        if u.type == "SCV":
            pygame.draw.circle(screen, (255,255,255), pos, 10)
        elif u.type == "Marine":
            pygame.draw.circle(screen, (255,255,255), pos, 8)
            oval = pygame.Rect(pos[0]-5, pos[1]-5, 10,10)
            pygame.draw.ellipse(screen, (255,165,0), oval, 2)
        elif u.type == "Tank":
            oval = pygame.Rect(pos[0]-10, pos[1]-5, 20,10)
            pygame.draw.ellipse(screen, (255,0,0), oval)
        elif u.type == "Wraith":
            oval = pygame.Rect(pos[0]-10, pos[1]-5, 20,10)
            pygame.draw.ellipse(screen, (255,255,0), oval)
        bw, bh = 20, 3
        ratio = u.health / 50
        pygame.draw.rect(screen, (255,0,0), (pos[0]-10, pos[1]-15, bw, bh))
        pygame.draw.rect(screen, (0,255,0), (pos[0]-10, pos[1]-15, int(bw*ratio), bh))
        if u in selected_units:
            pygame.draw.circle(screen, (0,255,0), pos, 12, 1)

    for p in game.projectiles:
        ppos = (int(p.x-cam_offset[0]), int(p.y-cam_offset[1]))
        pygame.draw.circle(screen, (255,255,0), ppos, 4)

    if selecting:
        s_rect = pygame.Rect(selection_rect.left-cam_offset[0],
                             selection_rect.top-cam_offset[1],
                             selection_rect.width, selection_rect.height)
        pygame.draw.rect(screen, (0,255,0), s_rect, 1)

    if waiting_for_build_key and builder_unit:
        mx2, my2 = pygame.mouse.get_pos()
        preview_rect = pygame.Rect(mx2-15, my2-15, 30,30)
        pygame.draw.rect(screen, (0,255,0), preview_rect, 2)
        font = pygame.font.SysFont(None, 24)
        letter = "B" if build_mode=="Barracks" else ("F" if build_mode=="Tank Factory" else ("W" if build_mode=="Wraith Factory" else "R"))
        txt = font.render(letter, True, (0,255,0))
        screen.blit(txt, (mx2-8, my2-10))

    font = pygame.font.SysFont(None, 24)
    res_text = font.render(f"Player Minerals: {game.resources['player']}   Vespane: {game.resources['vespane']}", True, (255,255,255))
    screen.blit(res_text, (10,10))

    mini_w, mini_h = 100, 100
    minimap = pygame.Surface((mini_w, mini_h))
    minimap.fill((50,50,50))
    scale_x = mini_w / WORLD_WIDTH
    scale_y = mini_h / WORLD_HEIGHT
    for b in game.buildings:
        bx = int(b.x * scale_x)
        by = int(b.y * scale_y)
        col = (0,255,0) if b.owner=="player" else (255,0,0)
        pygame.draw.rect(minimap, col, (bx, by, 3, 3))
    for u in game.units:
        ux = int(u.x * scale_x)
        uy = int(u.y * scale_y)
        pygame.draw.circle(minimap, (255,255,255), (ux,uy), 1)
    cam_rect = pygame.Rect(int(cam_offset[0]*scale_x), int(cam_offset[1]*scale_y), int(SCREEN_WIDTH*scale_x), int(SCREEN_HEIGHT*scale_y))
    pygame.draw.rect(minimap, (255,255,0), cam_rect, 1)
    screen.blit(minimap, (10, SCREEN_HEIGHT - mini_h - 10))

    if pygame.key.get_pressed()[pygame.K_c]:
        draw_controls(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
