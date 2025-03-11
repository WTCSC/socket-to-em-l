import pygame
import time
import random
from math import sqrt
from sys import exit

class Vector2:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.length = sqrt(x**2 + y**2)

    def normalize(self):
        return Vector2(self.x / self.length, self.y / self.length) if self.length > 0 else Vector2(0, 0)
    
    def __iter__(self):
        yield self.x
        yield self.y
    
    def __mul__(self, num: float):
        return Vector2(self.x * num, self.y * num)
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __str__(self):
        return f"({self.x}, {self.y})"

    __rmul__ = __mul__

class GameObject:
    def __init__(self, sprite: str, position: tuple | Vector2, owner: int = 0, size: Vector2 | None = None):
        self.sprite = sprite
        if isinstance(position, tuple):
            self.position = Vector2(position[0], position[1])
        else:
            self.position = position
        self.owner = owner
        self.surf = pygame.image.load(self.sprite)
        self.rect = self.surf.get_rect(topleft=tuple(self.position))
        if size is not None:
            self.size = size
        else:
            self.size = Vector2(*self.rect.size)
    
    def render(self, camera, screen):
        screen.blit(self.surf, (self.rect.x - camera.x, self.rect.y - camera.y))
    
    def scale(self, factor: tuple):
        self.surf = pygame.transform.scale(
            self.surf, 
            (int(self.rect.width * factor[0]), int(self.rect.height * factor[1]))
        )
        self.size = Vector2(self.surf.get_width(), self.surf.get_height())
        self.rect.size = tuple(self.size)

    def resize(self, size: tuple):
        self.surf = pygame.transform.scale(self.surf, size)
        self.size = Vector2(self.surf.get_width(), self.surf.get_height())
        self.rect.size = tuple(self.size)

class Indicator(GameObject):
    def __init__(self, sprite: str, position: tuple = (0, 0)):
        super().__init__(sprite, position)

class Mineral(GameObject):
    def __init__(self, sprite: str, position: tuple, crystal_limit: int):
        super().__init__(sprite, position)
        self.crystal_limit = crystal_limit

class Building(GameObject):
    def __init__(self, sprite: str, position: tuple, max_health: int):
        super().__init__(sprite, position)
        self.max_health = max_health
        self.health = max_health

class Troop(GameObject):
    def __init__(self, sprite: str, position: tuple, max_health: int, speed: int, damage: int, sight_range: int = 250, shot_cooldown: int = 1):
        super().__init__(sprite, position)
        self.max_health = max_health
        self.health = max_health
        self.speed = speed
        self.damage = damage
        self.velocity = Vector2(0, 0)
        self.target: Vector2 | None = None
        self.enemy_target: Troop | None = None
        self.sight_range = sight_range
        self.shot_cooldown = shot_cooldown
        self.time_since_shot = 0

    def stop(self):
        self.velocity = Vector2(0, 0)

    def move(self, camera, screen):
        # Enemy targeting
        if self.enemy_target:
            distance_to_enemy = (self.position - self.enemy_target.position).length
            if distance_to_enemy <= self.sight_range:
                if time.time() - self.time_since_shot > self.shot_cooldown:
                    self.projectile()
                    self.time_since_shot = time.time()
                self.stop()
                self.target = None
            else:
                self.target = self.enemy_target.position

            if self.rect.colliderect(self.enemy_target.rect):
                bullets.remove(self)
                if self.enemy_target.health > 0:
                    self.enemy_target.health -= self.damage
                if self.enemy_target.health <= 0:
                    enemy_troops.remove(self.enemy_target)
            elif self.enemy_target.health <= 0:
                self.enemy_target = None

        if self.target:
            if isinstance(self.target, Building):
                target_position = self.target.position
            else:
                target_position = self.target
            distance_to_target = (self.position - target_position).length
            if distance_to_target <= self.speed:
                self.stop()
            else:
                self.goto(target_position)
            self.position.x += self.velocity.x
            self.position.y += self.velocity.y
            self.rect.topleft = (self.position.x, self.position.y)

    def goto(self, position: Vector2):
        direction = Vector2(position.x - self.position.x, position.y - self.position.y)
        self.velocity = direction.normalize() * self.speed

    def projectile(self):
        speed = 50
        damage = self.damage
        bullet = Troop("imgs/b1.png", (self.position.x, self.position.y), 1, speed, damage, 0)
        bullet.scale((.5, .5))
        bullets.append(bullet)
        bullet.enemy_target = self.enemy_target

