import pygame
import time
import random
from math import sqrt
from sys import exit

class Vector2:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.length = sqrt((x ** 2) + (y ** 2))

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
    def __init__(self, sprite: str, position: tuple | Vector2, owner: int = 0):
        self.sprite = sprite
        if isinstance(position, tuple):
            self.position = Vector2(position[0], position[1])
        else:
            self.position = position
        self.owner = owner
        self.surf = pygame.image.load(self.sprite)
        self.rect = self.surf.get_rect(topleft=tuple(self.position))
    
    def render(self, camera, screen):
        screen.blit(self.surf, (self.rect.x - camera.x, self.rect.y - camera.y))
    
    def scale(self, factor: tuple):
        self.surf = pygame.transform.scale(self.surf, (self.rect.width * factor[0], self.rect.height * factor[1]))
        self.rect.size = (self.surf.get_width(), self.surf.get_height())

    def size(self, size: tuple):
        self.surf = pygame.transform.scale(self.surf, size)
        self.rect.size = (self.surf.get_width(), self.surf.get_height())

class Indicator(GameObject):
    def __init__(self, sprite: str, position: tuple = (0, 0)):
        super().__init__(sprite, position)

class Building(GameObject):
    def __init__(self, sprite: str, position: tuple, max_health: int):
        super().__init__(sprite, position)
        self.max_health = max_health
        self.health = max_health
        self.indicator = None

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
        self.indicator = None

    def stop(self):
        self.velocity = Vector2(0, 0)

    def move(self, camera, screen):
        if self.enemy_target:
            distance_to_target = (self.position - self.enemy_target.position).length

            if distance_to_target <= self.sight_range:
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
            distance_to_target = (self.position - self.target).length
            if distance_to_target <= self.speed:
                self.stop()
            else:
                self.goto(self.target)

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
        

def get_camera_position(camera: Vector2, world_size: tuple, screen_size: tuple) -> tuple:
    camera_x = max(0, min(camera.x, world_size[0] - screen_size[0]))
    camera_y = max(0, min(camera.y, world_size[1] - screen_size[1]))
    return Vector2(camera_x, camera_y)

def barraks_troop_spawn(mouse_pos: tuple, camera: Vector2, buildings: list[Building]) -> Building | None:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for barracks in buildings:
        if barracks.rect.collidepoint(cam_offset.x, cam_offset.y):
            bgreen = Indicator('imgs/green.png')
            bgreen.scale((.15, .15))
            bgreens.append(bgreen)
            return barracks
    return None

def depot_troop_spawn(mouse_pos: tuple, camera: Vector2, buildings: list[Building]) -> Building | None:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for depot in buildings:
        if depot.rect.collidepoint(cam_offset.x, cam_offset.y):
            bgreen = Indicator('imgs/green.png')
            bgreen.scale((.15, .15))
            bgreens.append(bgreen)
            return depot
    return None

def starport_troop_spawn(mouse_pos: tuple, camera: Vector2, buildings: list[Building]) -> Building | None:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for starport in buildings:
        if starport.rect.collidepoint(cam_offset.x, cam_offset.y):
            bgreen = Indicator('imgs/green.png')
            bgreen.scale((.15, .15))
            bgreens.append(bgreen)
            return starport
    return None

def select_troop(mouse_pos: tuple, camera: Vector2, troops: list[Troop], troop: Troop = None) -> Troop:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for troop in troops:
        if troop.rect.collidepoint(cam_offset.x, cam_offset.y):
            green = Indicator('imgs/green.png')
            green.scale((.15, .15))
            greens.append(green)
            return troop
    return None

def select_enemy_troop(mouse_pos: tuple, camera: Vector2, enemy_troops: list[Troop], enemy_troop: Troop = None) -> Troop:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for enemy_troop in enemy_troops:
        if enemy_troop.rect.collidepoint(cam_offset.x, cam_offset.y):
            return enemy_troop
    return None

