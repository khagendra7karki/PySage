import pygame
from config import CONFIG
from enemy import Enemy
from bullet import Bullet

class Player:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.size = CONFIG["player_size"]
        self.image = pygame.Surface(self.size).fill((0, 255, 0))
        self.speed = CONFIG["player_speed"]
        self.enemy = Enemy(375, 50)  # Depend on Enemy class for interaction
        self.bullets = []

    def move(self, keys):
        if keys[pygame.K_LEFT]: self.x -= self.speed
        if keys[pygame.K_RIGHT]: self.x += self.speed
        if keys[pygame.K_UP]: self.y -= self.speed
        if keys[pygame.K_DOWN]: self.y += self.speed

    def shoot(self):
        self.bullets.append(Bullet(self.x + 22, self.y))  # Player shoots bullets

    def draw(self, screen):
        screen.blit(self.image, (self.x, self.y))
        for bullet in self.bullets:
            bullet.move()
            bullet.draw(screen)

