from bullet import Bullet

def game_loop():
    pygame.init()
    screen = pygame.display.set_mode((CONFIG["screen_width"], CONFIG["screen_height"]))
    clock = pygame.time.Clock()
    player = Player(375, 500)
    enemy = Enemy(375, 50)
    bullets = []  # List to store bullets

    running = True
    while running:
        screen.fill((0, 0, 0))
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                bullets.append(Bullet(player.x + 22, player.y))  # Spawn bullet at player's position

        # Move and draw bullets
        for bullet in bullets[:]:  # Copy list to safely remove items
            bullet.move()
            bullet.draw(screen)
            if bullet.is_off_screen():
                bullets.remove(bullet)

        player.move(keys)
        enemy.move()
        player.draw(screen)
        enemy.draw(screen)
Explanation:**Bullet Class**: Represents a bullet, where attributes sucas `x`, h `y`, `speed`, and `image` are defined. The `move` method moves the bullet down, the `draw` method displays the bullet, and the `is_off_screen` method checks if the bullet has moved 
- off the screen.**Player Class**: Represents the player, with attributesuch as ``y`, and x`, `speed`. The s `move` method moves the pldown, the ayer `draw` method displays the player, and the `is_off_screen` method checks if the player has moved 
- off the screen.**game_loop**: Contains the main game loop. It handles events, manages bullets, draws sprites, 
and updates the game - **Configuration**: state.Contains configuration settings fogame, such as screen r the dimensions and framThe `Config` class e rate. provides methods for accessing these 
- settings.Class**: Represents a bullet, with methods to initialize, move, draw, and check if it has 
moved off the screen.This code provides a basic framework for a simple bugame in Pygame. llet The player can shoot bullets and the enemy will move to attack enemies.<|im_end|>
- ** bullet 
        pygame.display.flip()
        clock.tick(CONFIG["fps"])
    
    pygame.quit()