def main(game: dict[str, list[GameObject]], player: str):
    # Initialize pygame
    pygame.init()

    screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN | pygame.SCALED)

    # Camera setup
    camera = Vector2(0, 0)
    camera_speed = 30

    # Load background
    background = GameObject('imgs/background_grid.png', (0, 0))
    background.size((3000, 2000))

    # Define background tiling positions
    background_tiles = [
        (0, 0), (3000, 0),
        (0, 2000), (3000, 2000)
    ]

    # Make the other player the other player
    other_player = "p2" if player == "p1" else "p1"

    troop = None
    selected_building = None
    enemy_troop = None
    global troops
    troops = game[f"{player}_troops"]
    global bullets
    bullets = game["bullets"]
    global greens
    greens = []
    global bgreens
    bgreens = []
    global enemy_troops
    enemy_troops = game[f"{other_player}_troops"]
    global buildings
    buildings = game[f"{player}_buildings"]
    global enemy_buildings
    enemy_buildings = game[f"{other_player}_buildings"]

    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            mouse_pos = pygame.mouse.get_pos()
            world_size = (background.rect.width * 2, background.rect.height * 2)
            screen_size = screen.get_size()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                selected_building = barraks_troop_spawn(pygame.mouse.get_pos(), camera, buildings)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                selected_building = depot_troop_spawn(pygame.mouse.get_pos(), camera, buildings)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                selected_building = starport_troop_spawn(pygame.mouse.get_pos(), camera, buildings)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                troop = select_troop(pygame.mouse.get_pos(), camera, troops, troop)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    cam_pos = get_camera_position(camera, world_size, screen_size)
                    troop.target = Vector2(mouse_pos[0], mouse_pos[1]) + cam_pos

            keys = pygame.key.get_pressed()

            if keys[pygame.K_w]:  # Move up
                camera.y = max(camera.y - camera_speed, 0)
            if keys[pygame.K_s]:  # Move down
                camera.y = min(camera.y + camera_speed, (background.rect.height * 2) - screen.get_height())
            if keys[pygame.K_a]:  # Move left
                camera.x = max(camera.x - camera_speed, 0)
            if keys[pygame.K_d]:  # Move right
                camera.x = min(camera.x + camera_speed, (background.rect.width * 2) - screen.get_width())
            if keys[pygame.K_u]:
                troop = None
            if keys[pygame.K_c] and troop in troops:
                selected_enemy_troop = select_enemy_troop(pygame.mouse.get_pos(), camera, enemy_troops, enemy_troop)
                if selected_enemy_troop:
                    troop.enemy_target = selected_enemy_troop
            if keys[pygame.K_ESCAPE]:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                if isinstance(selected_building, Building):
                    spawn_x = selected_building.rect.right + 20
                    spawn_y = selected_building.rect.centery
                    red_troop = Troop('imgs/red_soildger.png', (spawn_x, spawn_y), 150, 10, int(40-50))
                    red_troop.scale(GLOBAL_SCALE)
                    troops.append(red_troop)

            if event.type == pygame.KEYDOWN:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_t]:
                    blue_tank = Troop('imgs/blue_tank.png', (1000, 400), 60, 10, int(150-180))
                    blue_tank.scale((.2, .2))
                    enemy_troops.append(blue_tank)

            if event.type == pygame.KEYDOWN:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_b]:
                    barracks = Building('imgs/barracks.png', (450, 185), 1000)
                    barracks.scale((.29, .29))
                    buildings.append(barracks)
                    starport = starport = Building('imgs/starport.png', (150, 450), 750)
                    starport.scale((.65, .65))
                    buildings.append(starport)
                    depot = Building('imgs/vehicle_depot.png', (445, 450), 1250)
                    depot.scale((.3, .3))
                    buildings.append(depot)

        # Render background tiles
        for pos in background_tiles:
            screen.blit(background.surf, (pos[0] - camera.x, pos[1] - camera.y))

        for red_troop in troops:
            red_troop.move(camera, screen)
            red_troop.render(camera, screen)

        for blue_tank in enemy_troops:
            blue_tank.move(camera, screen)
            blue_tank.render(camera, screen)

        for barracks in buildings:
            barracks.render(camera, screen)

        for starport in buildings:
            starport.render(camera, screen)

        for depot in buildings:
            depot.render(camera, screen)

        for bullet in bullets:
            bullet.move(camera, screen)
            bullet.render(camera, screen)

        for bgreen in bgreens:
            if selected_building:
                screen.blit(bgreen.surf, (selected_building.rect.midbottom[0] - camera.x - bgreen.rect.width // 2, selected_building.rect.midbottom[1] - camera.y))

        if troop is None:
            greens.clear()

        for green in greens:
            screen.blit(green.surf, (troop.rect.midbottom[0] - camera.x - green.rect.width // 2, troop.rect.midbottom[1] - camera.y))

        pygame.display.update()
        clock.tick(60)

if __name__ == "__main__":
    main()