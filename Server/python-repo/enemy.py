import pygame
from config import CONFIG

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = CONFIG["enemy_speed"]
        self.image = pygame.Surface((50, 50))
        self.image.fill((255, 0, 0))