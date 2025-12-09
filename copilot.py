import pygame
import random
import sys
import json
import os
from enum import Enum

pygame.init()
pygame.mixer.init()

# Screen setup
WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Scorpion Survival")
screen_shake = 0

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE  = (0, 0, 200)
RED   = (200, 0, 0)
YELLOW = (255, 200, 0)
GREEN = (0, 200, 0)
LIGHT_BLUE = (100, 150, 255)

# Enemy types
class EnemyType(Enum):
    NORMAL = 1
    FAST = 2
    TANK = 3

# Power-up types
class PowerUpType(Enum):
    SHIELD = 1
    RAPID_FIRE = 2
    INVINCIBILITY = 3

# Particle system
class Particle:
    def __init__(self, x, y, vx, vy, lifetime=30):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.age = 0
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.age += 1
        return self.age < self.lifetime
    
    def draw(self, surface):
        alpha = int(255 * (1 - self.age / self.lifetime))
        color = (255, max(0, 200 - alpha), 0)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), 3)

particles = []

# Sound system (with fallback for missing files)
def load_sound(filename):
    try:
        return pygame.mixer.Sound(filename)
    except:
        return None

def play_sound(sound):
    if sound:
        sound.play()

# Try to load sounds, create dummy if missing
shoot_sound = load_sound("shoot.wav")
hit_sound = load_sound("hit.wav")
powerup_sound = load_sound("powerup.wav")
bg_music = load_sound("background.wav")

# High score management
SCORE_FILE = "highscore.json"

def load_high_score():
    if os.path.exists(SCORE_FILE):
        try:
            with open(SCORE_FILE, 'r') as f:
                return json.load(f).get('high_score', 0)
        except:
            return 0
    return 0

def save_high_score(score):
    with open(SCORE_FILE, 'w') as f:
        json.dump({'high_score': score}, f)