class Collector(Troop):
    def __init__(self, sprite: str, position: tuple, max_health: int, speed: int, damage: int, command_center: Building, mineral_target: Mineral, collect_duration=4, collection_amount=10, **kwargs):
        super().__init__(sprite, position, max_health, speed, damage, **kwargs)
        self.state = "idle"
        self.manual_override = False
        self.manual_target = None
        self.timer = 0
        self.command_center = command_center  # Where the collector returns.
        self.mineral_target = mineral_target  # The mineral to mine.
        self.collect_duration = collect_duration  # Seconds to wait at the mineral.
        self.collection_amount = collection_amount  # Amount collected each cycle.

    def update(self):
        self.target = self.manual_target
        if (self.position - self.manual_target).length < 5:
            self.manual_override = False
            self.state = "idle"
            return

        if self.state == "idle":
            self.stop()

        elif self.state == "to_mineral":
            self.target = self.mineral_target.position
            if self.rect.colliderect(self.mineral_target.rect):
                self.state = "collecting"
                self.timer = time.time() + self.collect_duration
                self.stop()
        elif self.state == "collecting":
            if time.time() >= self.timer:
                # Collect resources:
                self.mineral_target.crystal_limit -= self.collection_amount
                if self.mineral_target.crystal_limit < 0:
                    self.mineral_target.crystal_limit = 0
                # Now return to command center.
                self.state = "to_command"
                self.target = self.command_center.position
        elif self.state == "to_command":
            self.target = self.command_center.position
            if self.rect.colliderect(self.command_center.rect):
                if self.mineral_target.crystal_limit > 0:
                    # Resume mining if resource is still available.
                    self.state = "to_mineral"
                else:
                    self.state = "idle"
                    self.target = None

        if self.target:
            self.goto(self.target)
            self.position.x += self.velocity.x
            self.position.y += self.velocity.y
            self.rect.topleft = (self.position.x, self.position.y)

    def __init__(self, sprite: str, position: tuple, max_health: int, speed: int, damage: int, command_center: Building, mineral_target: Mineral, collect_duration=4, collection_amount=10, **kwargs):
        super().__init__(sprite, position, max_health, speed, damage, **kwargs)
        self.state = "idle"
        self.timer = 0
        self.command_center = command_center
        self.mineral_target = mineral_target
        self.collect_duration = collect_duration
        self.collection_amount = collection_amount

    def update(self):
        if self.state == "idle":
            self.mineral_target = None

        elif self.state == "to_mineral":
            self.target = self.mineral_target.position
            if self.rect.colliderect(self.mineral_target.rect):
                self.state = "collecting"
                self.timer = time.time() + self.collect_duration
                self.stop()
        
        elif self.state == "collecting":
            # Wait until 4 seconds have passed.
            if time.time() >= self.timer:
                # Deduct the collected amount from the mineral.
                self.mineral_target.crystal_limit -= self.collection_amount
                if self.mineral_target.crystal_limit < 0:
                    self.mineral_target.crystal_limit = 0
                # Switch state: now return to the command center.
                self.state = "to_command"
                self.target = self.command_center.position
        
        elif self.state == "to_command":
            # Move toward the command center.
            if self.rect.colliderect(self.command_center.rect):
                # Arrived at the command center.
                if self.mineral_target.crystal_limit > 0:
                    self.state = "to_mineral"
                else:
                    self.state = "idle"
                    self.target = None

        # Update movement based on the target.
        if self.target:
            self.goto(self.target)
            self.position.x += self.velocity.x
            self.position.y += self.velocity.y
            self.rect.topleft = (self.position.x, self.position.y)

def get_camera_position(camera: Vector2, world_size: tuple, screen_size: tuple) -> Vector2:
    camera_x = max(0, min(camera.x, world_size[0] - screen_size[0]))
    camera_y = max(0, min(camera.y, world_size[1] - screen_size[1]))
    return Vector2(camera_x, camera_y)

def select_mineral(mouse_pos: tuple, camera: Vector2, minerals: list[GameObject]) -> GameObject | None:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for mineral in minerals:
        if mineral.rect.collidepoint(cam_offset.x, cam_offset.y):
            return mineral
    return None

selected_objects = []

