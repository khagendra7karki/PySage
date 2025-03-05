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

        pygame.display.flip()
        clock.tick(CONFIG["fps"])
    
    pygame.quit()
