import pygame
from config import CONFIG
from player import Player
from enemy import Enemy
from bullet import Bullet

def game_loop():
    pygame.init()
    screen = pygame.display.set_mode((CONFIG["screen_width"], CONFIG["screen_height"]))
    clock = pygame.time.Clock()
    player = Player(375, 500)
    enemy = Enemy(375, 50)

    running = True
    while running:
        screen.fill((0, 0, 0))
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                player.shoot()

        player.move(keys)
        enemy.move()
        player.draw(screen)
        enemy.draw(screen)

        if enemy.interact_with_bullet(player.bullets):  # Enemy interacts with player bullets
            print("Enemy hit by bullet!")

        pygame.display.flip()
        clock.tick(CONFIG["fps"])

    pygame.quit()

if __name__ == "__main__": game_loop()

