import pygame
from config import CONFIG
from bullet import Bullet

class Enemy:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.size = CONFIG["enemy_size"]
        self.image = pygame.Surface(self.size)
        self.image.fill((255, 0, 0))
        self.speed = CONFIG["enemy_speed"]

    def move(self):
        self.y += self.speed

    def draw(self, screen):
        screen.blit(self.image, (self.x, self.y))

    def interact_with_bullet(self, bullets):
        bullets_to_remove = []
        for bullet in bullets:
            if self.x < bullet.x < self.x + self.size[0] and self.y < bullet.y < self.y + self.size[1]:
                bullets_to_remove.append(bullet)
        
        for bullet in bullets_to_remove:
            bullets.remove(bullet)

        return bool(bullets_to_remove)  # Returns True if any bullet hit the enemy

