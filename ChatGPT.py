import pygame
import sys
import random
import math
from pygame.locals import *

# =======================
#       CONSTANTS
# =======================
WORLD_WIDTH, WORLD_HEIGHT = 3000, 3000
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
CAMERA_BORDER = 20       # When mouse is near the edge, pan camera
CAMERA_SPEED = 350       # Pixels per second

# Difficulty scaling
DIFFICULTY = "medium"  # Options: "easy", "medium", "hard"

# Tiles
TILE_SIZE = 15  # Each tile is 40 pixels square
BUILDING_GRID = {
    "Command Center": 3,   # occupies 3x3 tiles (120x120 pixels)
    "Barracks": 2,         # occupies 2x2 tiles (80x80 pixels)
    "Tank Factory": 2,     # occupies 2x2 tiles (80x80 pixels)
    "Wraith Factory": 2,   # occupies 2x2 tiles (80x80 pixels)
    "Turret": 1,           # occupies 1x1 tile (40x40 pixels)
    "Bunker": 1,
}

# Costs
COST_BARRACKS = 150       
COST_SCV = 50             
COST_MARINE = 50          
COST_TANK = 150           
COST_WRAITH = 200         
COST_TANK_FACTORY = 300   
COST_WRAITH_FACTORY = 350 
COST_TURRET = 200         
COST_BUNKER = 250         
COST_COMMAND_CENTER = 500

# Mining settings
MINING_CYCLE = 4          # Seconds per mining cycle
MINING_YIELD = 5          # Minerals per cycle
MINERAL_AMOUNT = 2000     

# Production settings
PRODUCTION_TIME = 8.0     # Seconds per unit spawn
AI_PRODUCTION_TIME = 7.0
MAX_QUEUE = 5          
AI_MAX_QUEUE = 2

# Combat settings
MARINE_SHOOT_COOLDOWN = 0.5   
PROJECTILE_SPEED = 300        
PROJECTILE_DAMAGE = 15        
SCV_ATTACK_DAMAGE = 5         

# Engagement & separation settings
ENGAGEMENT_RADIUS = 200       
SEPARATION_DISTANCE = 15      
SEPARATION_FORCE = 20         

# Turret settings
TURRET_SHOOT_INTERVAL = 1.0  
TURRET_PROJECTILE_SPEED = 400 
TURRET_PROJECTILE_DAMAGE = 10  
TURRET_RANGE = 150             

# Bunker settings
BUNKER_SHOOT_INTERVAL = 3.0  
BUNKER_PROJECTILE_SPEED = 250 
BUNKER_PROJECTILE_DAMAGE = 25 
BUNKER_RANGE = 100             
BUNKER_MAX_HEALTH = 1200       

# Upgrade system
UPGRADE_COST = 100            
player_damage_multiplier = 1.0  

# Enemy AI settings
ENEMY_ATTACK_COOLDOWN = 30  
AI_AGGRESSIVENESS = 0.0  # Increases over time (from 0.0 to 1.0)

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
#    CORE CLASSES
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
        self.owner = owner  # "player" or "enemy"
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
        self.builder = None  # SCV constructing the building
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
        # Turret behavior using the new target function
        if self.complete and self.type == "Turret":
            self.turret_shoot_timer += dt
            if self.turret_shoot_timer >= TURRET_SHOOT_INTERVAL:
                target = game.find_priority_target_for_turret(self)
                if target:
                    proj = Projectile(self.x, self.y, target, TURRET_PROJECTILE_SPEED, TURRET_PROJECTILE_DAMAGE, self.owner)
                    game.projectiles.append(proj)
                self.turret_shoot_timer = 0
        # Bunker behavior using the new target function
        if self.complete and self.type == "Bunker":
            self.bunker_shoot_timer += dt
            if self.bunker_shoot_timer >= BUNKER_SHOOT_INTERVAL:
                target = game.find_priority_target_for_bunker(self)
                if target:
                    proj = Projectile(self.x, self.y, target, BUNKER_PROJECTILE_SPEED, BUNKER_PROJECTILE_DAMAGE, self.owner)
                    game.projectiles.append(proj)
                self.bunker_shoot_timer = 0

class Unit:
    def __init__(self, u_type, x, y, owner):
        self.uid = get_next_id()
        self.type = u_type
        self.x = x
        self.y = y
        self.owner = owner  # "player" or "enemy"
        self.health = 50
        self.move_target = None  # (x, y)
        if u_type == "SCV":
            self.state = "idle"  # states: idle, to_mineral, mining, to_depot, building, repairing, moving, attack_move, attacking, retreat
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
        self.target = target  # Must have x, y, health
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

# --- New helper functions for mineral generation ---

def generate_center_minerals(center, count=15, radius=150):
    """
    Generate 'count' minerals arranged in a circle around center.
    The circle is large enough to leave room for a Command Center.
    """
    cx, cy = center
    minerals = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        minerals.append(Mineral(x, y))
    return minerals

