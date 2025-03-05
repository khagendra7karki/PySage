import pygame
from config import CONFIG
from utils import log

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = CONFIG["player_speed"]
        self.image = pygame.Surface((50, 50))
        self.image.fill((0, 255, 0))

    def move(self, keys):
        if keys[pygame.K_LEFT]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.x += self.speed
        if keys[pygame.K_UP]:
            self.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.y += self.speed

    def draw(self, screen):
        screen.blit(self.image, (self.x, self.y))