# Player setup
player_size = 50
player = pygame.Rect(WIDTH//2, HEIGHT - player_size - 10, player_size, player_size)
player_speed = 7
player_shield = False
player_shield_time = 0
player_invincible = False
player_invincible_time = 0
rapid_fire = False
rapid_fire_time = 0
rapid_fire_counter = 0

# Enemy setup
class Enemy:
    def __init__(self, x, y, enemy_type):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.type = enemy_type
        self.health = 1 if enemy_type == EnemyType.NORMAL else (1.5 if enemy_type == EnemyType.FAST else 3)
    
    def draw(self, surface):
        color = RED if self.type == EnemyType.NORMAL else (255, 100, 0) if self.type == EnemyType.FAST else (150, 0, 0)
        pygame.draw.rect(surface, color, self.rect)

enemies = []
enemy_speed = 4
spawn_rate = 25

# Power-ups
class PowerUp:
    def __init__(self, x, y, power_type):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.type = power_type
    
    def draw(self, surface):
        color = LIGHT_BLUE if self.type == PowerUpType.SHIELD else (255, 255, 0) if self.type == PowerUpType.RAPID_FIRE else (200, 100, 255)
        pygame.draw.rect(surface, color, self.rect)

powerups = []

# Missile setup
missiles = []
missile_speed = 8

# Score and Lives
score = 0
high_score = load_high_score()
lives = 3
font = pygame.font.SysFont("Comic Sans MS", 24)
large_font = pygame.font.SysFont("Comic Sans MS", 48)
small_font = pygame.font.SysFont("Comic Sans MS", 16)

clock = pygame.time.Clock()

# Game States
PLAYING = 0
GAME_OVER = 1
PAUSED = 2
game_state = PLAYING

def draw_window():
    global screen_shake
    
    # Apply screen shake
    shake_x = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
    shake_y = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
    
    screen.fill(WHITE)
    
    # Draw particles
    for particle in particles[:]:
        particle.draw(screen)
    
    # Draw player
    if player_invincible and int(player_invincible_time * 10) % 2:
        pygame.draw.rect(screen, LIGHT_BLUE, player.move(shake_x, shake_y))
    else:
        pygame.draw.rect(screen, BLUE, player.move(shake_x, shake_y))
    
    if player_shield:
        pygame.draw.circle(screen, LIGHT_BLUE, player.center, 60, 2)
    
    # Draw enemies
    for enemy in enemies:
        enemy.draw(screen)
        # Draw health for tank enemies
        if enemy.type == EnemyType.TANK and enemy.health < 3:
            health_color = (0, 255, 0) if enemy.health > 1.5 else RED
            pygame.draw.circle(screen, health_color, enemy.rect.center, 5)
    
    # Draw power-ups
    for powerup in powerups:
        powerup.draw(screen)
    
    # Draw missiles
    for missile in missiles:
        pygame.draw.rect(screen, YELLOW, missile)
    
    # Draw UI
    score_text = font.render(f"Score: {score}", True, BLACK)
    lives_text = font.render(f"Lives: {lives}", True, RED)
    high_score_text = small_font.render(f"High: {high_score}", True, BLACK)
    screen.blit(score_text, (10, 10))
    screen.blit(lives_text, (WIDTH - 150, 10))
    screen.blit(high_score_text, (WIDTH - 150, 40))
    
    # Draw power-up timers
    if player_shield:
        shield_text = small_font.render(f"Shield: {player_shield_time:.1f}s", True, LIGHT_BLUE)
        screen.blit(shield_text, (10, 40))
    
    if rapid_fire:
        rapid_text = small_font.render(f"Rapid Fire: {rapid_fire_time:.1f}s", True, YELLOW)
        screen.blit(rapid_text, (10, 60))
    
    if player_invincible:
        invincible_text = small_font.render(f"Invincible: {player_invincible_time:.1f}s", True, GREEN)
        screen.blit(invincible_text, (10, 80))
    
    pygame.display.update()
    
    # Reduce screen shake
    screen_shake = max(0, screen_shake - 1)

def draw_game_over():
    screen.fill(WHITE)
    game_over_text = large_font.render("GAME OVER", True, RED)
    final_score_text = font.render(f"Final Score: {score}", True, BLACK)
    high_score_text = font.render(f"High Score: {high_score}", True, BLACK)
    restart_text = font.render("Press SPACE to Restart or Q to Quit", True, BLACK)
    
    screen.blit(game_over_text, (WIDTH//2 - 150, HEIGHT//2 - 120))
    screen.blit(final_score_text, (WIDTH//2 - 120, HEIGHT//2 - 20))
    screen.blit(high_score_text, (WIDTH//2 - 130, HEIGHT//2 + 20))
    screen.blit(restart_text, (WIDTH//2 - 180, HEIGHT//2 + 80))
    pygame.display.update()

def draw_pause():
    screen.fill(BLACK)
    pause_text = large_font.render("PAUSED", True, WHITE)
    resume_text = font.render("Press P to Resume", True, WHITE)
    screen.blit(pause_text, (WIDTH//2 - 120, HEIGHT//2 - 50))
    screen.blit(resume_text, (WIDTH//2 - 110, HEIGHT//2 + 50))
    pygame.display.update()

def reset_game():
    global score, lives, enemy_speed, spawn_rate, game_state, high_score
    global player_shield, player_shield_time, player_invincible, player_invincible_time
    global rapid_fire, rapid_fire_time
    score = 0
    lives = 3
    enemy_speed = 4
    spawn_rate = 25
    enemies.clear()
    missiles.clear()
    powerups.clear()
    particles.clear()
    player.x = WIDTH // 2
    player_shield = False
    player_shield_time = 0
    player_invincible = False
    player_invincible_time = 0
    rapid_fire = False
    rapid_fire_time = 0
    game_state = PLAYING
    if bg_music:
        bg_music.play(-1)

def main():
    global score, lives, enemy_speed, spawn_rate, game_state, high_score, screen_shake
    global player_shield, player_shield_time, player_invincible, player_invincible_time
    global rapid_fire, rapid_fire_time, rapid_fire_counter
    
    running = True
    if bg_music:
        bg_music.play(-1)
    
    while running:
        clock.tick(30)
        
        if game_state == PAUSED:
            draw_pause()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        game_state = PLAYING
            continue
        
        if game_state == GAME_OVER:
            draw_game_over()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        reset_game()
                    if event.key == pygame.K_q:
                        running = False
            continue
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    missiles.append(pygame.Rect(player.centerx - 5, player.top, 10, 20))
                    play_sound(shoot_sound)
                if event.key == pygame.K_p:
                    game_state = PAUSED
        
        # Update power-up timers
        if player_shield:
            player_shield_time -= 1/30
            if player_shield_time <= 0:
                player_shield = False
        
        if rapid_fire:
            rapid_fire_time -= 1/30
            if rapid_fire_time <= 0:
                rapid_fire = False
        
        if player_invincible:
            player_invincible_time -= 1/30
            if player_invincible_time <= 0:
                player_invincible = False
        
        # Player movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player.left > 0:
            player.x -= player_speed
        if keys[pygame.K_RIGHT] and player.right < WIDTH:
            player.x += player_speed
        
        # Difficulty scaling
        if score > 0 and score % 10 == 0:
            enemy_speed = min(8, 4 + (score // 10) * 0.5)
            spawn_rate = max(15, 25 - (score // 10))
        
        # Enemy spawning with varied types
        if random.randint(1, spawn_rate) == 1:
            x_pos = random.randint(0, WIDTH - 40)
            enemy_type_choice = random.choices([EnemyType.NORMAL, EnemyType.FAST, EnemyType.TANK], 
                                               weights=[50, 30, 20])[0]
            enemies.append(Enemy(x_pos, 0, enemy_type_choice))
        
        # Enemy movement
        for enemy in enemies[:]:
            speed = enemy_speed if enemy.type == EnemyType.NORMAL else (enemy_speed * 1.5 if enemy.type == EnemyType.FAST else enemy_speed * 0.7)
            enemy.rect.y += speed
            
            if enemy.rect.top > HEIGHT:
                enemies.remove(enemy)
            elif enemy.rect.colliderect(player):
                if not player_invincible:
                    if player_shield:
                        player_shield = False
                        play_sound(hit_sound)
                        for _ in range(8):
                            particles.append(Particle(player.centerx, player.centery, 
                                                    random.uniform(-3, 3), random.uniform(-3, 3)))
                        enemies.remove(enemy)
                    else:
                        lives -= 1
                        screen_shake = 5
                        play_sound(hit_sound)
                        for _ in range(15):
                            particles.append(Particle(player.centerx, player.centery, 
                                                    random.uniform(-5, 5), random.uniform(-5, 5)))
                        enemies.remove(enemy)
                        if lives <= 0:
                            game_state = GAME_OVER
                            if score > high_score:
                                high_score = score
                                save_high_score(high_score)
        
        # Power-up spawning (10% chance when enemy dies)
        # (handled in missile collision below)
        
        # Rapid fire automatic shooting
        if rapid_fire:
            rapid_fire_counter += 1
            if rapid_fire_counter >= 3:
                missiles.append(pygame.Rect(player.centerx - 5, player.top, 10, 20))
                play_sound(shoot_sound)
                rapid_fire_counter = 0
        
        # Power-up collection
        for powerup in powerups[:]:
            if powerup.rect.colliderect(player):
                play_sound(powerup_sound)
                if powerup.type == PowerUpType.SHIELD:
                    player_shield = True
                    player_shield_time = 5
                elif powerup.type == PowerUpType.RAPID_FIRE:
                    rapid_fire = True
                    rapid_fire_time = 8
                elif powerup.type == PowerUpType.INVINCIBILITY:
                    player_invincible = True
                    player_invincible_time = 5
                powerups.remove(powerup)
        
        # Missile movement
        for missile in missiles[:]:
            missile.y -= 8
            if missile.bottom < 0:
                missiles.remove(missile)
            else:
                hit = False
                for enemy in enemies[:]:
                    if missile.colliderect(enemy.rect):
                        enemy.health -= 1
                        
                        # Explosion particles
                        for _ in range(10):
                            particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, 
                                                    random.uniform(-4, 4), random.uniform(-4, 4)))
                        
                        if enemy.health <= 0:
                            enemies.remove(enemy)
                            score += 1 if enemy.type == EnemyType.NORMAL else (2 if enemy.type == EnemyType.FAST else 3)
                            
                            # Power-up drop
                            if random.random() < 0.15:
                                powerup_type = random.choices([PowerUpType.SHIELD, PowerUpType.RAPID_FIRE, PowerUpType.INVINCIBILITY],
                                                             weights=[40, 35, 25])[0]
                                powerups.append(PowerUp(enemy.rect.centerx, enemy.rect.centery, powerup_type))
                        
                        if missile in missiles:
                            missiles.remove(missile)
                        hit = True
                        break
        
        # Update particles
        for particle in particles[:]:
            if not particle.update():
                particles.remove(particle)
        
        draw_window()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