def select_objects(mouse_pos: tuple, camera: Vector2, troops: list[Troop], buildings: list[Building]) -> list[GameObject]:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    candidates = []
    for building in buildings:
        if building.rect.collidepoint(cam_offset.x, cam_offset.y):
            candidates.append(building)
    for troop in troops:
        if troop.rect.collidepoint(cam_offset.x, cam_offset.y):
            candidates.append(troop)
    return candidates

def select_enemy_troop(mouse_pos: tuple, camera: Vector2, enemy_troops: list[Troop]) -> Troop | None:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for enemy_troop in enemy_troops:
        if enemy_troop.rect.collidepoint(cam_offset.x, cam_offset.y):
            return enemy_troop
    return None

def check_collector_mineral_collisions(collectors: list[Troop], minerals: list[Mineral]) -> list[tuple[Troop, Mineral]]:
    collisions = []
    for collector in collectors:
        if collector.sprite == 'imgs/collector.png':
            for mineral in minerals:
                if collector.rect.colliderect(mineral.rect):
                    collisions.append((collector, mineral))
    return collisions

def main(game: dict, player: str):
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN | pygame.SCALED)
    GLOBAL_SCALE = (.25, .25)

    camera = Vector2(0, 0)
    camera_speed = 30

    background = GameObject('imgs/background_grid.png', (0, 0))
    background.resize((3000, 2000))
    background_tiles = [(0, 0), (3000, 0), (0, 2000), (3000, 2000)]

    other_player = "p2" if player == "p1" else "p1"

    mineral1 = Mineral('imgs/mineral.png', (90, 90), random.randint(1000, 2000))
    mineral1.scale((.5, .5))

    mineral2 = Mineral('imgs/mineral.png', (50, 150), random.randint(1000, 2000))
    mineral2.scale((.5, .5))

    mineral3 = Mineral('imgs/mineral.png', (160, 50), random.randint(1000, 2000))
    mineral3.scale((.5, .5))

    mineral4 = Mineral('imgs/mineral.png', (40, 210), random.randint(1000, 2000))
    mineral4.scale((.5, .5))

    mineral5 = Mineral('imgs/mineral.png', (230, 35), random.randint(1000, 2000))
    mineral5.scale((.5, .5))

    mineral6 = Mineral('imgs/mineral.png', (30, 270), random.randint(1000, 2000))
    mineral6.scale((.5, .5))

    mineral7 = Mineral('imgs/mineral.png', (300, 25), random.randint(1000, 2000))
    mineral7.scale((.5, .5))

    mineral8 = Mineral('imgs/mineral.png', (20, 330), random.randint(1000, 2000))
    mineral8.scale((.5, .5))

    mineral9 = Mineral('imgs/mineral.png', (370, 20), random.randint(1000, 2000))
    mineral9.scale((.5, .5))

    starship_grey = Troop('imgs/black_ship.png', (600, 450), 700, 2, random.randint(80, 100))
    starship_grey.scale(GLOBAL_SCALE)

    blue_troop = Troop('imgs/blue_soildger.png', (300, 200), 150, 10, random.randint(40, 50))
    blue_troop.scale(GLOBAL_SCALE)

    global selected_objects, troops, enemy_troops, bullets, buildings, enemy_buildings, rallys, minerals
    troops = game[f"{player}_troops"]
    enemy_troops = game[f"{other_player}_troops"]
    bullets = game[f"{player}_bullets"]
    enemy_bullets = game[f"{other_player}_bullets"]
    buildings = game[f"{player}_buildings"]
    enemy_buildings = game[f"{other_player}_buildings"]
    rallys = []
    rally = None
    minerals = [mineral1, mineral2, mineral3, mineral4, mineral5, mineral6, mineral7, mineral8, mineral9]
    mineral_count = 1000000
    troop_limit = 0

    clock = pygame.time.Clock()
    while True:
        mouse_pos = pygame.mouse.get_pos()
        world_size = (background.rect.width * 2, background.rect.height * 2)
        screen_size = screen.get_size()
        cam_pos = get_camera_position(camera, world_size, screen_size)

        # Flags to track right-click actions:
        collector_selected = False

        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            # Mouse events
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click: selection
                    keys = pygame.key.get_pressed()
                    if not (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]):
                        selected_objects.clear()
                    new_selections = select_objects(mouse_pos, camera, troops, buildings)
                    for obj in new_selections:
                        if obj not in selected_objects:
                            selected_objects.append(obj)

                elif event.button == 3:  # Right click
                    cam_pos = get_camera_position(camera, world_size, screen_size)
                    # If a building is selected, set a rally point and command troops.
                    building_selected = next((obj for obj in selected_objects if isinstance(obj, Building)), None)
                    mineral_clicked = select_mineral(mouse_pos, camera, minerals)
                    if collector_selected and mineral_clicked:
                        for obj in selected_objects:
                            if isinstance(obj, Collector):
                                obj.set_manual_target(move_target)
                            elif isinstance(obj, Troop):
                                obj.target = move_target
                    elif building_selected:
                        rally = Vector2(mouse_pos[0], mouse_pos[1]) + cam_pos
                        rallys.clear()
                        flag = Building('imgs/rally.png', (rally.x, rally.y), 1)
                        flag.scale((.2, .2))
                        rallys.append(flag)
                        for obj in selected_objects:
                            if isinstance(obj, Troop):
                                obj.target = rally
                    else:
                        move_target = Vector2(mouse_pos[0], mouse_pos[1]) + cam_pos
                        for obj in selected_objects:
                            if isinstance(obj, Troop):
                                obj.target = move_target


            # KEYDOWN events
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    # Spawn troops from selected buildings using the rally point (if set)
                    for obj in selected_objects:
                        if isinstance(obj, Building):
                            spawn_x = obj.rect.right + random.randint(10, 40)
                            spawn_y = obj.rect.centery + random.randint(-80, 80)
                            if obj.sprite == 'imgs/barracks.png':
                                if rally is not None:
                                    if troop_limit <= 48 and mineral_count >= 50:
                                        mineral_count -= 50
                                        new_troop = Troop('imgs/red_soildger.png', (spawn_x, spawn_y), 150, 10, random.randint(30, 40))
                                        new_troop.scale(GLOBAL_SCALE)
                                        new_troop.target = rally
                                        troop_limit += 2
                                        troops.append(new_troop)
                                    else:
                                        print("Troop limit reached" if troop_limit > 48 else "Not enough minerals")
                                else:
                                    if troop_limit <= 48 and mineral_count >= 50:
                                        mineral_count -= 50
                                        new_troop = Troop('imgs/red_soildger.png', (spawn_x, spawn_y), 150, 10, random.randint(30, 40))
                                        new_troop.scale(GLOBAL_SCALE)
                                        troop_limit += 2
                                        troops.append(new_troop)
                                    else:
                                        print("Troop limit reached" if troop_limit > 48 else "Not enough minerals")
                            elif obj.sprite == 'imgs/command_center.png':
                                if rally is not None:
                                    if troop_limit <= 49 and mineral_count >= 50:
                                        mineral_count -= 50
                                        mineral_target = None
                                        new_collector = Collector('imgs/collector.png', (spawn_x, spawn_y), 150, 5, random.randint(30, 40), command_center, mineral_target)
                                        new_collector.scale((.12, .12))
                                        new_collector.target = rally
                                        troop_limit += 1
                                        troops.append(new_collector)
                                    else:
                                        print("Troop limit reached" if troop_limit > 49 else "Not enough minerals")
                                else:
                                    if troop_limit <= 49 and mineral_count >= 50:
                                        mineral_count -= 50
                                        mineral_target = None
                                        new_collector = Collector('imgs/collector.png', (spawn_x, spawn_y), 150, 5, random.randint(30, 40), command_center, mineral_target)
                                        new_collector.scale((.12, .12))
                                        troop_limit += 1
                                        troops.append(new_collector)
                                    else:
                                        print("Troop limit reached" if troop_limit > 49 else "Not enough minerals")
                            elif obj.sprite == 'imgs/starport.png':
                                if rally is not None:
                                    if troop_limit <= 46 and mineral_count >= 250:
                                        mineral_count -= 250
                                        new_ship = Troop('imgs/red_ship.png', (spawn_x, spawn_y), 700, 2, random.randint(80, 100))
                                        new_ship.scale(GLOBAL_SCALE)
                                        new_ship.target = rally
                                        troop_limit += 6
                                        troops.append(new_ship)
                                    else:
                                        print("Troop limit reached" if troop_limit > 44 else "Not enough minerals")
                                else:
                                    if troop_limit <= 44 and mineral_count >= 250:
                                        mineral_count -= 250
                                        new_ship = Troop('imgs/red_ship.png', (spawn_x, spawn_y), 700, 2, random.randint(80, 100))
                                        new_ship.scale(GLOBAL_SCALE)
                                        troop_limit += 6
                                        troops.append(new_ship)
                                    else:
                                        print("Troop limit reached" if troop_limit > 44 else "Not enough minerals")
                            elif obj.sprite == 'imgs/vehicle_depot.png':
                                if rally is not None:
                                    if troop_limit <= 46 and mineral_count >= 150:
                                        mineral_count -= 150
                                        new_tank = Troop('imgs/red_tank.png', (spawn_x, spawn_y), 400, 4, random.randint(50, 70))
                                        new_tank.scale((.15, .15))
                                        new_tank.target = rally
                                        troop_limit += 4
                                        troops.append(new_tank)
                                    else:
                                        print("Troop limit reached" if troop_limit > 46 else "Not enough minerals")
                                else:
                                    if troop_limit <= 46 and mineral_count >= 150:
                                        mineral_count -= 150
                                        new_tank = Troop('imgs/red_tank.png', (spawn_x, spawn_y), 400, 4, random.randint(50, 70))
                                        new_tank.scale((.15, .15))
                                        troop_limit += 4
                                        troops.append(new_tank)
                                    else:
                                        print("Troop limit reached" if troop_limit > 46 else "Not enough minerals")

                elif event.key == pygame.K_t:
                    blue_tank = Troop('imgs/blue_tank.png', (1000, 400), 60, 10, random.randint(150, 180))
                    blue_tank.scale((.2, .2))
                    enemy_troops.append(blue_tank)
                elif event.key == pygame.K_b:
                    barracks = Building('imgs/barracks.png', (650, 385), 1000)
                    barracks.scale((.29, .29))
                    buildings.append(barracks)
                    starport = Building('imgs/starport.png', (350, 650), 750)
                    starport.scale((.65, .65))
                    buildings.append(starport)
                    depot = Building('imgs/vehicle_depot.png', (645, 650), 1250)
                    depot.scale((.3, .3))
                    buildings.append(depot)
                    command_center = Building('imgs/command_center.png', (300, 300), 2000)
                    command_center.scale((.5, .5))
                    buildings.append(command_center)

        # Continuous key presses (camera, clearing selection, enemy targeting)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            camera.y = max(camera.y - camera_speed, 0)
        if keys[pygame.K_s]:
            camera.y = min(camera.y + camera_speed, (background.rect.height * 2) - screen.get_height())
        if keys[pygame.K_a]:
            camera.x = max(camera.x - camera_speed, 0)
        if keys[pygame.K_d]:
            camera.x = min(camera.x + camera_speed, (background.rect.width * 2) - screen.get_width())
        if keys[pygame.K_ESCAPE]:
            pygame.quit()
            exit()
        if keys[pygame.K_u]:
            selected_objects.clear()
        if keys[pygame.K_c]:
            selected_enemy = select_enemy_troop(mouse_pos, camera, enemy_troops)
            if selected_enemy:
                for obj in selected_objects:
                    if isinstance(obj, Troop):
                        obj.enemy_target = selected_enemy

        # Rendering
        for pos in background_tiles:
            screen.blit(background.surf, (pos[0] - camera.x, pos[1] - camera.y))
        for building in buildings:
            building.render(camera, screen)
        for building in enemy_buildings:
            building.render(camera, screen)
        for obj in minerals:
            obj.render(camera, screen)
        for enemy in enemy_troops:
            enemy.move(camera, screen)
            enemy.render(camera, screen)
        for troop in troops:
            if isinstance(troop, Collector):
                troop.update()
            troop.move(camera, screen)
            troop.render(camera, screen)
        for bullet in bullets + enemy_bullets:
            bullet.move(camera, screen)
            bullet.render(camera, screen)
        for flag in rallys:
            flag.render(camera, screen)
        for obj in selected_objects:
            indicator = Indicator('imgs/green.png')
            indicator.scale((.15, .15))
            screen.blit(indicator.surf, (obj.rect.midbottom[0] - camera.x - indicator.rect.width // 2, obj.rect.midbottom[1] - camera.y))

        pygame.display.update()
        clock.tick(60)

if __name__ == "__main__":
    game = {
        "p1_troops": [],
        "p2_troops": [],
        "p1_bullets": [],
        "p2_bullets": [],
        "p1_buildings": [],
        "p2_buildings": []
    }
    main(game, "p1")