def generate_corner_minerals_half_circle(corner, count=9, start_offset=100, arc_radius=150):
    """
    Generate 'count' minerals for a corner arranged along a flipped semicircular (half–circle) arc.
    
    Instead of fanning inward from the corner, this version flips the direction by 180°.
    It first computes the base angle for the corner (e.g., 45° for top–left), then adds π to flip it.
    An arc center is then determined by offsetting from the corner by 'start_offset' pixels
    in the direction of the flipped angle, and 'count' points are evenly distributed along a 180° arc
    centered on the flipped angle using 'arc_radius' as the radius.
    """
    cx, cy = corner

    # Determine the original base angle based on corner location.
    if cx < WORLD_WIDTH / 2 and cy < WORLD_HEIGHT / 2:           # Top–left
        base_angle = math.pi / 4      # 45°
    elif cx > WORLD_WIDTH / 2 and cy < WORLD_HEIGHT / 2:         # Top–right
        base_angle = 3 * math.pi / 4  # 135°
    elif cx < WORLD_WIDTH / 2 and cy > WORLD_HEIGHT / 2:         # Bottom–left
        base_angle = -math.pi / 4     # -45°
    else:                                                        # Bottom–right
        base_angle = -3 * math.pi / 4 # -135°

    # Flip the base angle by 180°.
    flipped_angle = base_angle + math.pi

    # Compute the arc center by offsetting from the corner in the direction of the flipped angle.
    arc_center = (cx + start_offset * math.cos(flipped_angle),
                  cy + start_offset * math.sin(flipped_angle))
    
    minerals = []
    # Distribute 'count' points evenly along a 180° arc centered on the flipped angle.
    start_angle = flipped_angle - math.pi / 2
    end_angle = flipped_angle + math.pi / 2
    for i in range(count):
        # Evenly space the angles between start_angle and end_angle.
        angle = start_angle + i * (end_angle - start_angle) / (count - 1)
        x = arc_center[0] + arc_radius * math.cos(angle)
        y = arc_center[1] + arc_radius * math.sin(angle)
        minerals.append(Mineral(x, y))
    return minerals


