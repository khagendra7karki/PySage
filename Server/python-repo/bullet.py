import pygame
from config import CONFIG

class Bullet:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.size = CONFIG["bullet_size"]
        self.image = pygame.Surface(self.size).fill((255, 255, 0))
        self.speed = CONFIG["bullet_speed"]

    def move(self): self.y -= self.speed
    def draw(self, screen): screen.blit(self.image, (self.x, self.y))
    def is_off_screen(self): return self.y < 0

