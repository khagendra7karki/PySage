import pygame
from config import CONFIG

class Bullet:
    def __init__(self, x, y):
        self.size = CONFIG["bullet_size"]
        self.x = x - self.size[0] // 2  # Center the bullet
        self.y = y
        self.image = pygame.Surface(self.size)
        self.image.fill((255, 255, 0))
        self.speed = CONFIG["bullet_speed"]

    def move(self):
        self.y -= self.speed

    def draw(self, screen):
        screen.blit(self.image, (self.x, self.y))

    def is_off_screen(self):
        return self.y + self.size[1] < 0  # Ensures complete disappearance before removal
