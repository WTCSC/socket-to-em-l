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

    def render(self, camera, screen):
        super().render(camera, screen)
        pygame.draw.rect(screen, (255, 0, 0), self.rect, 2)

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
        damage = random.randint(40, 50)
        bullet = Troop("imgs/b1.png", (self.position.x, self.position.y), 1, speed, damage, 0)
        bullet.scale((.5, .5))
        bullets.append(bullet)
        bullet.enemy_target = self.enemy_target
        

class Game:
    def __init__(self):
        self.game_objects: dict[str, list[GameObject]] = {}

def get_camera_position(camera: Vector2, world_size: tuple, screen_size: tuple) -> tuple:
    camera_x = max(0, min(camera.x, world_size[0] - screen_size[0]))
    camera_y = max(0, min(camera.y, world_size[1] - screen_size[1]))
    return Vector2(camera_x, camera_y)

def barraks_troop_spawn(mouse_pos: tuple, camera: Vector2, building_barracks: list[Building]) -> Building | None:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    for barrack in building_barracks:
        if barrack.rect.collidepoint(cam_offset.x, cam_offset.y):
            bgreen = Indicator('imgs/green.png')
            bgreen.scale((.15, .15))
            bgreens.append(bgreen)
            return barrack
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
            red = Indicator('imgs/red.png')
            red.scale((.15, .15))
            reds.append(red)
            return enemy_troop
    return None

def main():
    # Initialize pygame
    pygame.init()

    screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN | pygame.SCALED)
    GLOBAL_SCALE = (.25, .25)

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

    # Load game objects
    starship_grey = Troop('imgs/black_ship.png', (600, 450), 700, 2, int(200-250))
    starship_grey.scale(GLOBAL_SCALE)

    starship_red = Troop('imgs/red_ship.png', (600, 1000), 700, 2, int(70-80))
    starship_red.scale(GLOBAL_SCALE)

    command_center = Building('imgs/command_center.png', (100, 100), 2000)
    command_center.scale((.5, .5))

    starport = Building('imgs/starport.png', (150, 450), 750)
    starport.scale((.65, .65))

    depot = Building('imgs/vehicle_depot.png', (445, 450), 1250)
    depot.scale((.3, .3))

    red_troop = Troop('imgs/red_soildger.png', (1200, 700), 150, 10, int(40-50))
    red_troop.scale(GLOBAL_SCALE)

    blue_troop = Troop('imgs/blue_soildger.png', (300, 200), 150, 10, int(40-50))
    blue_troop.scale(GLOBAL_SCALE)

    troop = None
    selected_building = None
    enemy_troop = None
    troops = [red_troop, starship_red]
    global bullets
    bullets = []
    global greens
    greens = []
    global bgreens
    bgreens = []
    global reds
    reds = []
    global enemy_troops
    enemy_troops = []
    global building_barracks
    building_barracks = []

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
                selected_building = barraks_troop_spawn(pygame.mouse.get_pos(), camera, building_barracks)


            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                troop = select_troop(pygame.mouse.get_pos(), camera, troops, troop)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if troop == red_troop:
                    cam_pos = get_camera_position(camera, world_size, screen_size)
                    red_troop.target = Vector2(mouse_pos[0], mouse_pos[1]) + cam_pos

                elif troop == starship_red:
                    cam_pos = get_camera_position(camera, world_size, screen_size)
                    starship_red.target = Vector2(mouse_pos[0], mouse_pos[1]) + cam_pos

            # Camera movement
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
                    building_barracks.append(barracks)

        # Render background tiles
        for pos in background_tiles:
            screen.blit(background.surf, (pos[0] - camera.x, pos[1] - camera.y))

        red_troop.move(camera, screen)
        blue_troop.move(camera, screen)
        starship_grey.move(camera, screen)
        starship_red.move(camera, screen)

        for blue_tank in enemy_troops:
            blue_tank.move(camera, screen)
            blue_tank.render(camera, screen)

        for barracks in building_barracks:
            barracks.render(camera, screen)

        for bullet in bullets:
            bullet.move(camera, screen)
            bullet.render(camera, screen)

        for bgreen in bgreens:
            if selected_building:
                screen.blit(bgreen.surf, (selected_building.rect.midbottom[0] - camera.x - bgreen.rect.width // 2, selected_building.rect.midbottom[1] - camera.y))


        for green in greens:
            if troop:
                screen.blit(green.surf, (troop.rect.midbottom[0] - camera.x - green.rect.width // 2, troop.rect.midbottom[1] - camera.y))


        # Render objects
        command_center.render(camera, screen)
        starport.render(camera, screen)
        depot.render(camera, screen)
        red_troop.render(camera, screen)
        blue_troop.render(camera, screen)
        #blue_tank.render(camera, screen)
        starship_grey.render(camera, screen)
        starship_red.render(camera, screen)

        pygame.display.update()
        clock.tick(60)

if __name__ == "__main__":
    main()