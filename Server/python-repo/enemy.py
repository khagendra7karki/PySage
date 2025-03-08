import pygame
from config import CONFIG
from bullet import Bullet

class Enemy:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.size = CONFIG["enemy_size"]
        self.image = pygame.Surface(self.size).fill((255, 0, 0))
        self.speed = CONFIG["enemy_speed"]

    def move(self): self.y += self.speed
    def draw(self, screen): screen.blit(self.image, (self.x, self.y))

    def interact_with_bullet(self, bullets):
        for bullet in bullets:
            if self.x < bullet.x < self.x + self.size[0] and self.y < bullet.y < self.y + self.size[1]:
                bullets.remove(bullet)
                return True  # Bullet hit the enemy
        return False
    
    def check_collision_with_bullet(self, bullets):
        return False
