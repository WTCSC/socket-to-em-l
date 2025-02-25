import pygame
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
    
    def __str__(self):
        return f"({self.x}, {self.y})"

    __rmul__ = __mul__
    
class GameObject:
    def __init__(self, sprite: str, position: tuple):
        self.sprite = sprite
        self.position = Vector2(position[0], position[1])
        self.surf = pygame.image.load(self.sprite)
        self.rect = self.get_rect()
    
    def render(self):
        screen.blit(self.surf, self.rect)
    
    def scale(self, factor: tuple):
        self.surf = pygame.transform.scale(self.surf, (self.rect.width * factor[0], self.rect.height * factor[1]))
        self.rect = self.get_rect()
    
    def size(self, size: tuple):
        self.surf = pygame.transform.scale(self.surf, size)
        self.rect = self.get_rect()

    def get_rect(self):
        return self.surf.get_rect(topleft = tuple(self.position))

class Building(GameObject):
    def __init__(self, sprite: str, position: tuple, health: int):
        super().__init__(sprite, position)
        self.health = health

class Troop(GameObject):
    def __init__(self, sprite: str, position: tuple, health: int, speed: int):
        super().__init__(sprite, position)
        self.health = health
        self.speed = speed
        self.velocity = Vector2(0, 0)

    def move(self):
        self.position.x += self.velocity.x
        self.position.y += self.velocity.y
        self.rect = self.get_rect()


pygame.init()
screen = pygame.display.set_mode((1500, 800))
GLOBAL_SCALE = (.25, .25)

background = GameObject('imgs/background_grid.png', (0, 0))
background.size((3000, 2000))

starship_grey = Troop('imgs/black_ship.png', (600, 450), 400, 2)
starship_grey.scale(GLOBAL_SCALE)

#starship_red = Troop('imgs/red_ship.png', (600, 450), 400, 2)
#starship_red.scale(GLOBAL_SCALE)

#starship_yellow = Troop('imgs/yellow_ship.png', (600, 450), 400, 2)
#starship_yellow.scale(GLOBAL_SCALE)

command_center = Building('imgs/command_center.png', (100, 100), 3000)
command_center.scale(GLOBAL_SCALE)

barracks = Building('imgs/barracks.png', (400, 150), 1250)
barracks.scale(GLOBAL_SCALE)

starport = Building('imgs/starport.png', (150, 450), 750)
starport.scale(GLOBAL_SCALE)

depot = Building('imgs/vehicle_deop.png', (375, 350), 1500)
depot.scale(GLOBAL_SCALE)

red_troop = Troop('imgs/red_soildger.png', (1200, 700), 75, 2)
red_troop.scale(GLOBAL_SCALE)

blue_troop = Troop('imgs/blue_soildger.png', (300, 200), 75, 5)
blue_troop.scale(GLOBAL_SCALE)

troops: list[Troop]= []
for i in range(3):
    troops.append(Troop('imgs/blue_soildger.png', (200 * i, 200 * i), 75, 5))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
    
    for i, troop in enumerate(troops):
        next_troop = troops[i + 1] if i + 1 < len(troops) else troops[0]
        troop.velocity = Vector2(next_troop.position.x - troop.position.x, next_troop.position.y - troop.position.y).normalize() * troop.speed
        troop.move()
        print(troop.surf.get_height())
        troop.render()

    blue_troop.velocity = Vector2(red_troop.position.x - blue_troop.position.x, red_troop.position.y - blue_troop.position.y).normalize() * blue_troop.speed
    red_troop.velocity = Vector2(-1, -1) * red_troop.speed

    blue_troop.move()
    starship_grey.move()
    red_troop.move()

    background.render()
    starship_grey.render()
    command_center.render()
    barracks.render()
    starport.render()
    depot.render()
    red_troop.render()
    blue_troop.render()
    
    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        pygame.quit()
        exit()
    
    pygame.display.update()