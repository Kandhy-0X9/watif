import pygame
import random
import sys
import json
import os
import math
from enum import Enum

pygame.init()
pygame.mixer.init()

# Screen setup
WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Starship Defense")
screen_shake = 0

# CRT filter surface (scanlines)
crt_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for y in range(0, HEIGHT, 4):
    pygame.draw.line(crt_surface, (0, 0, 0, 45), (0, y), (WIDTH, y))

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
    ORBITAL = 4         # Deployable orbital satellites
    CUTTER = 5          # Freezes enemies + spinning blades

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
        alpha = max(0, int(255 * (1 - self.age / self.lifetime)))
        # create a small surface for alpha drawing
        size = max(1, int(3 * (1 - self.age / self.lifetime)))
        surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        draw_color = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(surf, draw_color, (size, size), size)
        surface.blit(surf, (int(self.x)-size, int(self.y)-size))

particles = []

# Shockwaves (for damage)
shockwaves = []

class Shockwave:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 1
        self.alpha = 255
    
    def update(self):
        self.radius += 4
        self.alpha -= 10
        return self.alpha > 0
    
    def draw(self, surface):
        if self.alpha <= 0:
            return
        size = int(self.radius * 2 + 6)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 255, 255, max(0, self.alpha)), (size//2, size//2), int(self.radius), 3)
        surface.blit(surf, (int(self.x) - size//2, int(self.y) - size//2))

# Background starfield
NUM_STARS = 80
stars = []
for _ in range(NUM_STARS):
    stars.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), random.choice([1, 2]), random.uniform(0.5, 1.8)])

# Sound system (with fallback for missing files)
def load_sound(filename):
    try:
        return pygame.mixer.Sound(filename)
    except:
        return None

def play_sound(sound):
    if sound:
        try:
            sound.play()
        except:
            pass

