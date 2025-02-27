import pygame
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
    def __init__(self, sprite: str, position: tuple):
        self.sprite = sprite
        self.position = Vector2(position[0], position[1])
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

class Troop(GameObject):
    def __init__(self, sprite: str, position: tuple, max_health: int, speed: int, damage: int):
        super().__init__(sprite, position)
        self.max_health = max_health
        self.health = max_health
        self.speed = speed
        self.damage = damage
        self.velocity = Vector2(0, 0)
        self.target: Vector2 | None = None
        self.is_targeting_enemy = False
        self.enemy_target = None
        self.b1_image = GameObject('imgs/b1.png', (0, 0))  # Example image, adjust path as needed.
        self.b1_image.scale((0.15, 0.15))  # Adjust size if necessary
        self.b1_speed = 50  # Set the speed for the b1 image.

    def stop(self):
        self.velocity = Vector2(0, 0)

    def move(self, camera, screen):
        if self.target:
            if self.is_targeting_enemy:
                distance_to_target = (self.position - self.enemy_target.position).length
                if distance_to_target <= 250:
                    # Show the b1 image when the troop is within range
                    self.b1_image.position = self.enemy_target.position  # Set the position of b1 near the enemy
                    self.b1_image.render(camera, screen)  # Render b1 image
                    self.reduce_enemy_health()
                    self.stop()
                    self.is_targeting_enemy = False
                    self.target = None
                else:
                    self.goto(self.enemy_target.position)

            else:
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

    def combat(self, other):
        self.enemy_target = other
        distance = sqrt((self.position.x - other.position.x) ** 2 + (self.position.y - other.position.y) ** 2)

        if distance <= 250:
            self.stop()
            self.is_targeting_enemy = False
            self.target = None
        else:
            self.is_targeting_enemy = True
            self.target = other.position

    def reduce_enemy_health(self):
        # Reduce health by 40-50
        damage = random.randint(40, 50)
        if self.enemy_target:
            self.enemy_target.health -= damage
            print(f"Enemy health reduced by {damage}. New health: {self.enemy_target.health}")


class Game:
    def __init__(self):
        self.game_objects: dict[str, list[GameObject]] = {}

def get_camera_position(camera: Vector2, world_size: tuple, screen_size: tuple) -> tuple:
    camera_x = max(0, min(camera.x, world_size[0] - screen_size[0]))
    camera_y = max(0, min(camera.y, world_size[1] - screen_size[1]))
    return Vector2(camera_x, camera_y)

def select_troop(mouse_pos: tuple, camera: Vector2, troops: list[Troop], selected_troop: Troop = None) -> Troop:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    
    for troop in troops:
        if troop.rect.collidepoint(cam_offset.x, cam_offset.y):
            return troop
    
    return selected_troop

def select_enemy_troop(mouse_pos: tuple, camera: Vector2, enemy_troops: list[Troop], selected_enemy_troop: Troop = None) -> Troop:
    cam_offset = Vector2(mouse_pos[0] + camera.x, mouse_pos[1] + camera.y)
    
    for enemy_troop in enemy_troops:
        if enemy_troop.rect.collidepoint(cam_offset.x, cam_offset.y):
            return enemy_troop
    
    return selected_enemy_troop

def main():
    # Initialize pygame
    pygame.init()
    window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen = pygame.display.set_mode((1920, 1080))
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
    green_indicator = Indicator('imgs/green.png')
    green_indicator.scale((.15, .15))

    red_indicator = Indicator('imgs/red.png')
    red_indicator.scale((.2, .2))

    starship_grey = Troop('imgs/black_ship.png', (600, 450), 700, 2, int(200-250))
    starship_grey.scale(GLOBAL_SCALE)

    starship_red = Troop('imgs/red_ship.png', (600, 1000), 700, 2, int(70-80))
    starship_red.scale(GLOBAL_SCALE)

    command_center = Building('imgs/command_center.png', (100, 100), 2000)
    command_center.scale((.5, .5))

    barracks = Building('imgs/barracks.png', (450, 185), 1000)
    barracks.scale((.29, .29))

    starport = Building('imgs/starport.png', (150, 450), 750)
    starport.scale((.65, .65))

    depot = Building('imgs/vehicle_depot.png', (445, 450), 1250)
    depot.scale((.3, .3))

    red_troop = Troop('imgs/red_soildger.png', (1200, 700), 150, 10, int(40-50))
    red_troop.scale(GLOBAL_SCALE)

    blue_troop = Troop('imgs/blue_soildger.png', (300, 200), 150, 10, int(40-50))
    blue_troop.scale(GLOBAL_SCALE)

    blue_tank = Troop('imgs/blue_tank.png', (1000, 400), 500, 10, int(150-180))
    blue_tank.scale((.2, .2))

    selected_troop = None
    selected_enemy_troop = None
    troops = [red_troop, starship_red]
    enemy_troops = [blue_troop, starship_grey, blue_tank]
    buildings = [command_center, barracks, starport, depot]

    # Game loop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            mouse_pos = pygame.mouse.get_pos()
            world_size = (background.rect.width * 2, background.rect.height * 2)
            screen_size = screen.get_size()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    selected_troop = select_troop(pygame.mouse.get_pos(), camera, troops, selected_troop)

                elif event.button == 3:
                    if selected_troop == red_troop:
                        cam_pos = get_camera_position(camera, world_size, screen_size)
                        red_troop.target = Vector2(mouse_pos[0], mouse_pos[1]) + cam_pos

                    elif selected_troop == starship_red:
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
                selected_troop = None
            if keys[pygame.K_c] and selected_troop in troops:
                selected_enemy_troop = select_enemy_troop(pygame.mouse.get_pos(), camera, enemy_troops, selected_enemy_troop)
                if selected_enemy_troop:
                    selected_troop.combat(selected_enemy_troop)
            if keys[pygame.K_ESCAPE]:
                pygame.quit()
                exit()


        # Render background tiles
        for pos in background_tiles:
            screen.blit(background.surf, (pos[0] - camera.x, pos[1] - camera.y))

        red_troop.move(camera, screen)
        blue_troop.move(camera, screen)
        starship_grey.move(camera, screen)
        starship_red.move(camera, screen)
        blue_tank.move(camera, screen)

        # Render objects
        command_center.render(camera, screen)
        barracks.render(camera, screen)
        starport.render(camera, screen)
        depot.render(camera, screen)
        red_troop.render(camera, screen)
        blue_troop.render(camera, screen)
        blue_tank.render(camera, screen)
        starship_grey.render(camera, screen)
        starship_red.render(camera, screen)

        if selected_troop:
            screen.blit(green_indicator.surf, (selected_troop.rect.midbottom[0] - camera.x - green_indicator.rect.width // 2, selected_troop.rect.midbottom[1] - camera.y))

        if selected_enemy_troop:
            screen.blit(red_indicator.surf, (selected_enemy_troop.rect.midbottom[0] - camera.x - red_indicator.rect.width // 2, selected_enemy_troop.rect.midbottom[1] - camera.y))
        
        resized_screen = pygame.transform.scale(screen, (window.get_width(), window.get_height()))
        window.blit(resized_screen, (0, 0))

        # Update the display
        pygame.display.update()

if __name__ == "__main__":
    main()