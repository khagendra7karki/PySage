import pygame

class Bullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 7
        self.image = pygame.Surface((5, 10))
        self.image.fill((255, 255, 0))  # Yellow bullets

    def move(self):
        self.y -= self.speed  # Move bullet upwards

    def draw(self, screen):
        screen.blit(self.image, (self.x, self.y))

    def is_off_screen(self):
        return self.y < 0