# =======================
#        GAME CLASS
# =======================
class Game:
    def __init__(self):
        self.buildings = []
        self.units = []
        self.projectiles = []
        self.resources = {"player": 50, "enemy": 50}
        self.game_over = False
        self.winner = None
        self.player_minerals = []
        self.enemy_minerals = []
        self.resource_drops = []
        self.enemy_attack_timer = 0
        self.elapsed_time = 0
        self.enemy_attack_stage = 0
        self.enemy_attack_threshold = 12  # Initial combat force threshold for launching an attack
        # Set AI production parameters based on difficulty.
        if DIFFICULTY == "easy":
            self.prod_time = 9.0
            self.max_queue = 5
        elif DIFFICULTY == "medium":
            self.prod_time = 8.0
            self.max_queue = 3
        elif DIFFICULTY == "hard":
            self.prod_time = 7.0
            self.max_queue = 1


    def count_units(self, owner, unit_type):
        return sum(1 for u in self.units if u.owner == owner and u.type == unit_type)

    def add_building(self, b_type, x, y, owner, complete=False):
        # Determine grid dimension (default is 1 if not found)
        grid_dim = BUILDING_GRID.get(b_type, 1)
        # Snap x and y to the nearest multiple of TILE_SIZE.
        grid_x = round(x / TILE_SIZE) * TILE_SIZE
        grid_y = round(y / TILE_SIZE) * TILE_SIZE
        b = Building(b_type, grid_x, grid_y, owner, complete)
        b.grid_dim = grid_dim  # store the grid dimension for later (e.g. collision, scaling)
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
            print(f"Queued {unit_type} at {building.type} (Queue: {len(building.production_queue)})")
            return True
        else:
            print("Production queue is full!")
        return False

    def process_production(self, building, dt):
        if building.production_queue and building.complete:
            building.production_timer += dt
            if building.production_timer >= PRODUCTION_TIME:
                order = building.production_queue.pop(0)
                if order == "SCV":
                    unit = self.add_unit("SCV", building.x + 10, building.y + 10, building.owner)
                    unit.state = "idle"
                    # Ensure newly built SCVs behave like starting SCVs:
                    if building.type == "Command Center":
                        unit.deposit_target = building
                    else:
                        unit.deposit_target = self.get_building("Command Center", building.owner)
                    print(f"{building.owner.capitalize()} SCV spawned from {building.type}.")
                elif order == "Marine":
                    offset_x = random.uniform(-20, 20)
                    offset_y = random.uniform(-20, 20)
                    unit = self.add_unit("Marine", building.x + offset_x, building.y + offset_y, building.owner)
                    print(f"{building.owner.capitalize()} Marine spawned from {building.type}.")
                elif order == "Tank":
                    offset_x = random.uniform(-20, 20)
                    offset_y = random.uniform(-20, 20)
                    unit = self.add_unit("Tank", building.x + offset_x, building.y + offset_y, building.owner)
                    print(f"{building.owner.capitalize()} Tank spawned from {building.type}.")
                elif order == "Wraith":
                    offset_x = random.uniform(-20, 20)
                    offset_y = random.uniform(-20, 20)
                    unit = self.add_unit("Wraith", building.x + offset_x, building.y + offset_y, building.owner)
                    print(f"{building.owner.capitalize()} Wraith spawned from {building.type}.")
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

    def get_target_priority(self, target):
        """
        Returns an integer indicating how important this target is to kill first.
        Lower numbers mean higher priority.
        Priority order:
        - For units:
            * Combat units ("Marine", "Tank", "Wraith") => 1
            * SCVs => 2
        - For buildings:
            * Production/defense buildings (Barracks, Tank Factory, Wraith Factory, Turret, Bunker) => 3
            * Command Center => 4
        """
        if isinstance(target, Unit):
            if target.type in ["Marine", "Tank", "Wraith"]:
                return 1
            elif target.type == "SCV":
                return 2
        elif isinstance(target, Building):
            if target.type == "Command Center":
                return 4
            else:
                return 3
        return 999


    def find_priority_target(self, attacker, enemy_owner="enemy", max_range=100):
        # 1) Gather all valid targets in range (units + buildings)
        all_targets = []

        # Collect enemy units in range
        for u in self.units:
            if u.owner == enemy_owner:
                dist = math.hypot(attacker.x - u.x, attacker.y - u.y)
                if dist <= max_range:
                    prio = self.get_target_priority(u)
                    all_targets.append((u, prio, dist))

        # Collect enemy buildings in range
        for b in self.buildings:
            if b.owner == enemy_owner:
                dist = math.hypot(attacker.x - b.x, attacker.y - b.y)
                if dist <= max_range:
                    prio = self.get_target_priority(b)
                    all_targets.append((b, prio, dist))

        # 2) If no targets in range, return None
        if not all_targets:
            return None

        # 3) Sort by (priority asc, distance asc)
        #    i.e. kill "priority 1" first, then 2, and so on
        all_targets.sort(key=lambda tup: (tup[1], tup[2]))

        # 4) Return the best target
        return all_targets[0][0]


    def update_attack_state(self, unit, dt):
        # If the current target exists and is still alive…
        if unit.target_enemy and unit.target_enemy.health > 0:
            dist = math.hypot(unit.x - unit.target_enemy.x, unit.y - unit.target_enemy.y)
            if dist <= ENGAGEMENT_RADIUS:
                # In-range: perform attack (your existing code for shooting goes here)
                unit.shoot_timer += dt
                if unit.shoot_timer >= MARINE_SHOOT_COOLDOWN:  # adapt based on unit type if needed
                    damage = PROJECTILE_DAMAGE
                    if unit.owner == "player":
                        damage = int(PROJECTILE_DAMAGE * player_damage_multiplier)
                    proj = Projectile(unit.x, unit.y, unit.target_enemy, PROJECTILE_SPEED, damage, unit.owner)
                    self.projectiles.append(proj)
                    unit.shoot_timer = 0
            else:
                # Out-of-range: continue moving toward the target.
                unit.state = "attack_move"
                unit.move_target = (unit.target_enemy.x, unit.target_enemy.y)
        else:
            # If the unit has no target or its target is dead, find a new one.
            # This new target will be chosen based on our custom get_target_priority ordering.
            new_target = self.find_priority_target(
                unit,
                enemy_owner=("enemy" if unit.owner == "player" else "player"),
                max_range=ENGAGEMENT_RADIUS * 2
            )
            if new_target:
                unit.target_enemy = new_target
                unit.state = "attacking"
            else:
                # No target found: remain in attack_move to keep moving in the general direction.
                unit.state = "attack_move"



    def apply_separation(self, dt):
        combat_units = [u for u in self.units if u.type in ["Marine", "Tank", "Wraith"]]
        for i in range(len(combat_units)):
            for j in range(i+1, len(combat_units)):
                u1 = combat_units[i]
                u2 = combat_units[j]
                dx = u1.x - u2.x
                dy = u1.y - u2.y
                dist = math.hypot(dx, dy)
                if dist < SEPARATION_DISTANCE and dist > 0:
                    overlap = SEPARATION_DISTANCE - dist
                    nx = dx / dist
                    ny = dy / dist
                    u1.x += nx * SEPARATION_FORCE * dt * (overlap / SEPARATION_DISTANCE)
                    u1.y += ny * SEPARATION_FORCE * dt * (overlap / SEPARATION_DISTANCE)
                    u2.x -= nx * SEPARATION_FORCE * dt * (overlap / SEPARATION_DISTANCE)
                    u2.y -= ny * SEPARATION_FORCE * dt * (overlap / SEPARATION_DISTANCE)

    def update_enemy_building_requirements(self):
        enemy_scv = self.count_units("enemy", "SCV")
        enemy_barracks = len([b for b in self.buildings if b.owner == "enemy" and b.type == "Barracks"])
        enemy_tank_factory = len([b for b in self.buildings if b.owner == "enemy" and b.type == "Tank Factory"])
        enemy_wraith_factory = len([b for b in self.buildings if b.owner == "enemy" and b.type == "Wraith Factory"])
        cc = self.get_building("Command Center", "enemy")
        if not cc:
            return
        if enemy_scv >= 9 * (enemy_barracks + 1) and self.resources["enemy"] >= COST_BARRACKS:
            bx, by = self.get_random_build_location(cc, radius=100, min_sep=20)
            bx = round(bx / TILE_SIZE) * TILE_SIZE
            by = round(by / TILE_SIZE) * TILE_SIZE
            self.add_building("Barracks", bx, by, "enemy", complete=False)
            self.resources["enemy"] -= COST_BARRACKS
            print("Enemy AI: Building additional Barracks")
        if enemy_scv >= 15 * (enemy_tank_factory + 1) and enemy_barracks >= 2 * (enemy_tank_factory + 1) and self.resources["enemy"] >= COST_TANK_FACTORY:
            bx, by = self.get_random_build_location(cc, radius=100, min_sep=20)
            bx = round(bx / TILE_SIZE) * TILE_SIZE
            by = round(by / TILE_SIZE) * TILE_SIZE
            self.add_building("Tank Factory", bx, by, "enemy", complete=False)
            self.resources["enemy"] -= COST_TANK_FACTORY
            print("Enemy AI: Building additional Tank Factory")
        if enemy_scv >= 17 * (enemy_wraith_factory + 1) and enemy_barracks >= 2 * (enemy_wraith_factory + 1) and enemy_tank_factory >= (enemy_wraith_factory + 1) and self.resources["enemy"] >= COST_WRAITH_FACTORY:
            bx, by = self.get_random_build_location(cc, radius=100, min_sep=20)
            bx = round(bx / TILE_SIZE) * TILE_SIZE
            by = round(by / TILE_SIZE) * TILE_SIZE
            self.add_building("Wraith Factory", bx, by, "enemy", complete=False)
            self.resources["enemy"] -= COST_WRAITH_FACTORY
            print("Enemy AI: Building additional Wraith Factory")



    def get_random_build_location(self, cc, radius=100, min_sep=20):
        """
        Returns a random (x, y) position within ±radius of the given Command Center (cc)
        that is not within min_sep of any existing building or mineral.
        Try up to 20 candidates, otherwise return the cc position.
        """
        for _ in range(20):
            candidate_x = cc.x + random.randint(-radius, radius)
            candidate_y = cc.y + random.randint(-radius, radius)
            valid = True
            # Check for proximity to all buildings.
            for b in self.buildings:
                if math.hypot(candidate_x - b.x, candidate_y - b.y) < min_sep:
                    valid = False
                    break
            # Check for proximity to all minerals (both player and enemy).
            if valid:
                for m in self.player_minerals + self.enemy_minerals:
                    if math.hypot(candidate_x - m.x, candidate_y - m.y) < min_sep:
                        valid = False
                        break
            if valid:
                return candidate_x, candidate_y
        # If no valid location is found, return the command center's location.
        return cc.x, cc.y


    # --- Enemy AI: Modified to wait until there are at least 12 Marines
    def update_enemy_ai(self, dt):
        global AI_AGGRESSIVENESS
        AI_AGGRESSIVENESS = min(1.0, self.elapsed_time / 300)
        
        enemy_scvs = self.count_units("enemy", "SCV")
        enemy_marines = sum(1 for u in self.units if u.owner=="enemy" and u.type=="Marine")
        cc = self.get_building("Command Center", "enemy")
        
        # Prioritize worker production when minerals are abundant or if SCVs are low.
        if cc and len(cc.production_queue) < AI_MAX_QUEUE:
            if enemy_scvs < 18 and self.resources["enemy"] >= COST_SCV * (1 - 0.5 * AI_AGGRESSIVENESS):
                self.resources["enemy"] -= COST_SCV
                cc.production_queue.append("SCV")
                print("Enemy AI: Producing SCV")

        self.update_enemy_building_requirements()

        enemy_turrets = [b for b in self.buildings if b.owner=="enemy" and b.type=="Turret"]
        if cc and not enemy_turrets and self.resources["enemy"] >= COST_TURRET:
            bx, by = self.get_random_build_location(cc, radius=100, min_sep=20)
            self.add_building("Turret", bx, by, "enemy", complete=False)
            self.resources["enemy"] -= COST_TURRET
            print("Enemy AI: Constructing Turret for defense")
        
        # Random production of combat units weighted by aggressiveness.
        barracks = self.get_building("Barracks", "enemy")
        if barracks and len(barracks.production_queue) < AI_MAX_QUEUE:
            if self.resources["enemy"] >= COST_MARINE and random.random() < (0.5 + AI_AGGRESSIVENESS * 0.5):
                self.resources["enemy"] -= COST_MARINE
                barracks.production_queue.append("Marine")
                print("Enemy AI: Queuing Marine")
        tank_factory = self.get_building("Tank Factory", "enemy")
        if tank_factory and len(tank_factory.production_queue) < AI_MAX_QUEUE:
            if self.resources["enemy"] >= COST_TANK and random.random() < (0.3 + AI_AGGRESSIVENESS * 0.4):
                self.resources["enemy"] -= COST_TANK
                tank_factory.production_queue.append("Tank")
                print("Enemy AI: Queuing Tank")
        wraith_factory = self.get_building("Wraith Factory", "enemy")
        if wraith_factory and len(wraith_factory.production_queue) < AI_MAX_QUEUE:
            if self.resources["enemy"] >= COST_WRAITH and random.random() < (0.2 + AI_AGGRESSIVENESS * 0.4):
                self.resources["enemy"] -= COST_WRAITH
                wraith_factory.production_queue.append("Wraith")
                print("Enemy AI: Queuing Wraith")

        # Get reference to the enemy Command Center
        cc = self.get_building("Command Center", "enemy")

        # Count total enemy combat units (Marines, Tanks, and Wraiths)
        enemy_combat = sum(1 for u in self.units if u.owner == "enemy" and u.type in ["Marine", "Tank", "Wraith"])

        # If built-up forces are below the threshold, make them patrol near the enemy Command Center.
        if enemy_combat < self.enemy_attack_threshold and cc is not None:
            for u in self.units:
                if u.owner == "enemy" and u.type in ["Marine", "Tank", "Wraith"]:
                    # Only change state if the unit is idle (or not already attacking/patrolling)
                    if u.state not in ["patrolling", "attacking", "attack_move"]:
                        u.state = "patrolling"
                        # Set a random target within 100 pixels of the enemy CC
                        u.move_target = (cc.x + random.randint(-100, 100), cc.y + random.randint(-100, 100))

        # Attack only if there are at least 12 enemy Marines.
        # Count total enemy combat units (Marines, Tanks, and Wraiths).
        enemy_combat = sum(1 for u in self.units if u.owner == "enemy" and u.type in ["Marine", "Tank", "Wraith"])

        # If the built-up forces meet or exceed the threshold and the attack timer allows an attack...
        if enemy_combat >= self.enemy_attack_threshold and self.enemy_attack_timer <= 0:
            print("Enemy AI: Launching attack wave!")
            self.enemy_attack_timer = ENEMY_ATTACK_COOLDOWN * (1 - AI_AGGRESSIVENESS * 0.5)
            # Order all enemy combat units to attack
            for u in self.units:
                if u.owner == "enemy" and u.type in ["Marine", "Tank", "Wraith"]:
                    # Try to choose an optimal target according to our priority ordering with an extended range.
                    target = self.find_priority_target(u, enemy_owner="player", max_range=ENGAGEMENT_RADIUS * 2)
                    if not target:
                        # Fall back to targeting the player's Command Center.
                        target = self.get_building("Command Center", "player")
                    if target:
                        u.target_enemy = target
                        u.state = "attacking"
            # Increase the threshold for the next attack (adjust increment as desired)
            self.enemy_attack_threshold += 5



    def update(self, dt):
        self.elapsed_time += dt
        if self.elapsed_time >= 1200:
            print("Time's up! Ending game...")
            if self.get_building("Command Center", "player"):
                self.game_over = True
                self.winner = "Player"
            else:
                self.game_over = True
                self.winner = "Enemy"
            return

        for b in self.buildings:
            b.update(dt)
            if b.production_queue is not None:
                self.process_production(b, dt)
        self.update_enemy_ai(dt)
        for p in self.projectiles[:]:
            if p.update(dt):
                p.target.health -= p.damage
                self.projectiles.remove(p)
        self.apply_separation(dt)
        if random.random() < dt / 30:
            drop = ResourceDrop(random.randint(0, WORLD_WIDTH), random.randint(0, WORLD_HEIGHT), amount=100)
            self.resource_drops.append(drop)
        for drop in self.resource_drops[:]:
            for u in self.units:
                if u.owner == "player" and u.type == "SCV":
                    if math.hypot(u.x - drop.x, u.y - drop.y) < 10:
                        self.resources["player"] += drop.amount
                        self.resource_drops.remove(drop)
                        break
                elif u.owner == "enemy" and u.type == "SCV":
                    if math.hypot(u.x - drop.x, u.y - drop.y) < 10:
                        self.resources["enemy"] += drop.amount
                        self.resource_drops.remove(drop)
                        break
        for u in self.units:
            # ---- Player SCV Behavior ----
            if u.type == "SCV" and u.owner == "player":
                if u.health < 15 and u.state != "retreat":
                    cc = self.get_building("Command Center", "player")
                    if cc:
                        u.state = "retreat"
                        u.move_target = (cc.x, cc.y)
                if u.state == "retreat":
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    u.health += 2 * dt
                    if u.health >= 50:
                        u.health = 50
                        u.state = "idle"
                    continue
                if u.state == "repairing":
                    self.move_towards(u, u.target_building.x, u.target_building.y, dt)
                    if math.hypot(u.x - u.target_building.x, u.y - u.target_building.y) < 5:
                        u.target_building.health += 10 * dt
                        if u.target_building.health >= u.target_building.max_health:
                            u.target_building.health = u.target_building.max_health
                            u.state = "idle"
                            u.target_building = None
                    continue
                if u.state == "building":
                    self.move_towards(u, u.target_building.x, u.target_building.y, dt)
                    continue
                if u.state == "idle" and u.target_mineral is None:
                    available = [m for m in self.player_minerals if m.amount > 0 and math.hypot(u.x - m.x, u.y - m.y) <= 800]
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
                    # Calculate the center of the deposit building (Command Center) using its grid dimension.
                    depot_width = u.deposit_target.grid_dim * TILE_SIZE
                    depot_height = u.deposit_target.grid_dim * TILE_SIZE
                    depot_center = (u.deposit_target.x + depot_width/2, u.deposit_target.y + depot_height/2)
                    self.move_towards(u, depot_center[0], depot_center[1], dt)
                    # Create the building rectangle to detect collision.
                    depot_rect = pygame.Rect(u.deposit_target.x, u.deposit_target.y, depot_width, depot_height)
                    if depot_rect.collidepoint(u.x, u.y):
                        self.resources["player"] += u.cargo
                        u.cargo = 0
                        if u.target_mineral and u.target_mineral.amount > 0:
                            u.state = "to_mineral"
                        else:
                            u.state = "idle"

                if u.state == "attack_move" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if not u.attack_target:
                        u.attack_target = self.find_priority_target(u, enemy_owner="enemy", max_range=ENGAGEMENT_RADIUS)
                    if u.attack_target:
                        u.state = "attacking"
                if u.state == "attacking":
                    self.update_attack_state(u, dt)
            # ---- Player Marine Behavior ----
            if u.type == "Marine" and u.owner == "player":
                if u.state == "moving" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if math.hypot(u.x - u.move_target[0], u.y - u.move_target[1]) < 5:
                        u.state = "idle"
                        u.move_target = None
                if u.state == "attack_move" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if not u.target_enemy:
                        u.target_enemy = self.find_priority_target(u, enemy_owner="enemy", max_range=ENGAGEMENT_RADIUS)
                    if u.target_enemy:
                        u.state = "attacking"
                if u.state == "attacking":
                    self.update_attack_state(u, dt)
            # ---- Player Tank and Wraith Behavior ----
            if u.type in ["Tank", "Wraith"] and u.owner == "player":
                if u.state == "moving" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if math.hypot(u.x - u.move_target[0], u.y - u.move_target[1]) < 5:
                        u.state = "idle"
                        u.move_target = None
                if u.state == "attack_move" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if not u.target_enemy:
                        u.target_enemy = self.find_priority_target(u, enemy_owner="enemy", max_range=ENGAGEMENT_RADIUS)
                    if u.target_enemy:
                        u.state = "attacking"
                if u.state == "attacking":
                    self.update_attack_state(u, dt)
            # ---- Enemy SCV Behavior ----
            if u.type == "SCV" and u.owner == "enemy":
                if u.state == "idle" and u.target_mineral is None:
                    available = [m for m in self.player_minerals if m.amount > 0 and math.hypot(u.x - m.x, u.y - m.y) <= 800]
                    if available:
                        u.target_mineral = random.choice(available)
                        u.state = "to_mineral"

                if u.state == "moving" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                    if math.hypot(u.x - u.move_target[0], u.y - u.move_target[1]) < 5:
                        u.state = "idle"
                        u.move_target = None
                    continue
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
                    # Calculate the center of the deposit building (Command Center) using its grid dimension.
                    depot_width = u.deposit_target.grid_dim * TILE_SIZE
                    depot_height = u.deposit_target.grid_dim * TILE_SIZE
                    depot_center = (u.deposit_target.x + depot_width/2, u.deposit_target.y + depot_height/2)
                    self.move_towards(u, depot_center[0], depot_center[1], dt)
                    # Create the building rectangle to detect collision.
                    depot_rect = pygame.Rect(u.deposit_target.x, u.deposit_target.y, depot_width, depot_height)
                    if depot_rect.collidepoint(u.x, u.y):
                        self.resources["enemy"] += u.cargo
                        u.cargo = 0
                        if u.target_mineral and u.target_mineral.amount > 0:
                            u.state = "to_mineral"
                        else:
                            u.state = "idle"

            # ---- Enemy Combat Units Behavior ----
            if u.type in ["Marine", "Tank", "Wraith"] and u.owner == "enemy":
                if u.state == "idle":
                    target = self.find_priority_target(u, enemy_owner="player", max_range=ENGAGEMENT_RADIUS)
                    if target is None:
                        target = self.get_building("Command Center", "player")
                    if target:
                        u.state = "attacking"
                        u.target_enemy = target
                if u.state == "attack_move" and u.move_target:
                    self.move_towards(u, u.move_target[0], u.move_target[1], dt)
                if u.state == "attacking":
                    self.update_attack_state(u, dt)
        self.units = [u for u in self.units if u.health > 0]
        self.buildings = [b for b in self.buildings if b.health > 0]
        player_buildings = [b for b in self.buildings if b.owner=="player"]
        enemy_buildings = [b for b in self.buildings if b.owner=="enemy"]
        if not player_buildings:
            self.game_over = True
            self.winner = "Enemy"
        if not enemy_buildings:
            self.game_over = True
            self.winner = "Player"

    def get_building(self, b_type, owner):
        for b in self.buildings:
            if b.type == b_type and b.owner == owner and b.complete:
                return b
        return None

    # New method for turret target selection
    def find_priority_target_for_turret(self, turret):
        # If turret belongs to the enemy, target the player's units; otherwise, target enemy units.
        target_owner = "player" if turret.owner == "enemy" else "enemy"
        return self.find_priority_target(turret, enemy_owner=target_owner, max_range=TURRET_RANGE)


    # New method for bunker target selection
    def find_priority_target_for_bunker(self, bunker):
        target_owner = "player" if bunker.owner == "enemy" else "enemy"
        return self.find_priority_target(bunker, enemy_owner=target_owner, max_range=BUNKER_RANGE)