# Audio setup: auto-detect audio files and map them to roles
shoot_sound = None
hit_sound = None
powerup_sound = None
rapid_fire_sound = None
shield_sound = None
warp_sound = None
orbital_sound = None
cutter_sound = None
bg_music_file = None
audio_files = [f for f in os.listdir('.') if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
if audio_files:
    # choose background music (prefer files with "background", "bg", or "music" in the name)
    for f in audio_files:
        if any(k in f.lower() for k in ('background', 'bg', 'music', 'ambient')):
            bg_music_file = f
            break
    if not bg_music_file:
        # fallback to the first file
        bg_music_file = audio_files[0]

    # try loading background music via mixer.music (streaming)
    try:
        pygame.mixer.music.load(bg_music_file)
        pygame.mixer.music.set_volume(0.25)
        pygame.mixer.music.play(-1)
    except Exception:
        bg_music_file = None

    def pick_file(keywords, exclude=None):
        for f in audio_files:
            if exclude and f == exclude:
                continue
            lname = f.lower()
            if any(k in lname for k in keywords):
                return f
        return None

    # map common roles to files
    shoot_candidate = pick_file(('laser', 'shoot', 'gun', 'pew', 'zap'))
    hit_candidate = pick_file(('hit', 'explode', 'explosion', 'boom', 'impact'), exclude=bg_music_file)
    powerup_candidate = pick_file(('powerup', 'power', 'pickup', 'collect', 'ping'), exclude=bg_music_file)
    rapid_candidate = pick_file(('burst', 'rapid', 'auto', 'blip'), exclude=bg_music_file)
    orbital_candidate = pick_file(('orbital', 'orb', 'satellite', 'deploy', 'launch'), exclude=bg_music_file)
    cutter_candidate = pick_file(('cutter', 'cut', 'slice'), exclude=bg_music_file)

    # fallback selections
    if not shoot_candidate:
        shoot_candidate = pick_file(('laser', 'shoot', 'gun')) or (audio_files[0] if audio_files else None)
    if not hit_candidate:
        hit_candidate = pick_file(('explode', 'hit'))
    if not powerup_candidate:
        powerup_candidate = pick_file(('powerup', 'pickup', 'ping'))
        # specific power-up sounds (shield/warp)
        shield_candidate = pick_file(('shield', 'sheild'), exclude=bg_music_file)
        warp_candidate = pick_file(('warp', 'invinc', 'invulnerability'), exclude=bg_music_file)
    if not rapid_candidate:
        rapid_candidate = pick_file(('burst', 'rapid'))

    # load sounds (use load_sound which handles exceptions)
    if shoot_candidate:
        shoot_sound = load_sound(shoot_candidate)
    if hit_candidate:
        hit_sound = load_sound(hit_candidate)
    if powerup_candidate:
        powerup_sound = load_sound(powerup_candidate)
    if 'shield_candidate' in locals() and shield_candidate:
        shield_sound = load_sound(shield_candidate)
    else:
        shield_sound = None
    if 'warp_candidate' in locals() and warp_candidate:
        warp_sound = load_sound(warp_candidate)
    else:
        warp_sound = None
    if rapid_candidate:
        rapid_fire_sound = load_sound(rapid_candidate)
    else:
        rapid_fire_sound = None
    if orbital_candidate:
        orbital_sound = load_sound(orbital_candidate)
    else:
        orbital_sound = None
    if cutter_candidate:
        cutter_sound = load_sound(cutter_candidate)
    else:
        cutter_sound = None

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
orbital_count = 0
orbital_charging = False
orbital_charge_duration = 12.0  # 12 seconds to charge
orbital_charge_time = 0.0
orbital_beam_active = False
orbital_beam_duration = 2.0  # beam lasts 2 seconds
orbital_beam_time = 0.0
orbital_beam_width = 80  # beam width in pixels
# Cutter upgrade (rare like orbital): freezes enemies and spins blades
cutter_charging = False
cutter_charge_duration = 12.0
cutter_charge_time = 0.0
cutter_active = False
cutter_active_duration = 5.0
cutter_active_time = 0.0
cutter_blade_distance = 60
cutter_blade_size = 10
cutter_rotation_angle = 0.0
cutter_rotation_speed = 0.25
# (Overdrive removed) No chargeable ability present

# Enemy setup
class Enemy:
    def __init__(self, x, y, enemy_type):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.type = enemy_type
        self.health = 1 if enemy_type == EnemyType.DRONE else (1.5 if enemy_type == EnemyType.FIGHTER else 3)
        self.alpha = 0  # for fade-in warp entry
    
    def draw(self, surface):
        # Fade in warp effect
        self.alpha = min(255, self.alpha + 12)
        surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        if self.type == EnemyType.DRONE:
            # Small cyan drone
            pygame.draw.rect(surf, (CYAN[0], CYAN[1], CYAN[2], self.alpha), (0, 0, self.rect.width, self.rect.height))
            pygame.draw.circle(surf, (NEON_GREEN[0], NEON_GREEN[1], NEON_GREEN[2], self.alpha), (self.rect.width//2, self.rect.height//2), 8, 2)
        elif self.type == EnemyType.FIGHTER:
            # Pink fighter - draw polygon on surf
            points = [
                (self.rect.width//2, 0),
                (self.rect.width, self.rect.height//2),
                (self.rect.width//2, self.rect.height),
                (0, self.rect.height//2)
            ]
            pygame.draw.polygon(surf, (NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], self.alpha), points)
        else:  # CAPITAL
            # Large purple capital ship
            pygame.draw.rect(surf, (NEON_PURPLE[0], NEON_PURPLE[1], NEON_PURPLE[2], self.alpha), (0, 0, self.rect.width, self.rect.height))
            pygame.draw.circle(surf, (CYAN[0], CYAN[1], CYAN[2], self.alpha), (self.rect.width//2, self.rect.height//2), 15, 2)
        surface.blit(surf, self.rect.topleft)

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
        elif self.type == PowerUpType.INVINCIBILITY:
            pygame.draw.rect(surface, NEON_PINK, self.rect)
            pygame.draw.circle(surface, NEON_PINK, self.rect.center, 12, 2)
        elif self.type == PowerUpType.ORBITAL:
            pygame.draw.rect(surface, (255,160,0), self.rect)
            pygame.draw.circle(surface, (255,220,120), self.rect.center, 8, 2)
        elif self.type == PowerUpType.CUTTER:
            pygame.draw.rect(surface, (200,200,255), self.rect)
            pygame.draw.line(surface, (150,180,220), (self.rect.left, self.rect.centery), (self.rect.right, self.rect.centery), 2)

powerups = []

# Missile setup
missiles = []
missile_speed = 8

# Score and Lives
score = 0
high_score = load_high_score()
lives = 3
font = pygame.font.Font("space age.ttf", 24)
large_font = pygame.font.Font("space age.ttf", 48)
small_font = pygame.font.Font("space age.ttf", 16)

clock = pygame.time.Clock()

# Game States
PLAYING = 0
GAME_OVER = 1
PAUSED = 2
game_state = PLAYING

# Thruster spawn function
def spawn_thruster():
    for _ in range(2):
        particles.append(Particle(
            player.centerx + random.randint(-6, 6),
            player.bottom + random.randint(0, 4),
            random.uniform(-0.8, 0.8),
            random.uniform(1.8, 3.2),
            lifetime=18,
            color=(150, 200, 255)
        ))

def draw_window():
    global screen_shake
    
    # Apply screen shake
    shake_x = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
    shake_y = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
    
    screen.fill(BLACK_SPACE)
    
    # Draw and update starfield (moving downward for parallax)
    # We'll draw glow by using small per-star surfaces (keeps alpha)
    for s in stars:
        # s = [x, y, size, speed]
        s[1] += s[3]
        if s[1] > HEIGHT:
            s[1] = 0
            s[0] = random.randint(0, WIDTH)
            s[2] = random.choice([1, 2])
            s[3] = random.uniform(0.5, 1.8)
        color = WHITE if s[2] == 1 else (180, 230, 255)
        # main star
        pygame.draw.circle(screen, color, (int(s[0]), int(s[1])), s[2])
        # glow
        glow_size = s[2] + 3
        glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
        # alpha a bit subtle
        pygame.draw.circle(glow_surf, (color[0], color[1], color[2], 40), (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (int(s[0])-glow_size, int(s[1])-glow_size))
    
    # Draw particles
    for particle in particles[:]:
        particle.draw(screen)
    
    # Draw shockwaves
    for sw in shockwaves:
        sw.draw(screen)
    
    # Draw player (starship)
    if player_invincible and int(player_invincible_time * 10) % 2:
        # Draw glowing warp shield around player
        pygame.draw.circle(screen, NEON_PINK, (player.centerx, player.centery), 60, 2)
        pygame.draw.circle(screen, NEON_PINK, (player.centerx, player.centery), 50, 1)
        pygame.draw.polygon(screen, NEON_PINK, [
            (player.centerx, player.top + shake_x),
            (player.right, player.centery + shake_y),
            (player.centerx, player.bottom + shake_x),
            (player.left, player.centery + shake_y)
        ])
        # Add warp particles around player during invincibility
        if random.random() < 0.3:
            particles.append(Particle(
                player.centerx + random.randint(-40, 40),
                player.centery + random.randint(-40, 40),
                random.uniform(-2, 2),
                random.uniform(-2, 2),
                lifetime=20,
                color=NEON_PINK
            ))
    else:
        pygame.draw.polygon(screen, CYAN, [
            (player.centerx, player.top + shake_x),
            (player.right, player.centery + shake_y),
            (player.centerx, player.bottom + shake_x),
            (player.left, player.centery + shake_y)
        ])
    
    if player_shield:
        pygame.draw.circle(screen, SHIELD_COLOR, player.center, 60, 3)
    
    if orbital_charging and int(orbital_charge_time * 10) % 2:
        # Draw flashing orange orbital shield during charge-up
        pygame.draw.circle(screen, (255, 200, 50), (player.centerx, player.centery), 70, 3)
        pygame.draw.circle(screen, (255, 200, 50), (player.centerx, player.centery), 55, 1)
    
    # Draw enemies
    for enemy in enemies:
        enemy.draw(screen)
    
    # Draw power-ups
    for powerup in powerups:
        powerup.draw(screen)

    # Draw orbital beam strike if active (cone shape that expands to screen width)
    if orbital_beam_active:
        beam_x = player.centerx
        beam_top = 0
        beam_bottom = player.top
        # Cone expands from narrow at player to full screen width at top
        cone_width_bottom = 40  # narrow at player
        cone_width_top = WIDTH  # expand to full screen width at top
        # draw cone as a triangle (opaque white)
        cone_points = [
            (beam_x - cone_width_bottom // 2, beam_bottom),
            (beam_x + cone_width_bottom // 2, beam_bottom),
            (beam_x + cone_width_top // 2, beam_top),
            (beam_x - cone_width_top // 2, beam_top)
        ]
        beam_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(beam_surf, (255, 255, 255, 200), cone_points)
        # glow effect around cone
        pygame.draw.polygon(beam_surf, (200, 200, 255, 120), cone_points, 3)
        screen.blit(beam_surf, (0, 0))

    # Draw cutter blades if active
    if cutter_active:
        cx, cy = player.centerx, player.centery
        for i in range(4):
            angle = cutter_rotation_angle + math.pi/4 + i * (math.pi/2)
            bx = cx + math.cos(angle) * cutter_blade_distance
            by = cy + math.sin(angle) * cutter_blade_distance
            # blade body
            pygame.draw.circle(screen, (200, 200, 220), (int(bx), int(by)), cutter_blade_size)
            # blade glow (use a small surface)
            glow = pygame.Surface((cutter_blade_size*3, cutter_blade_size*3), pygame.SRCALPHA)
            pygame.draw.circle(glow, (150, 180, 220, 120), (cutter_blade_size, cutter_blade_size), cutter_blade_size+3)
            screen.blit(glow, (int(bx)-cutter_blade_size, int(by)-cutter_blade_size))
    
    # Draw laser missiles
    for missile in missiles:
            # Normal green missiles
            pygame.draw.line(screen, NEON_GREEN, (missile.centerx, missile.top), (missile.centerx, missile.bottom), 3)
            pygame.draw.circle(screen, NEON_GREEN, missile.center, 2)
    
    # Draw UI with neon styling
    score_text = font.render(f"SCORE: {score}", True, NEON_GREEN)
    lives_text = font.render(f"SHIPS: {lives}", True, RED)
    high_score_text = small_font.render(f"HIGH: {high_score}", True, CYAN)
    screen.blit(score_text, (10, 10))
    screen.blit(lives_text, (WIDTH - 180, 10))
    screen.blit(high_score_text, (WIDTH - 180, 40))
    # (Removed overdrive UI)
    
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
    
    if orbital_charging:
        orbital_text = small_font.render(f"CHARGING: {orbital_charge_time:.1f}s", True, (255, 200, 50))
        screen.blit(orbital_text, (10, 100))
    
    # Apply CRT filter with slight opacity (scanlines)
    screen.blit(crt_surface, (0, 0))

    
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
    global rapid_fire, rapid_fire_time, rapid_fire_counter
    global orbital_count, orbital_beam_active, orbital_charging, orbital_charge_time
    global cutter_charging, cutter_charge_time, cutter_active, cutter_active_time, cutter_rotation_angle
    score = 0
    lives = 3
    enemy_speed = 4
    spawn_rate = 25
    enemies.clear()
    missiles.clear()
    powerups.clear()
    particles.clear()
    shockwaves.clear()
    player.x = WIDTH // 2
    player_shield = False
    player_shield_time = 0
    player_invincible = False
    player_invincible_time = 0
    rapid_fire = False
    rapid_fire_time = 0
    rapid_fire_counter = 0
    orbital_count = 0
    orbital_charging = False
    orbital_charge_time = 0
    orbital_beam_active = False
    # reset cutter state
    cutter_charging = False
    cutter_charge_time = 0
    cutter_active = False
    cutter_active_time = 0
    cutter_rotation_angle = 0.0
    game_state = PLAYING

def main():
    global score, lives, enemy_speed, spawn_rate, game_state, high_score, screen_shake
    global player_shield, player_shield_time, player_invincible, player_invincible_time
    global rapid_fire, rapid_fire_time, rapid_fire_counter
    global orbital_count, orbital_charging, orbital_charge_duration, orbital_charge_time
    global orbital_beam_active, orbital_beam_time, orbital_beam_duration, orbital_beam_width
    # Cutter globals
    global cutter_charging, cutter_charge_duration, cutter_charge_time
    global cutter_active, cutter_active_duration, cutter_active_time, cutter_rotation_angle, cutter_rotation_speed, cutter_blade_distance, cutter_blade_size
    
    running = True
    running = True
    
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
                # (Overdrive activation removed)
        
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
        moving = False
        if keys[pygame.K_a] and player.left > 0:
            player.x -= player_speed
            moving = True
        if keys[pygame.K_d] and player.right < WIDTH:
            player.x += player_speed
            moving = True
        if keys[pygame.K_w] and player.top > 50:
            player.y -= player_speed
            moving = True
        if keys[pygame.K_s] and player.bottom < HEIGHT:
            player.y += player_speed
            moving = True
        
        # Thruster particles if moving
        if moving:
            spawn_thruster()
        
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
            # Slow enemies while cutter is active (instead of full freeze)
            if cutter_active:
                speed = enemy_speed * 0.2
            else:
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
                        shockwaves.append(Shockwave(player.centerx, player.centery))
                        if lives <= 0:
                            game_state = GAME_OVER
                            if score > high_score:
                                high_score = score
                                save_high_score(high_score)
                            # stop orbital sound if charging/active
                            try:
                                if globals().get('orbital_sound', None):
                                    globals()['orbital_sound'].stop()
                            except Exception:
                                pass
        
        # Power-up spawning (10% chance when enemy dies)
        # (handled in missile collision below)
        
        # Rapid fire automatic shooting
        if rapid_fire:
            rapid_fire_counter += 1
            if rapid_fire_counter >= 3:
                missiles.append(pygame.Rect(player.centerx - 5, player.top, 10, 20))
                # play rapid-fire effect if available, else fall back to normal shoot
                play_sound(rapid_fire_sound if 'rapid_fire_sound' in globals() and rapid_fire_sound else shoot_sound)
                rapid_fire_counter = 0
        
        # Power-up collection
        for powerup in powerups[:]:
            if powerup.rect.colliderect(player):
                # Play a sound specific to the power-up type if available
                if powerup.type == PowerUpType.SHIELD:
                    play_sound(globals().get('shield_sound', None) or globals().get('powerup_sound', None))
                    player_shield = True
                    player_shield_time = 5
                elif powerup.type == PowerUpType.RAPID_FIRE:
                    # play a short rapid-fire pickup sound if available
                    play_sound(globals().get('rapid_fire_sound', None) or globals().get('powerup_sound', None))
                    rapid_fire = True
                    rapid_fire_time = 8
                elif powerup.type == PowerUpType.INVINCIBILITY:
                    play_sound(globals().get('warp_sound', None) or globals().get('powerup_sound', None))
                    player_invincible = True
                    player_invincible_time = 5
                elif powerup.type == PowerUpType.ORBITAL:
                    # collect an orbital satellite and start charging
                    play_sound(globals().get('orbital_sound', None) or globals().get('powerup_sound', None))
                    orbital_count += 1
                    orbital_charging = True
                    orbital_charge_time = orbital_charge_duration
                    # Make the orbital shield behave like warp: invincible during charge and beam
                    player_invincible = True
                    # total invincibility covers charge duration + beam duration
                    player_invincible_time = orbital_charge_duration + orbital_beam_duration
                elif powerup.type == PowerUpType.CUTTER:
                    # collect cutter upgrade and start charging (rare)
                    play_sound(globals().get('cutter_sound', None) or globals().get('powerup_sound', None))
                    cutter_charging = True
                    cutter_charge_time = cutter_charge_duration
                    # no auto-invincibility for cutter; only freezes enemies when active
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
                            # Count kill and apply score
                            base_score = 1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3)
                            score += base_score

                            # Power-up drop
                            if random.random() < 0.15:
                                powerup_type = random.choices(
                                    [PowerUpType.SHIELD, PowerUpType.RAPID_FIRE, PowerUpType.INVINCIBILITY, PowerUpType.ORBITAL, PowerUpType.CUTTER],
                                    weights=[35, 30, 20, 15, 15]
                                )[0]
                                powerups.append(PowerUp(enemy.rect.centerx, enemy.rect.centery, powerup_type))
                        
                        if missile in missiles:
                            missiles.remove(missile)
                        hit = True
                        break

        # Cutter blades collision (damage enemies that touch blades)
        if cutter_active:
            cx, cy = player.centerx, player.centery
            blades = []
            for i in range(4):
                angle = cutter_rotation_angle + math.pi/4 + i * (math.pi/2)
                bx = cx + math.cos(angle) * cutter_blade_distance
                by = cy + math.sin(angle) * cutter_blade_distance
                blades.append((bx, by))
            for enemy in enemies[:]:
                hit_by_blade = False
                for bx, by in blades:
                    if enemy.rect.collidepoint(int(bx), int(by)):
                        # play cutter sound and spawn particles
                        play_sound(globals().get('cutter_sound', None) or globals().get('powerup_sound', None))
                        for _ in range(12):
                            particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, random.uniform(-4, 4), random.uniform(-4, 4), color=(200,200,255)))
                        # apply damage and score
                        base_score = 1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3)
                        try:
                            enemies.remove(enemy)
                            score += base_score
                        except ValueError:
                            pass
                        hit_by_blade = True
                        break
                if hit_by_blade:
                    continue
        
        # Update particles
        for particle in particles[:]:
            if not particle.update():
                try:
                    particles.remove(particle)
                except ValueError:
                    pass
        
        # Update shockwaves
        for sw in shockwaves[:]:
            if not sw.update():
                try:
                    shockwaves.remove(sw)
                except ValueError:
                    pass
        
        # Update orbitals (charging then beam)
        if orbital_charging:
            orbital_charge_time -= 1/30
            if orbital_charge_time <= 0:
                # charge finished, activate the beam
                orbital_charging = False
                orbital_beam_active = True
                orbital_beam_time = orbital_beam_duration
                # Make sure player remains invincible during the beam (like warp)
                player_invincible = True
                # ensure at least beam duration remains (don't cut off any charge-time left)
                player_invincible_time = max(player_invincible_time, orbital_beam_duration)
                # Spawn multiple enemies during orbital strike
                for _ in range(8):
                    enemy_type = random.choices([EnemyType.DRONE, EnemyType.FIGHTER, EnemyType.CAPITAL], weights=[50, 35, 15])[0]
                    x = random.randint(0, WIDTH - 40)
                    enemies.append(Enemy(x, -40, enemy_type))
        
            # Update cutter active timer and rotation
            if cutter_active:
                cutter_active_time -= 1/30
                cutter_rotation_angle += cutter_rotation_speed
                if cutter_active_time <= 0:
                    cutter_active = False
                    cutter_rotation_angle = 0.0

        # Update cutter (charging then active blades)
        if cutter_charging:
            cutter_charge_time -= 1/30
            if cutter_charge_time <= 0:
                cutter_charging = False
                cutter_active = True
                cutter_active_time = cutter_active_duration
                # play cutter activation sound if available
                play_sound(globals().get('cutter_sound', None) or globals().get('powerup_sound', None))
        
        # Update orbitals (beam collision)
        if orbital_beam_active:
            orbital_beam_time -= 1/30
            # check collisions between beam and enemies (using cone polygon)
            cone_width_bottom = 40
            cone_width_top = WIDTH
            cone_points = [
                (player.centerx - cone_width_bottom // 2, player.top),
                (player.centerx + cone_width_bottom // 2, player.top),
                (player.centerx + cone_width_top // 2, 0),
                (player.centerx - cone_width_top // 2, 0)
            ]
            enemies_hit = []
            for enemy in enemies[:]:
                # More precise cone collision: check if enemy is within expanding cone
                enemy_y = enemy.rect.centery
                if 0 <= enemy_y <= player.top:
                    # Calculate cone width at enemy's y position
                    progress = 1 - (enemy_y / player.top)  # 0 at player, 1 at top
                    width_at_y = cone_width_bottom + (cone_width_top - cone_width_bottom) * progress
                    cone_x_left = player.centerx - width_at_y / 2
                    cone_x_right = player.centerx + width_at_y / 2
                    if cone_x_left <= enemy.rect.centerx <= cone_x_right:
                        enemies_hit.append(enemy)
                        for _ in range(15):
                            particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, random.uniform(-5, 5), random.uniform(-5, 5), color=(255,255,255)))
                        score += (1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3))
            # remove all hit enemies
            for enemy in enemies_hit:
                try:
                    enemies.remove(enemy)
                except ValueError:
                    pass
            # end beam after duration
            if orbital_beam_time <= 0:
                orbital_beam_active = False
                # stop orbital sound
                try:
                    if globals().get('orbital_sound', None):
                        globals()['orbital_sound'].stop()
                except Exception:
                    pass

        # (Overdrive removed)
        
        draw_window()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
