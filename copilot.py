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
pygame.display.set_caption("Starship Defense")
screen_shake = 0

# Colors - Sci-fi theme
BLACK_SPACE = (5, 5, 20)
CYAN = (0, 255, 255)
NEON_GREEN = (0, 255, 100)
NEON_PINK = (255, 0, 200)
NEON_PURPLE = (150, 0, 255)
DARK_BLUE = (10, 50, 100)
WHITE = (220, 220, 255)
SHIELD_COLOR = (100, 200, 255)
RED = (255, 50, 50)

# Enemy types
class EnemyType(Enum):
    DRONE = 1       # Small fast scout
    FIGHTER = 2     # Medium speed
    CAPITAL = 3     # Large slow tank

# Power-up types
class PowerUpType(Enum):
    SHIELD = 1          # Energy shield
    RAPID_FIRE = 2      # Laser burst
    INVINCIBILITY = 3   # Warp core

# Particle system
class Particle:
    def __init__(self, x, y, vx, vy, lifetime=30, color=(0, 255, 255)):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.age = 0
        self.color = color
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.age += 1
        return self.age < self.lifetime
    
    def draw(self, surface):
        alpha = int(255 * (1 - self.age / self.lifetime))
        color = tuple(int(c * (alpha / 255)) for c in self.color)
        size = int(3 * (1 - self.age / self.lifetime))
        if size > 0:
            pygame.draw.circle(surface, color, (int(self.x), int(self.y)), size)

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
        self.health = 1 if enemy_type == EnemyType.DRONE else (1.5 if enemy_type == EnemyType.FIGHTER else 3)
    
    def draw(self, surface):
        if self.type == EnemyType.DRONE:
            # Small cyan drone
            pygame.draw.rect(surface, CYAN, self.rect)
            pygame.draw.circle(surface, NEON_GREEN, self.rect.center, 8, 2)
        elif self.type == EnemyType.FIGHTER:
            # Pink fighter
            pygame.draw.polygon(surface, NEON_PINK, [
                (self.rect.centerx, self.rect.top),
                (self.rect.right, self.rect.centery),
                (self.rect.centerx, self.rect.bottom),
                (self.rect.left, self.rect.centery)
            ])
        else:  # CAPITAL
            # Large purple capital ship
            pygame.draw.rect(surface, NEON_PURPLE, self.rect)
            pygame.draw.circle(surface, CYAN, self.rect.center, 15, 2)

enemies = []
enemy_speed = 4
spawn_rate = 25

# Power-ups
class PowerUp:
    def __init__(self, x, y, power_type):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.type = power_type
    
    def draw(self, surface):
        if self.type == PowerUpType.SHIELD:
            pygame.draw.rect(surface, SHIELD_COLOR, self.rect)
            pygame.draw.circle(surface, CYAN, self.rect.center, 10, 2)
        elif self.type == PowerUpType.RAPID_FIRE:
            pygame.draw.rect(surface, NEON_GREEN, self.rect)
            pygame.draw.line(surface, CYAN, self.rect.topleft, self.rect.bottomright, 2)
        else:  # INVINCIBILITY
            pygame.draw.rect(surface, NEON_PINK, self.rect)
            pygame.draw.circle(surface, NEON_PINK, self.rect.center, 12, 2)

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
    
    screen.fill(BLACK_SPACE)
    
    # Draw stars in background
    for i in range(10):
        star_x = (int(score / 10) + i * 60) % WIDTH
        pygame.draw.circle(screen, WHITE, (star_x, 20 + (i % 5) * 60), 1)
    
    # Draw particles
    for particle in particles[:]:
        particle.draw(screen)
    
    # Draw player (starship)
    if player_invincible and int(player_invincible_time * 10) % 2:
        pygame.draw.polygon(screen, SHIELD_COLOR, [
            (player.centerx, player.top + shake_x),
            (player.right, player.centery + shake_y),
            (player.centerx, player.bottom + shake_x),
            (player.left, player.centery + shake_y)
        ])
    else:
        pygame.draw.polygon(screen, CYAN, [
            (player.centerx, player.top + shake_x),
            (player.right, player.centery + shake_y),
            (player.centerx, player.bottom + shake_x),
            (player.left, player.centery + shake_y)
        ])
    
    if player_shield:
        pygame.draw.circle(screen, SHIELD_COLOR, player.center, 60, 3)
    
    # Draw enemies
    for enemy in enemies:
        enemy.draw(screen)
    
    # Draw power-ups
    for powerup in powerups:
        powerup.draw(screen)
    
    # Draw laser missiles
    for missile in missiles:
        pygame.draw.line(screen, NEON_GREEN, (missile.centerx, missile.top), (missile.centerx, missile.bottom), 3)
        pygame.draw.circle(screen, NEON_GREEN, missile.center, 2)
    
    # Draw UI with neon styling
    score_text = font.render(f"SCORE: {score}", True, NEON_GREEN)
    lives_text = font.render(f"SHIPS: {lives}", True, RED)
    high_score_text = small_font.render(f"HIGH: {high_score}", True, CYAN)
    screen.blit(score_text, (10, 10))
    screen.blit(lives_text, (WIDTH - 180, 10))
    screen.blit(high_score_text, (WIDTH - 180, 40))
    
    # Draw power-up timers
    if player_shield:
        shield_text = small_font.render(f"SHIELD: {player_shield_time:.1f}s", True, SHIELD_COLOR)
        screen.blit(shield_text, (10, 40))
    
    if rapid_fire:
        rapid_text = small_font.render(f"BURST: {rapid_fire_time:.1f}s", True, NEON_GREEN)
        screen.blit(rapid_text, (10, 60))
    
    if player_invincible:
        invincible_text = small_font.render(f"WARP: {player_invincible_time:.1f}s", True, NEON_PINK)
        screen.blit(invincible_text, (10, 80))
    
    pygame.display.update()
    
    # Reduce screen shake
    screen_shake = max(0, screen_shake - 1)

def draw_game_over():
    screen.fill(BLACK_SPACE)
    game_over_text = large_font.render("MISSION FAILED", True, RED)
    final_score_text = font.render(f"FINAL SCORE: {score}", True, NEON_GREEN)
    high_score_text = font.render(f"HIGH SCORE: {high_score}", True, CYAN)
    restart_text = font.render("Press SPACE to Restart or Q to Quit", True, WHITE)
    
    screen.blit(game_over_text, (WIDTH//2 - 160, HEIGHT//2 - 120))
    screen.blit(final_score_text, (WIDTH//2 - 150, HEIGHT//2 - 20))
    screen.blit(high_score_text, (WIDTH//2 - 160, HEIGHT//2 + 20))
    screen.blit(restart_text, (WIDTH//2 - 200, HEIGHT//2 + 80))
    pygame.display.update()

def draw_pause():
    screen.fill(BLACK_SPACE)
    pause_text = large_font.render("SYSTEMS PAUSED", True, CYAN)
    resume_text = font.render("Press P to Resume", True, WHITE)
    screen.blit(pause_text, (WIDTH//2 - 180, HEIGHT//2 - 50))
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
            enemy_type_choice = random.choices([EnemyType.DRONE, EnemyType.FIGHTER, EnemyType.CAPITAL], 
                                               weights=[50, 30, 20])[0]
            enemies.append(Enemy(x_pos, 0, enemy_type_choice))
        
        # Enemy movement
        for enemy in enemies[:]:
            speed = enemy_speed if enemy.type == EnemyType.DRONE else (enemy_speed * 1.5 if enemy.type == EnemyType.FIGHTER else enemy_speed * 0.7)
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
                            score += 1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3)
                            
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
