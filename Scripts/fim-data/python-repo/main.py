import pygame
from config import CONFIG
from player import Player
from enemy import Enemy
from bullet import Bullet as b

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
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                player.shoot()

        # Move player and restrict within screen bounds
        player.move(keys)
        player.x = max(0, min(player.x, CONFIG["screen_width"] - player.size[0]))
        player.y = max(0, min(player.y, CONFIG["screen_height"] - player.size[1]))

        # Move and draw enemy
        enemy.move()
        enemy.draw(screen)

        # Move bullets and remove off-screen bullets
        for bullet in player.bullets:
            bullet.move()
        
        player.bullets = [bullet for bullet in player.bullets if not bullet.is_off_screen()]

        # Draw player and bullets
        player.draw(screen)

        # Check bullet collisions with enemy
        if enemy.interact_with_bullet(player.bullets):
            print("Enemy hit by bullet!")

        pygame.display.flip()
        clock.tick(CONFIG["fps"])

    pygame.quit()

if __name__ == "__main__":
    game_loop()
