import pygame
from sys import exit

pygame.init()
screen = pygame.display.set_mode((2000, 1000))

background_surf = pygame.image.load('imgs/background_grid.png')
background_surf = pygame.transform.scale(background_surf, (3000, 2000))

starship_surf = pygame.image.load('imgs/black_ship.png')
w = starship_surf.get_rect().width
h = starship_surf.get_rect().height
starship_surf = pygame.transform.scale(starship_surf, (w * .25, h * .25))
starship_rect = starship_surf.get_rect(center = (1000, 500))

command_surf = pygame.image.load('imgs/command_center.png')
w = command_surf.get_rect().width
h = command_surf.get_rect().height
command_surf = pygame.transform.scale(command_surf, (w * .25, h * .25))
command_rect = command_surf.get_rect(center = (200, 200))

barraks_surf = pygame.image.load('imgs/barracks.png')
w = barraks_surf.get_rect().width
h = barraks_surf.get_rect().height
barraks_surf = pygame.transform.scale(barraks_surf, (w * .25, h * .25))
barraks_rect = barraks_surf.get_rect(midleft = (375, 250))

starport_surf = pygame.image.load('imgs/starport.png')
w = starport_surf.get_rect().width
h = starport_surf.get_rect().height
starport_surf = pygame.transform.scale(starport_surf, (w * .25, h * .25))
starport_rect = starport_surf.get_rect(midtop = (200, 395))

depo_surf = pygame.image.load('imgs/vehicle_deop.png')
w = depo_surf.get_rect().width
h = depo_surf.get_rect().height
depo_surf = pygame.transform.scale(depo_surf, (w * .25, h * .25))
deop_rect = depo_surf.get_rect(topleft = (375, 375))

red_surf = pygame.image.load('imgs/red_soildger.png')
w = red_surf.get_rect().width
h = red_surf.get_rect().height
red_surf = pygame.transform.scale(red_surf, (w * .25, h * .25))
red_rect = red_surf.get_rect(center = (200, 200))

blue_surf = pygame.image.load('imgs/blue_soildger.png')
w = blue_surf.get_rect().width
h = blue_surf.get_rect().height
blue_surf = pygame.transform.scale(blue_surf, (w * .25, h * .25))
blue_rect = blue_surf.get_rect(center = (200, 200))


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        

    screen.blit(background_surf, (0, 0))
    screen.blit(starship_surf, starship_rect)
    screen.blit(command_surf, command_rect)
    screen.blit(barraks_surf, barraks_rect)
    screen.blit(starport_surf, starport_rect)
    screen.blit(depo_surf, deop_rect)
    screen.blit(red_surf, red_rect)
    screen.blit(blue_surf, blue_rect)
    
    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        pygame.quit()
        exit()
    
    pygame.display.update()