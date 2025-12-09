import pygame
import random
import sys

pygame.init()

# Screen setup
WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Scorpion Survival")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE  = (0, 0, 200)
RED   = (200, 0, 0)
YELLOW = (255, 200, 0)

# Player setup
player_size = 50
player = pygame.Rect(WIDTH//2, HEIGHT - player_size - 10, player_size, player_size)
player_speed = 7

# Enemy setup
enemy_size = 40
enemies = []
enemy_speed = 4

# Missile setup
missiles = []
missile_speed = 8

# Score
score = 0
font = pygame.font.SysFont("Arial", 24)

clock = pygame.time.Clock()

def draw_window():
    screen.fill(WHITE)
    pygame.draw.rect(screen, BLUE, player)
    for enemy in enemies:
        pygame.draw.rect(screen, RED, enemy)
    for missile in missiles:
        pygame.draw.rect(screen, YELLOW, missile)
    score_text = font.render(f"Score: {score}", True, BLACK)
    screen.blit(score_text, (10, 10))
    pygame.display.update()

def main():
    global score
    running = True
    while running:
        clock.tick(30)
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    missiles.append(pygame.Rect(player.centerx - 5, player.top, 10, 20))
        
        # Player movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player.left > 0:
            player.x -= player_speed
        if keys[pygame.K_RIGHT] and player.right < WIDTH:
            player.x += player_speed
        
        # Enemy spawning
        if random.randint(1, 25) == 1:
            x_pos = random.randint(0, WIDTH - enemy_size)
            enemies.append(pygame.Rect(x_pos, 0, enemy_size, enemy_size))
        
        # Enemy movement
        for enemy in enemies[:]:
            enemy.y += enemy_speed
            if enemy.top > HEIGHT:
                enemies.remove(enemy)
            if enemy.colliderect(player):
                print("Game Over! Final Score:", score)
                running = False
        
        # Missile movement
        for missile in missiles[:]:
            missile.y -= missile_speed
            if missile.bottom < 0:
                missiles.remove(missile)
            else:
                for enemy in enemies[:]:
                    if missile.colliderect(enemy):
                        enemies.remove(enemy)
                        missiles.remove(missile)
                        score += 1
                        break
        
        draw_window()

if __name__ == "__main__":
    main()
 