# =======================
#    CONTROLS OVERLAY
# =======================
def draw_controls(surface):
    font = pygame.font.SysFont(None, 32)
    overlay = pygame.Surface((600, 300))
    overlay.set_alpha(230)
    overlay.fill((0, 0, 0))
    controls = [
        "Controls:",
        "Left Click: Select / Place buildings",
        "Right Click: Issue move, mine, repair, or attack commands",
        "P: Enter Build Mode, then press: B, F, W, T, or N",
        "S: Queue production order for selected building",
        "A: Attack command",
        "R: Repair command (with SCV selected, right-click on a damaged building)",
        "X: Upgrade weapon damage (cost 100 minerals)",
        "C: Hold to view controls"
    ]
    for i, line in enumerate(controls):
        text = font.render(line, True, (255,255,255))
        overlay.blit(text, (20, 20 + i * 32))
    surface.blit(overlay, (SCREEN_WIDTH//2 - 300, SCREEN_HEIGHT//2 - 150))

# =======================
#       MAIN SETUP
# =======================
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("RTS PvAI")
clock = pygame.time.Clock()

cam_offset = [0, 0]
waiting_for_build_key = False
build_mode = None
builder_unit = None
player_damage_multiplier = 1.0

game = Game()
player_cc = game.add_building("Command Center", 200, 200, "player", complete=True)     # Top-left
enemy_cc = game.add_building("Command Center", 2800, 2800, "enemy", complete=True)       # Bottom-right

# Generate corner mineral fields arranged in a half–circle.
# Top-left corner:
tl_corner = (250, 250)
game.player_minerals += generate_corner_minerals_half_circle(tl_corner, count=9, start_offset=100, arc_radius=150)

# Top-right corner:
tr_corner = (WORLD_WIDTH - 250, 250)
game.enemy_minerals += generate_corner_minerals_half_circle(tr_corner, count=9, start_offset=100, arc_radius=150)

# Bottom-left corner:
bl_corner = (250, WORLD_HEIGHT - 250)
game.player_minerals += generate_corner_minerals_half_circle(bl_corner, count=9, start_offset=100, arc_radius=150)

# Bottom-right corner:
br_corner = (WORLD_WIDTH - 250, WORLD_HEIGHT - 250)
game.enemy_minerals += generate_corner_minerals_half_circle(br_corner, count=9, start_offset=100, arc_radius=150)




# Add a central mineral field of 15 minerals arranged in a circle.
center = (WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
central_minerals = generate_center_minerals(center, count=15, radius=150)
game.player_minerals += central_minerals  # or add to both sides if desired

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

# =======================
#       MAIN LOOP
# =======================
running = True
game_time = 0
while running:
    dt = clock.tick(60) / 1000.0
    game_time += dt
    mx, my = pygame.mouse.get_pos()
    if mx < CAMERA_BORDER:
        cam_offset[0] = max(0, cam_offset[0] - CAMERA_SPEED * dt)
    if mx > SCREEN_WIDTH - CAMERA_BORDER:
        cam_offset[0] = min(WORLD_WIDTH - SCREEN_WIDTH, cam_offset[0] + CAMERA_SPEED * dt)
    if my < CAMERA_BORDER:
        cam_offset[1] = max(0, cam_offset[1] - CAMERA_SPEED * dt)
    if my > SCREEN_HEIGHT - CAMERA_BORDER:
        cam_offset[1] = min(WORLD_HEIGHT - SCREEN_HEIGHT, cam_offset[1] + CAMERA_SPEED * dt)
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False
            if event.key == K_x:
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
                elif event.key == K_o:
                    # Build a new Command Center.
                    # wx, wy should already be defined as the mouse position adjusted by cam_offset.
                    new_x = round(wx / TILE_SIZE) * TILE_SIZE
                    new_y = round(wy / TILE_SIZE) * TILE_SIZE
                    # Define the minimum distance: 5 tiles.
                    min_distance = 5 * TILE_SIZE
                    valid_location = True
                    for m in game.player_minerals + game.enemy_minerals:
                        if math.hypot(new_x - m.x, new_y - m.y) < min_distance:
                            valid_location = False
                            break
                    if not valid_location:
                        print("Invalid location: Command Center cannot be built within 5 tiles of a mineral!")
                        waiting_for_build_key = False
                        build_mode = None
                    elif game.resources["player"] < COST_COMMAND_CENTER:
                        print("Not enough minerals for new Command Center!")
                        waiting_for_build_key = False
                        build_mode = None
                    else:
                        game.resources["player"] -= COST_COMMAND_CENTER
                        new_cc = game.add_building("Command Center", wx, wy, "player", complete=False)
                        print("Player: Building new Command Center.")
                        waiting_for_build_key = False
                        build_mode = None

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
                if game.resources["player"] < cost:
                    print("Not enough minerals!")
                    build_mode = None
                else:
                    game.resources["player"] -= cost
                    print(f"{build_mode} build mode activated. A green preview box will appear.")
            if event.key == K_r:
                for unit in selected_units:
                    if unit.type == "SCV":
                        if game.resources["player"] >= 5:
                            unit.state = "repairing"
                            print("Repair command issued. Right-click on a damaged building.")
                        else:
                            print("Not enough minerals to repair")
            if event.key == K_s:
                for obj in selected_units:
                    if hasattr(obj, "production_queue") and obj.production_queue is not None:
                        if len(obj.production_queue) < MAX_QUEUE:
                            if obj.type == "Command Center":
                                unit_type = "SCV"
                                cost = COST_SCV
                                if game.resources["player"] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources["player"] -= cost
                            elif obj.type == "Barracks":
                                unit_type = "Marine"
                                cost = COST_MARINE
                                if game.resources["player"] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources["player"] -= cost
                            elif obj.type == "Tank Factory":
                                unit_type = "Tank"
                                cost = COST_TANK
                                if game.resources["player"] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources["player"] -= cost
                            elif obj.type == "Wraith Factory":
                                unit_type = "Wraith"
                                cost = COST_WRAITH
                                if game.resources["player"] < cost:
                                    print("Not enough minerals!")
                                    continue
                                game.resources["player"] -= cost
                            else:
                                continue
                            obj.production_queue.append(unit_type)
                            print(f"Queued {unit_type} at {obj.type} (Queue: {len(obj.production_queue)})")
            if event.key == K_x:
                if game.resources["player"] >= UPGRADE_COST:
                    game.resources["player"] -= UPGRADE_COST
                    player_damage_multiplier += 0.1
                    print(f"Upgraded weapon damage. New multiplier: {player_damage_multiplier:.1f}")
                else:
                    print("Not enough minerals for upgrade!")
            if event.key == K_a:
                attack_command_active = True
                print("Attack command active. Click on target location.")
        if event.type == MOUSEBUTTONDOWN:
            wx = event.pos[0] + cam_offset[0]
            wy = event.pos[1] + cam_offset[1]
            if event.button == 3:
                building_clicked = None
                for b in game.buildings:
                    # Use the building's grid dimensions to create the rectangle.
                    width = b.grid_dim * TILE_SIZE
                    height = b.grid_dim * TILE_SIZE
                    rect = pygame.Rect(b.x, b.y, width, height)
                    if rect.collidepoint(wx, wy) and b.owner == "player" and b.health < b.max_health:
                        building_clicked = b
                        break
                if building_clicked and selected_units:
                    for u in selected_units:
                        if u.type == "SCV":
                            u.target_building = building_clicked
                            u.state = "repairing"
                            print("SCV assigned to repair building.")
                    continue
                if selected_units:
                    if len(selected_units) > 1:
                        center_x = sum(v.x for v in selected_units) / len(selected_units)
                        center_y = sum(v.y for v in selected_units) / len(selected_units)
                        for u in selected_units:
                            offset_x = u.x - center_x
                            offset_y = u.y - center_y
                            u.state = "moving"
                            u.move_target = (wx + offset_x, wy + offset_y)
                            u.target_mineral = None
                            u.target_building = None
                    else:
                        for u in selected_units:
                            if u.type in ["SCV", "Marine", "Tank", "Wraith"]:
                                if u.state not in ["building", "repairing"]:
                                    u.state = "moving"
                                    u.move_target = (wx, wy)
                                    u.target_mineral = None
                                    u.target_building = None
                    print("Selected units moving to", (wx, wy))
            if event.button == 1:
                if build_mode is not None and builder_unit:
                    new_b = game.add_building(build_mode, wx, wy, "player", complete=False)
                    new_b.builder = builder_unit
                    builder_unit.state = "building"
                    builder_unit.target_building = new_b
                    print(f"Player {build_mode} placed at ({wx}, {wy}).")
                    build_mode = None
                    selected_units = []
                elif attack_command_active and selected_units:
                    for u in selected_units:
                        if u.type in ["Marine", "SCV", "Tank", "Wraith"]:
                            u.state = "attack_move"
                            u.move_target = (wx, wy)
                    attack_command_active = False
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
                        rect = pygame.Rect(b.x - 15, b.y - 15, 30, 30)
                        if rect.collidepoint(selection_rect.center):
                            selected_units = [b]
                            found = True
                            print(f"Selected {b.owner}'s {b.type}.")
                            break
                    if not found:
                        for u in game.units:
                            r = 10 if u.type == "SCV" else 8 if u.type == "Marine" else 5
                            if math.hypot(u.x - selection_rect.centerx, u.y - selection_rect.centery) < r:
                                if u.owner == "player":
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
        pygame.draw.line(screen, (20,20,20), (x - cam_offset[0], 0 - cam_offset[1]), (x - cam_offset[0], WORLD_HEIGHT - cam_offset[1]))
    for y in range(0, WORLD_HEIGHT, 100):
        pygame.draw.line(screen, (20,20,20), (0 - cam_offset[0], y - cam_offset[1]), (WORLD_WIDTH - cam_offset[0], y - cam_offset[1]))
    for m in game.player_minerals:
        if m.amount > 0:
            pygame.draw.circle(screen, (255,255,0), (int(m.x - cam_offset[0]), int(m.y - cam_offset[1])), 8)
    for m in game.enemy_minerals:
        if m.amount > 0:
            pygame.draw.circle(screen, (200,200,0), (int(m.x - cam_offset[0]), int(m.y - cam_offset[1])), 8)
    for drop in game.resource_drops:
        pygame.draw.circle(screen, (0,255,0), (int(drop.x - cam_offset[0]), int(drop.y - cam_offset[1])), 6)
    for b in game.buildings:
        width = b.grid_dim * TILE_SIZE
        height = b.grid_dim * TILE_SIZE
        rect = pygame.Rect(b.x - cam_offset[0], b.y - cam_offset[1], width, height)

        # Determine color based on building type and owner
        if b.type == "Command Center":
            col = (0, 0, 255) if b.owner == "player" else (255, 0, 0)
        elif b.type == "Barracks":
            col = (255, 165, 0) if b.owner == "player" else (200, 100, 0)
        elif b.type in ["Tank Factory", "Wraith Factory", "Bunker"]:
            col = (150, 150, 150) if b.owner == "player" else (100, 100, 100)
        elif b.type == "Turret":
            col = (0, 255, 255)
        else:
            col = (128, 128, 128)

        if not b.complete:
            col = (100, 100, 100)

        pygame.draw.rect(screen, col, rect)

            # --- New: For Command Centers, display production queue above its center ---
        if b.type == "Command Center" and b.production_queue is not None:
            font_small = pygame.font.SysFont(None, 20)
            prod_text = font_small.render(f"{b.production_timer:.1f}s / {len(b.production_queue)}", True, (255,255,255))
            # Calculate position: center of Command Center, then offset upward.
            text_rect = prod_text.get_rect()
            text_rect.centerx = b.x - cam_offset[0] + width // 2
            text_rect.bottom = b.y - cam_offset[1] - 5  # 5 pixels above the building
            screen.blit(prod_text, text_rect)

        # Draw health bar
        bar_w, bar_h = width, 4
        ratio = b.health / b.max_health
        pygame.draw.rect(screen, (255, 0, 0), (rect.left, rect.top - 6, bar_w, bar_h))
        pygame.draw.rect(screen, (0, 255, 0), (rect.left, rect.top - 6, int(bar_w * ratio), bar_h))

        # Draw construction progress if incomplete
        if not b.complete:
            font_mid = pygame.font.SysFont(None, 24)
            txt = font_mid.render(f"{int(b.progress)}%", True, (255, 255, 255))
            screen.blit(txt, (b.x - cam_offset[0], b.y - cam_offset[1]))

        # Highlight selected
        if b in selected_units:
            pygame.draw.rect(screen, (0, 255, 0), rect, 2)

        bar_w, bar_h = 30, 4
        ratio = b.health / b.max_health
        pygame.draw.rect(screen, (255,0,0), (rect.left, rect.top-6, bar_w, bar_h))
        pygame.draw.rect(screen, (0,255,0), (rect.left, rect.top-6, int(bar_w*ratio), bar_h))
        if not b.complete:
            font_mid = pygame.font.SysFont(None, 24)
            txt = font_mid.render(f"{int(b.progress)}%", True, (255,255,255))
            screen.blit(txt, (b.x-15-cam_offset[0], b.y-15-cam_offset[1]))
        if b in selected_units:
            pygame.draw.rect(screen, (0,255,0), rect, 2)
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
        s_rect = pygame.Rect(selection_rect.left - cam_offset[0], selection_rect.top - cam_offset[1], selection_rect.width, selection_rect.height)
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
        elif event.key == K_o:
            # Build a new Command Center.
            new_x = round(wx / TILE_SIZE) * TILE_SIZE
            new_y = round(wy / TILE_SIZE) * TILE_SIZE
            # Minimum allowed distance is 5 tiles (5 * TILE_SIZE).
            min_distance = 5 * TILE_SIZE
            valid_location = True
            for m in game.player_minerals + game.enemy_minerals:
                if math.hypot(new_x - m.x, new_y - m.y) < min_distance:
                    valid_location = False
                    break
            if not valid_location:
                print("Invalid location: Command Center cannot be built within 5 tiles of a mineral!")
                waiting_for_build_key = False
                build_mode = None
            elif game.resources["player"] < COST_COMMAND_CENTER:
                print("Not enough minerals for new Command Center!")
                waiting_for_build_key = False
                build_mode = None
            else:
                game.resources["player"] -= COST_COMMAND_CENTER
                new_cc = game.add_building("Command Center", wx, wy, "player", complete=False)
                print("Player: Building new Command Center.")
                waiting_for_build_key = False
                build_mode = None

        if letter:
            txt = font_mid.render(letter, True, (0,255,0))
            screen.blit(txt, (mx2 - 10, my2 - 12))
    font = pygame.font.SysFont(None, 32)
    res_text = font.render(f"Player Minerals: {game.resources['player']}", True, (255,255,255))
    screen.blit(res_text, (10, 10))
    selected_counts = {"M":0, "S":0, "T":0, "W":0}
    for u in selected_units:
        if hasattr(u, "type"):
            if u.type == "Marine":
                selected_counts["M"] += 1
            elif u.type == "SCV":
                selected_counts["S"] += 1
            elif u.type == "Tank":
                selected_counts["T"] += 1
            elif u.type == "Wraith":
                selected_counts["W"] += 1
    troop_text = font.render(f"(Selected Troops: {selected_counts['M']}M {selected_counts['S']}S {selected_counts['T']}T {selected_counts['W']}W)", True, (255,255,255))
    screen.blit(troop_text, (10, 50))
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
