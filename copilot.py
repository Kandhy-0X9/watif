# copilot.py
# Starship Defense (single-file Pygame shooter) - Patched with Cutter + Artillery
# - Cutter: pickup → 5s spin of 4 blades (instant-kill on touch) → blades launch outward → explosion radius kills enemies
# - Artillery: rare pickup → press R to target (full freeze) → click to choose impact → game resumes → shell hits after 0.5s → huge explosion (can kill player)
# - Preserves all existing systems (plasma, overdrive, orbital, audio auto-detect, particles, shockwaves, HUD, difficulty scaling)
# - Clean: integrated new artillery system and added power-up spawn weight

import pygame
import random
import sys
import json
import os
import math
from enum import Enum

# =============================================================================
#  Starship Defense (single-file Pygame shooter) - Patched (complete)
# =============================================================================

# --- Pygame init (video + audio)
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass  # allow running without audio device

# --- Screen setup
WIDTH, HEIGHT = 1200, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Starship Defense")

# Screen shake magnitude (frames) used after taking a hit
screen_shake = 0

# --- CRT overlay (scanlines)
crt_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for y in range(0, HEIGHT, 4):
    pygame.draw.line(crt_surface, (0, 0, 0, 45), (0, y), (WIDTH, y))

# --- Palette
BLACK_SPACE = (5, 5, 20)
CYAN = (0, 255, 255)
NEON_GREEN = (0, 255, 100)
NEON_PINK = (255, 0, 200)
NEON_PURPLE = (150, 0, 255)
DARK_BLUE = (10, 50, 100)
WHITE = (220, 220, 255)
SHIELD_COLOR = (100, 200, 255)
RED = (255, 50, 50)

# --- Enumerations
class EnemyType(Enum):
    DRONE = 1
    FIGHTER = 2
    CAPITAL = 3


class PowerUpType(Enum):
    SHIELD = 1
    RAPID_FIRE = 2
    INVINCIBILITY = 3
    ORBITAL = 4
    PLASMA = 5
    CUTTER = 6           # newly added cutter power-up
    ARTILLERY = 7        # newly added artillery power-up

# --- Particle system
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
        size = max(1, int(3 * (1 - self.age / self.lifetime)))
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        draw_color = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(surf, draw_color, (size, size), size)
        surface.blit(surf, (int(self.x) - size, int(self.y) - size))


particles = []

# --- Shockwaves
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
        pygame.draw.circle(surf, (255, 255, 255, max(0, self.alpha)), (size // 2, size // 2), int(self.radius), 3)
        surface.blit(surf, (int(self.x) - size // 2, int(self.y) - size // 2))


shockwaves = []

# --- Background starfield
NUM_STARS = 80
stars = []
for _ in range(NUM_STARS):
    stars.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), random.choice([1, 2]), random.uniform(0.5, 1.8)])

# --- Audio helpers

def load_sound(filename):
    try:
        return pygame.mixer.Sound(filename)
    except Exception:
        return None


def play_sound(sound):
    if sound:
        try:
            sound.play()
        except Exception:
            pass

# --- Audio auto-mapping
shoot_sound = None
hit_sound = None
powerup_sound = None
rapid_fire_sound = None
shield_sound = None
warp_sound = None
orbital_sound = None
plasma_sound = None
overdrive_sound = None
bg_music_file = None
artillery_sound = None


audio_files = [f for f in os.listdir('.') if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
if audio_files:
    for f in audio_files:
        if any(k in f.lower() for k in ('background', 'bg', 'music', 'ambient')):
            bg_music_file = f
            break
    if not bg_music_file:
        bg_music_file = audio_files[0]

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

    shoot_candidate = pick_file(('laser', 'shoot', 'gun', 'pew', 'zap'))
    hit_candidate = pick_file(('hit', 'explode', 'explosion', 'boom', 'impact'), exclude=bg_music_file)
    powerup_candidate = pick_file(('powerup', 'power', 'pickup', 'collect', 'ping'), exclude=bg_music_file)
    rapid_candidate = pick_file(('burst', 'rapid', 'auto', 'blip'), exclude=bg_music_file)
    orbital_candidate = pick_file(('orbital', 'orb', 'satellite', 'deploy', 'launch'), exclude=bg_music_file)
    plasma_candidate = pick_file(('plasma', 'blast', 'blaster', 'wave'), exclude=bg_music_file)
    overdrive_candidate = pick_file(('overdrive',), exclude=bg_music_file)
    artillery_candidate = pick_file(('artillery', 'shell', 'bomb', 'strike'), exclude=bg_music_file)
    if not shoot_candidate:
        shoot_candidate = pick_file(('laser', 'shoot', 'gun')) or (audio_files[0] if audio_files else None)
    if not hit_candidate:
        hit_candidate = pick_file(('explode', 'hit'))
    if not powerup_candidate:
        powerup_candidate = pick_file(('powerup', 'pickup', 'ping'))
        shield_candidate = pick_file(('shield', 'sheild'), exclude=bg_music_file)
        warp_candidate = pick_file(('warp', 'invinc', 'invulnerability'), exclude=bg_music_file)
    if not rapid_candidate:
        rapid_candidate = pick_file(('burst', 'rapid'))
    
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
    if plasma_candidate:
        plasma_sound = load_sound(plasma_candidate)
    else:
        plasma_sound = None
    if overdrive_candidate:
        overdrive_sound = load_sound(overdrive_candidate)
    else:
        overdrive_sound = None
    # Load explosion sound manually
    if artillery_candidate:
        artillery_sound = load_sound("strike.mp3")
    else:
        artillery_sound = None

# --- High score persistence
SCORE_FILE = "highscore.json"


def load_high_score():
    if os.path.exists(SCORE_FILE):
        try:
            with open(SCORE_FILE, 'r') as f:
                return json.load(f).get('high_score', 0)
        except Exception:
            return 0
    return 0


def save_high_score(score):
    with open(SCORE_FILE, 'w') as f:
        json.dump({'high_score': score}, f)

# --- Player state
player_size = 50
player = pygame.Rect(WIDTH // 2, HEIGHT - player_size - 10, player_size, player_size)
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
orbital_charge_duration = 12.0
orbital_charge_time = 0.0
orbital_beam_active = False
orbital_beam_duration = 2.0
orbital_beam_time = 0.0
orbital_beam_width = 80

# --- Plasma globals
plasma_active = False
plasma_radius = 0.0
plasma_max_radius = 160.0
plasma_expand_speed = 14.0
plasma_hits = set()

# --- Overdrive system (with cooldown + aura)
overdrive_points = 0
overdrive_ready = False
overdrive_active = False
overdrive_timer = 0.0
overdrive_cooldown = 8.0
overdrive_on_cooldown = False
overdrive_cd_timer = 0.0

# --- Cutter (orbiting blades) globals (NEW)
cutter_active = False
cutter_active_time = 0.0        # spin duration remaining (seconds)
cutter_spin_duration = 5.0     # user requested 5 seconds
cutter_spin_radius = 72        # orbit radius while spinning
cutter_blade_count = 4
cutter_blades = []             # list of CutterBlade instances
blade_launch_speed = 9.0       # speed when blades fling outward
blade_size = 12                # visual size for blades
blade_explosion_radius = 72    # big explosion radius on impact (kills enemies)

# --- Artillery globals (NEW)
artillery_available = 0        # number of artillery charges the player has
artillery_targeting = False    # true while the game is frozen and player picks a target
artillery_pending = False      # true after target picked, countdown until impact
artillery_target_pos = (0, 0)
artillery_drop_delay = 0.5     # user requested 0.5s delay after click
artillery_drop_timer = 0.0
artillery_radius = 240         # user requested HUGE radius (240 px)
artillery_activation_key = pygame.K_r

# --- Enemy entity
class Enemy:
    def __init__(self, x, y, enemy_type):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.type = enemy_type
        self.health = 1 if enemy_type == EnemyType.DRONE else (1.5 if enemy_type == EnemyType.FIGHTER else 3)
        self.alpha = 0

    def draw(self, surface):
        self.alpha = min(255, self.alpha + 12)
        surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        if self.type == EnemyType.DRONE:
            pygame.draw.ellipse(surf, (CYAN[0], CYAN[1], CYAN[2], self.alpha), (0, 0, self.rect.width, self.rect.height))
            pygame.draw.circle(surf, (NEON_GREEN[0], NEON_GREEN[1], NEON_GREEN[2], self.alpha), (self.rect.width // 2, self.rect.height // 2), 6, 2)
        elif self.type == EnemyType.FIGHTER:
            points = [(self.rect.width // 2, 0), (self.rect.width, self.rect.height // 2), (self.rect.width // 2, self.rect.height), (0, self.rect.height // 2)]
            pygame.draw.polygon(surf, (NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], self.alpha), points)
            pygame.draw.polygon(surf, (255,255,255,self.alpha//3), points, 2)
        else:
            pygame.draw.rect(surf, (NEON_PURPLE[0], NEON_PURPLE[1], NEON_PURPLE[2], self.alpha), (0, 0, self.rect.width, self.rect.height))
            pygame.draw.circle(surf, (CYAN[0], CYAN[1], CYAN[2], self.alpha), (self.rect.width // 2, self.rect.height // 2), 12, 2)

        surface.blit(surf, self.rect.topleft)


enemies = []
enemy_speed = 4
spawn_rate = 25

# --- Power-ups
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
            pygame.draw.rect(surface, (255, 160, 0), self.rect)
            pygame.draw.circle(surface, (255, 220, 120), self.rect.center, 8, 2)
        elif self.type == PowerUpType.PLASMA:
            pygame.draw.rect(surface, (30, 30, 40), self.rect)
            pygame.draw.circle(surface, (0, 200, 200), self.rect.center, 9, 2)
            pygame.draw.circle(surface, WHITE, self.rect.center, 5)
        elif self.type == PowerUpType.CUTTER:
            # Visual: pick a neutral silver/white icon
            pygame.draw.rect(surface, (180, 180, 200), self.rect)
            cx, cy = self.rect.center
            # small triangular blade icon
            pygame.draw.polygon(surface, WHITE, [(cx - 6, cy + 6), (cx + 10, cy), (cx - 6, cy - 6)])
            pygame.draw.circle(surface, (220, 220, 220), self.rect.center, 5, 1)
        elif self.type == PowerUpType.ARTILLERY:
            # Visual: a simple artillery icon (crosshair + dot)
            pygame.draw.rect(surface, (160, 160, 200), self.rect)
            cx, cy = self.rect.center
            pygame.draw.circle(surface, RED, (cx, cy), 4)
            pygame.draw.line(surface, WHITE, (cx - 6, cy), (cx + 6, cy), 1)
            pygame.draw.line(surface, WHITE, (cx, cy - 6), (cx, cy + 6), 1)


powerups = []

# --- Missiles
missiles = []
missile_speed = 8

# --- Score + UI
score = 0
high_score = load_high_score()
lives = 3
try:
    font = pygame.font.Font("space age.ttf", 24)
    large_font = pygame.font.Font("space age.ttf", 48)
    small_font = pygame.font.Font("space age.ttf", 16)
except Exception:
    font = pygame.font.SysFont(None, 24)
    large_font = pygame.font.SysFont(None, 48)
    small_font = pygame.font.SysFont(None, 16)

clock = pygame.time.Clock()

# --- Game states
PLAYING = 0
GAME_OVER = 1
PAUSED = 2

game_state = PLAYING

# --- Helper
def spawn_thruster():
    for _ in range(2):
        particles.append(Particle(player.centerx + random.randint(-6, 6), player.bottom + random.randint(0, 4), random.uniform(-0.8, 0.8), random.uniform(1.8, 3.2), lifetime=18, color=(150, 200, 255)))

# --- CutterBlade class (NEW)
class CutterBlade:
    def __init__(self, angle, radius=cutter_spin_radius):
        self.angle = angle        # current angle (radians)
        self.radius = radius      # orbit radius while spinning
        self.state = 'orbit'      # 'orbit' or 'launched'
        self.x = player.centerx + math.cos(self.angle) * self.radius
        self.y = player.centery + math.sin(self.angle) * self.radius
        self.vx = 0.0
        self.vy = 0.0
        self.size = blade_size
        self.rect = pygame.Rect(int(self.x - self.size//2), int(self.y - self.size//2), self.size, self.size)

    def update_orbit(self, spin_speed=0.16):
        # spin_speed is radians per frame (approx for 30 fps)
        self.angle += spin_speed
        self.x = player.centerx + math.cos(self.angle) * self.radius
        self.y = player.centery + math.sin(self.angle) * self.radius
        self.rect.center = (int(self.x), int(self.y))

    def launch(self):
        # outward velocity based on current angle
        self.state = 'launched'
        self.vx = math.cos(self.angle) * blade_launch_speed
        self.vy = math.sin(self.angle) * blade_launch_speed

    def update_launched(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface):
        # draw a small rotating shard / blade with simple triangle
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pts = [(self.size, 0), (self.size*2 - 2, self.size), (2, self.size)]
        pygame.draw.polygon(surf, (200, 220, 255, 220), pts)
        pygame.draw.polygon(surf, (255,255,255,80), pts, 1)
        rot = pygame.transform.rotate(surf, (self.angle * 180 / math.pi) % 360)
        rrect = rot.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rot, rrect.topleft)


# --- Draw frame
def draw_window():
    global screen_shake, plasma_active, plasma_radius
    global overdrive_ready, overdrive_active, overdrive_timer, overdrive_on_cooldown, overdrive_cd_timer

    shake_x = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
    shake_y = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0

    screen.fill(BLACK_SPACE)

    # Stars
    for s in stars:
        s[1] += s[3]
        if s[1] > HEIGHT:
            s[1] = 0
            s[0] = random.randint(0, WIDTH)
            s[2] = random.choice([1, 2])
            s[3] = random.uniform(0.5, 1.8)
        color = WHITE if s[2] == 1 else (180, 230, 255)
        pygame.draw.circle(screen, color, (int(s[0]), int(s[1])), s[2])
        glow_size = s[2] + 3
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (color[0], color[1], color[2], 40), (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (int(s[0]) - glow_size, int(s[1]) - glow_size))

    # Particles
    for particle in particles:
        particle.draw(screen)
    for sw in shockwaves:
        sw.draw(screen)

    # Player
    if player_invincible and int(player_invincible_time * 10) % 2:
        pygame.draw.circle(screen, NEON_PINK, (player.centerx, player.centery), 60, 2)
        pygame.draw.circle(screen, NEON_PINK, (player.centerx, player.centery), 50, 1)
        pygame.draw.polygon(screen, NEON_PINK, [(player.centerx, player.top + shake_x), (player.right, player.centery + shake_y), (player.centerx, player.bottom + shake_x), (player.left, player.centery + shake_y)])
        if random.random() < 0.3:
            particles.append(Particle(player.centerx + random.randint(-40, 40), player.centery + random.randint(-40, 40), random.uniform(-2, 2), random.uniform(-2, 2), lifetime=20, color=NEON_PINK))
    else:
        pygame.draw.polygon(screen, CYAN, [(player.centerx, player.top + shake_x), (player.right, player.centery + shake_y), (player.centerx, player.bottom + shake_x), (player.left, player.centery + shake_y)])

    if player_shield:
        pygame.draw.circle(screen, SHIELD_COLOR, player.center, 60, 3)

    # Orbital cue
    if orbital_charging and int(orbital_charge_time * 10) % 2:
        pygame.draw.circle(screen, (255, 200, 50), (player.centerx, player.centery), 70, 3)
        pygame.draw.circle(screen, (255, 200, 50), (player.centerx, player.centery), 55, 1)

    # Enemies & powerups
    for enemy in enemies:
        enemy.draw(screen)
    for powerup in powerups:
        powerup.draw(screen)

    # Plasma ring
    if plasma_active:
        ring_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (0, 255, 255, 180), player.center, int(plasma_radius), 6)
        inner = max(1, int(plasma_radius * 0.65))
        pygame.draw.circle(ring_surf, (200, 255, 255, 80), player.center, inner, 2)
        screen.blit(ring_surf, (0, 0))
        if random.random() < 0.6:
            angle = random.random() * math.tau
            px = player.centerx + math.cos(angle) * plasma_radius
            py = player.centery + math.sin(angle) * plasma_radius
            particles.append(Particle(px, py, random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8), lifetime=20, color=(0, 255, 255)))

    # Orbital beam
    if orbital_beam_active:
        beam_x = player.centerx
        beam_top = 0
        beam_bottom = player.top
        cone_width_bottom = 40
        cone_width_top = WIDTH
        cone_points = [(beam_x - cone_width_bottom // 2, beam_bottom), (beam_x + cone_width_bottom // 2, beam_bottom), (beam_x + cone_width_top // 2, beam_top), (beam_x - cone_width_top // 2, beam_top)]
        beam_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(beam_surf, (255, 255, 255, 200), cone_points)
        pygame.draw.polygon(beam_surf, (200, 200, 255, 120), cone_points, 3)
        screen.blit(beam_surf, (0, 0))

    # Missiles (upgraded visuals)
    for missile in missiles:
        # Choose color based on overdrive
        bullet_color = CYAN if overdrive_active else NEON_GREEN

        # Core glow
        pygame.draw.circle(screen, bullet_color, missile.center, 3)

        # Tail: short comet streak using an alpha surface
        tail_length = 18
        tail_surf = pygame.Surface((6, tail_length), pygame.SRCALPHA)
        for i in range(tail_length):
            alpha = max(0, 200 - int((i / tail_length) * 180))
            pygame.draw.line(tail_surf, (bullet_color[0], bullet_color[1], bullet_color[2], alpha), (3, tail_length), (3, tail_length - i), 3 - i // 8)
        screen.blit(tail_surf, (missile.centerx - 3, missile.centery - tail_length // 2))

        # Overdrive twin-beam visual
        if overdrive_active:
            pygame.draw.line(screen, CYAN, (missile.centerx - 3, missile.bottom), (missile.centerx - 3, missile.top - 6), 2)
            pygame.draw.line(screen, CYAN, (missile.centerx + 3, missile.bottom), (missile.centerx + 3, missile.top - 6), 2)

    # Cutter blades (draw after player so they appear around the ship)
    if cutter_blades:
        for blade in cutter_blades:
            blade.draw(screen)

    # HUD
    score_text = font.render(f"SCORE: {score}", True, NEON_GREEN)
    lives_text = font.render(f"SHIPS: {lives}", True, RED)
    high_score_text = small_font.render(f"HIGH: {high_score}", True, CYAN)
    screen.blit(score_text, (10, 10))
    screen.blit(lives_text, (WIDTH - 180, 10))
    screen.blit(high_score_text, (WIDTH - 180, 40))

    if player_shield:
        shield_text = small_font.render(f"SHIELD: {player_shield_time:.1f}s", True, SHIELD_COLOR)
        screen.blit(shield_text, (10, 40))
    if rapid_fire:
        rapid_text = small_font.render(f"BURST: {rapid_fire_time:.1f}s", True, NEON_GREEN)
        screen.blit(rapid_text, (10, 60))
    if player_invincible:
        inv_text = small_font.render(f"WARP: {player_invincible_time:.1f}s", True, NEON_PINK)
        screen.blit(inv_text, (10, 80))
    if orbital_charging:
        orbital_text = small_font.render(f"CHARGING: {orbital_charge_time:.1f}s", True, (255, 200, 50))
        screen.blit(orbital_text, (10, 100))

    # Cutter timers
    if cutter_active:
        cutter_active_text = small_font.render(f"CUTTER ACTIVE: {cutter_active_time:.1f}s", True, (180, 220, 255))
        screen.blit(cutter_active_text, (10, 120))

    # Overdrive UI & cooldown
    if overdrive_ready:
        ready_text = small_font.render("OVERDRIVE READY", True, CYAN)
        screen.blit(ready_text, (10, 160))
    if overdrive_active:
        active_text = small_font.render(f"OVERDRIVE: {overdrive_timer:.1f}s", True, CYAN)
        screen.blit(active_text, (10, 180))
    if overdrive_on_cooldown:
        cd_text = small_font.render(f"OVR CD: {overdrive_cd_timer:.1f}s", True, (180, 180, 255))
        screen.blit(cd_text, (10, 200))

    # Artillery HUD
    artillery_text = small_font.render(f"ARTILLERY: {artillery_available}", True, (255, 200, 80))
    screen.blit(artillery_text, (10, 220))

    # Artillery targeting crosshair (when frozen targeting)
    if artillery_targeting:
        mx, my = pygame.mouse.get_pos()
        cx, cy = mx, my
        # red crosshair
        pygame.draw.line(screen, RED, (cx - 12, cy), (cx + 12, cy), 2)
        pygame.draw.line(screen, RED, (cx, cy - 12), (cx, cy + 12), 2)
        pygame.draw.circle(screen, (255, 100, 100), (cx, cy), 6, 2)
        target_hint = small_font.render("Click to confirm artillery strike", True, RED)
        screen.blit(target_hint, (cx + 16, cy - 8))

    # Overdrive aura: red burning ring (visual + damage region drawn elsewhere)
    if overdrive_active:
        burn_radius = 90
        aura_surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, (255, 60, 60, 160), (100, 100), burn_radius, 6)
        screen.blit(aura_surf, (player.centerx - 100, player.centery - 100), special_flags=pygame.BLEND_RGBA_ADD)

    # CRT overlay
    screen.blit(crt_surface, (0, 0))
    pygame.display.update()

    screen_shake = max(0, screen_shake - 1)


# --- Menus
def draw_game_over():
    screen.fill(BLACK_SPACE)
    game_over_text = large_font.render("MISSION FAILED", True, RED)
    final_score_text = font.render(f"FINAL SCORE: {score}", True, NEON_GREEN)
    high_score_text = font.render(f"HIGH SCORE: {high_score}", True, CYAN)
    restart_text = font.render("SPACE: Restart  |  Q: Quit", True, WHITE)
    screen.blit(game_over_text, (WIDTH // 2 - 160, HEIGHT // 2 - 120))
    screen.blit(final_score_text, (WIDTH // 2 - 150, HEIGHT // 2 - 20))
    screen.blit(high_score_text, (WIDTH // 2 - 160, HEIGHT // 2 + 20))
    screen.blit(restart_text, (WIDTH // 2 - 200, HEIGHT // 2 + 80))
    pygame.display.update()


def draw_pause():
    screen.fill(BLACK_SPACE)
    pause_text = large_font.render("SYSTEMS PAUSED", True, CYAN)
    resume_text = font.render("P: Resume", True, WHITE)
    screen.blit(pause_text, (WIDTH // 2 - 180, HEIGHT // 2 - 50))
    screen.blit(resume_text, (WIDTH // 2 - 110, HEIGHT // 2 + 50))
    pygame.display.update()


# --- Reset
def reset_game():
    global score, lives, enemy_speed, spawn_rate, game_state, high_score
    global player_shield, player_shield_time, player_invincible, player_invincible_time
    global rapid_fire, rapid_fire_time, rapid_fire_counter
    global orbital_count, orbital_beam_active, orbital_charging, orbital_charge_time
    global plasma_active, plasma_radius, plasma_hits
    global overdrive_points, overdrive_ready, overdrive_active, overdrive_timer, overdrive_on_cooldown, overdrive_cd_timer
    global cutter_active, cutter_active_time, cutter_blades
    global artillery_available, artillery_targeting, artillery_pending, artillery_drop_timer

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

    plasma_active = False
    plasma_radius = 0.0
    plasma_hits.clear()

    overdrive_points = 0
    overdrive_ready = False
    overdrive_active = False
    overdrive_timer = 0.0
    overdrive_on_cooldown = False
    overdrive_cd_timer = 0.0

    cutter_active = False
    cutter_active_time = 0.0
    cutter_blades.clear()

    artillery_available = 0
    artillery_targeting = False
    artillery_pending = False
    artillery_drop_timer = 0.0

    game_state = PLAYING


# --- Main loop
def main():
    global score, lives, enemy_speed, spawn_rate, game_state, high_score, screen_shake
    global player_shield, player_shield_time, player_invincible, player_invincible_time
    global rapid_fire, rapid_fire_time, rapid_fire_counter
    global orbital_count, orbital_charging, orbital_charge_duration, orbital_charge_time
    global orbital_beam_active, orbital_beam_time, orbital_beam_duration, orbital_beam_width
    global plasma_active, plasma_radius, plasma_max_radius, plasma_expand_speed, plasma_hits
    global overdrive_points, overdrive_ready, overdrive_active, overdrive_timer, overdrive_on_cooldown, overdrive_cd_timer
    global cutter_active, cutter_active_time, cutter_spin_duration, cutter_blades
    global artillery_available, artillery_targeting, artillery_pending, artillery_target_pos, artillery_drop_timer

    running = True

    while running:
        clock.tick(30)

        if game_state == PAUSED:
            draw_pause()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not artillery_targeting:
                    # fire missile
                    missiles.append(pygame.Rect(player.centerx - 5, player.top, 10, 20))
                    play_sound(overdrive_sound if overdrive_active else shoot_sound)
                    # muzzle flash particle
                    particles.append(Particle(player.centerx, player.top, random.uniform(-1, 1), -3, lifetime=12, color=(255, 255, 200)))
                if event.key == pygame.K_p:
                    game_state = PAUSED
                if event.key == pygame.K_e and overdrive_ready and not overdrive_active and not overdrive_on_cooldown and not artillery_targeting:
                    overdrive_active = True
                    overdrive_ready = False
                    overdrive_points = 0
                    overdrive_timer = 5.0
                    play_sound(overdrive_sound)
                    # small activation burst
                    for _ in range(12):
                        particles.append(Particle(player.centerx + random.uniform(-20, 20), player.centery + random.uniform(-20, 20), random.uniform(-3, 3), random.uniform(-3, 3), lifetime=30, color=(0, 230, 255)))
                if event.key == artillery_activation_key and artillery_available > 0 and not artillery_targeting and not artillery_pending and game_state == PLAYING:
                    # begin targeting: freeze the game visually and stop updates
                    artillery_targeting = True
                    # capture mouse so player can choose
                    pygame.mouse.set_visible(True)
                    play_sound(powerup_sound or overdrive_sound)

            # Mouse click handling during targeting
            if event.type == pygame.MOUSEBUTTONDOWN and artillery_targeting:
                mx, my = pygame.mouse.get_pos()
                artillery_target_pos = (mx, my)
                artillery_pending = True
                artillery_drop_timer = artillery_drop_delay
                artillery_targeting = False
                artillery_available = max(0, artillery_available - 1)
                # unhide/hide mouse as desired
                pygame.mouse.set_visible(False)
                # small confirmation burst on click (visual)
                for _ in range(8):
                    particles.append(Particle(mx + random.uniform(-8,8), my + random.uniform(-8,8), random.uniform(-2,2), random.uniform(-2,2), lifetime=18, color=(255,180,60)))
                # resume the game (updates continue)

        # If we're currently in targeting mode, we must render the frozen frame and skip all updates.
        if artillery_targeting:
            # draw the window (it will render current state + crosshair because draw_window uses artillery_targeting flag)
            draw_window()
            # do not progress game timers, enemy movement, particles, missiles, etc. (they appear frozen on screen)
            continue

        # Timers
        if player_shield:
            player_shield_time -= 1 / 30
            if player_shield_time <= 0:
                player_shield = False
        if rapid_fire:
            rapid_fire_time -= 1 / 30
            if rapid_fire_time <= 0:
                rapid_fire = False
        if player_invincible:
            player_invincible_time -= 1 / 30
            if player_invincible_time <= 0:
                player_invincible = False

        # Overdrive timer
        if overdrive_active:
            overdrive_timer -= 1 / 30
            if overdrive_timer <= 0:
                overdrive_active = False
                overdrive_on_cooldown = True
                overdrive_cd_timer = overdrive_cooldown
        if overdrive_on_cooldown:
            overdrive_cd_timer -= 1 / 30
            if overdrive_cd_timer <= 0:
                overdrive_on_cooldown = False
                overdrive_cd_timer = 0.0

        # Player movement
        keys = pygame.key.get_pressed()
        moving = False
        if keys[pygame.K_a] and player.left > 0:
            player.x -= (player_speed + 3 if overdrive_active else player_speed)
            moving = True
        if keys[pygame.K_d] and player.right < WIDTH:
            player.x += (player_speed + 3 if overdrive_active else player_speed)
            moving = True
        if keys[pygame.K_w] and player.top > 50:
            player.y -= (player_speed + 3 if overdrive_active else player_speed)
            moving = True
        if keys[pygame.K_s] and player.bottom < HEIGHT:
            player.y += (player_speed + 3 if overdrive_active else player_speed)
            moving = True
        if moving:
            spawn_thruster()

        # Plasma update
        if plasma_active:
            plasma_radius += plasma_expand_speed
            for enemy in enemies[:]:
                if id(enemy) in plasma_hits:
                    continue
                dx = enemy.rect.centerx - player.centerx
                dy = enemy.rect.centery - player.centery
                if dx * dx + dy * dy <= (plasma_radius * plasma_radius):
                    plasma_hits.add(id(enemy))
                    if enemy.type == EnemyType.CAPITAL:
                        enemy.health -= enemy.health * 0.5
                        for _ in range(12):
                            particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, random.uniform(-4, 4), random.uniform(-4, 4), color=(0, 255, 255)))
                        if enemy.health <= 0:
                            try:
                                enemies.remove(enemy)
                            except ValueError:
                                pass
                            score += 3
                            overdrive_points += 1
                            if overdrive_points >= 5:
                                overdrive_ready = True
                    else:
                        for _ in range(15):
                            particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, random.uniform(-5, 5), random.uniform(-5, 5), color=(0, 255, 255)))
                        try:
                            enemies.remove(enemy)
                        except ValueError:
                            pass
                        score += 1 if enemy.type == EnemyType.DRONE else 2
            screen_shake = max(screen_shake, 3)
            if plasma_radius >= plasma_max_radius:
                plasma_active = False
                plasma_hits.clear()

        # Smooth continuous difficulty scaling
        enemy_speed = min(9, 4 + score * 0.03)
        spawn_rate = max(6, int(25 - score * 0.12))

        # Enemy spawn
        if random.randint(1, max(1, spawn_rate)) == 1:
            x_pos = random.randint(0, WIDTH - 40)
            enemy_type_choice = random.choices([EnemyType.DRONE, EnemyType.FIGHTER, EnemyType.CAPITAL], weights=[50, 30, 20])[0]
            enemies.append(Enemy(x_pos, 0, enemy_type_choice))

        # Enemy movement + collision
        for enemy in enemies[:]:
            # per-type speeds
            drone_speed = enemy_speed
            fighter_speed = enemy_speed * 1.5
            capital_speed = enemy_speed * 0.7

            if cutter_active:
                speed = enemy_speed * 0.2
            else:
                if enemy.type == EnemyType.DRONE:
                    speed = drone_speed
                elif enemy.type == EnemyType.FIGHTER:
                    speed = fighter_speed
                else:
                    speed = capital_speed

            enemy.rect.y += speed
            if enemy.rect.top > HEIGHT:
                try:
                    enemies.remove(enemy)
                except ValueError:
                    pass
            elif enemy.rect.colliderect(player):
                if not player_invincible:
                    if player_shield:
                        player_shield = False
                        play_sound(hit_sound)
                        for _ in range(8):
                            particles.append(Particle(player.centerx, player.centery, random.uniform(-3, 3), random.uniform(-3, 3)))
                        try:
                            enemies.remove(enemy)
                        except ValueError:
                            pass
                    else:
                        lives -= 1
                        screen_shake = 5
                        play_sound(hit_sound)
                        for _ in range(15):
                            particles.append(Particle(player.centerx, player.centery, random.uniform(-5, 5), random.uniform(-5, 5)))
                        try:
                            enemies.remove(enemy)
                        except ValueError:
                            pass
                        shockwaves.append(Shockwave(player.centerx, player.centery))
                        if lives <= 0:
                            game_state = GAME_OVER
                            if score > high_score:
                                high_score = score
                                save_high_score(high_score)
                            try:
                                if globals().get('orbital_sound', None):
                                    globals()['orbital_sound'].stop()
                            except Exception:
                                pass

        # --- Overdrive burning ring damage
        if overdrive_active:
            burn_radius = 90
            for enemy in enemies[:]:
                dx = enemy.rect.centerx - player.centerx
                dy = enemy.rect.centery - player.centery
                dist_sq = dx * dx + dy * dy
                if dist_sq <= burn_radius * burn_radius:
                    enemy.health -= 0.18
                    if random.random() < 0.35:
                        particles.append(Particle(enemy.rect.centerx + random.uniform(-6, 6),
                                                 enemy.rect.centery + random.uniform(-6, 6),
                                                 random.uniform(-2, 2),
                                                 random.uniform(-2, 2),
                                                 lifetime=14,
                                                 color=(255, 80, 30)))
                    if enemy.health <= 0:
                        try:
                            enemies.remove(enemy)
                        except ValueError:
                            pass
                        score += 1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3)
                        overdrive_points += 0.2
                        if overdrive_points >= 5:
                            overdrive_ready = True

        # Rapid fire
        if rapid_fire:
            rapid_fire_counter += 1
            if rapid_fire_counter >= 3:
                missiles.append(pygame.Rect(player.centerx - 5, player.top, 10, 20))
                play_sound(overdrive_sound if overdrive_active else (rapid_fire_sound if rapid_fire_sound else shoot_sound))
                rapid_fire_counter = 0

        # Power-up collection
        for powerup in powerups[:]:
            if powerup.rect.colliderect(player):
                if powerup.type == PowerUpType.SHIELD:
                    play_sound(shield_sound or powerup_sound)
                    player_shield = True
                    player_shield_time = 5
                elif powerup.type == PowerUpType.RAPID_FIRE:
                    play_sound(rapid_fire_sound or powerup_sound)
                    rapid_fire = True
                    rapid_fire_time = 8
                elif powerup.type == PowerUpType.INVINCIBILITY:
                    play_sound(warp_sound or powerup_sound)
                    player_invincible = True
                    player_invincible_time = 5
                elif powerup.type == PowerUpType.ORBITAL:
                    play_sound(orbital_sound or powerup_sound)
                    orbital_count += 1
                    orbital_charging = True
                    orbital_charge_time = orbital_charge_duration
                    player_invincible = True
                    player_invincible_time = orbital_charge_duration + orbital_beam_duration
                elif powerup.type == PowerUpType.PLASMA:
                    play_sound(plasma_sound or powerup_sound)
                    plasma_active = True
                    plasma_radius = 1.0
                    plasma_hits.clear()
                elif powerup.type == PowerUpType.CUTTER:
                    # activate cutter: begin spinning immediately for cutter_spin_duration
                    play_sound(powerup_sound or overdrive_sound)
                    cutter_blades.clear()
                    for i in range(cutter_blade_count):
                        ang = (i / cutter_blade_count) * math.tau
                        cutter_blades.append(CutterBlade(ang))
                    cutter_active = True
                    cutter_active_time = cutter_spin_duration
                elif powerup.type == PowerUpType.ARTILLERY:
                    # give the player one artillery charge
                    play_sound(powerup_sound or overdrive_sound)
                    artillery_available += 1
                try:
                    powerups.remove(powerup)
                except ValueError:
                    pass

        # Missile collision & movement
        for missile in missiles[:]:
            missile.y -= missile_speed
            if missile.bottom < 0:
                try:
                    missiles.remove(missile)
                except ValueError:
                    pass
                continue
            for enemy in enemies[:]:
                if missile.colliderect(enemy.rect):
                    enemy.health -= 1
                    for _ in range(10):
                        particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, random.uniform(-4, 4), random.uniform(-4, 4)))
                    if enemy.health <= 0:
                        try:
                            enemies.remove(enemy)
                        except ValueError:
                            pass
                        base_score = 1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3)
                        score += base_score
                        if enemy.type == EnemyType.CAPITAL:
                            overdrive_points += 1
                            if overdrive_points >= 5:
                                overdrive_ready = True
                        if random.random() < 0.25:
                            powerup_type = random.choices(
                                [PowerUpType.SHIELD, PowerUpType.RAPID_FIRE, PowerUpType.INVINCIBILITY, PowerUpType.ORBITAL, PowerUpType.PLASMA, PowerUpType.CUTTER, PowerUpType.ARTILLERY],
                                weights=[100, 60, 40, 10, 100, 50, 15]
                            )[0]
                            powerups.append(PowerUp(enemy.rect.centerx, enemy.rect.centery, powerup_type))
                    if missile in missiles:
                        try:
                            missiles.remove(missile)
                        except ValueError:
                            pass
                    break

        # Particle cleanup
        for particle in particles[:]:
            if not particle.update():
                try:
                    particles.remove(particle)
                except ValueError:
                    pass
        for sw in shockwaves[:]:
            if not sw.update():
                try:
                    shockwaves.remove(sw)
                except ValueError:
                    pass

        # Orbital update
        if orbital_charging:
            orbital_charge_time -= 1 / 30
            if orbital_charge_time <= 0:
                orbital_charging = False
                orbital_beam_active = True
                orbital_beam_time = orbital_beam_duration
                player_invincible = True
                player_invincible_time = max(player_invincible_time, orbital_beam_duration)
                for _ in range(8):
                    enemy_type = random.choices([EnemyType.DRONE, EnemyType.FIGHTER, EnemyType.CAPITAL], weights=[50, 35, 15])[0]
                    x = random.randint(0, WIDTH - 40)
                    enemies.append(Enemy(x, -40, enemy_type))

        if orbital_beam_active:
            orbital_beam_time -= 1 / 30
            cone_width_bottom = 40
            cone_width_top = WIDTH
            enemies_hit = []
            for enemy in enemies[:]:
                enemy_y = enemy.rect.centery
                if 0 <= enemy_y <= player.top:
                    progress = 1 - (enemy_y / player.top)
                    width_at_y = cone_width_bottom + (cone_width_top - cone_width_bottom) * progress
                    cone_x_left = player.centerx - width_at_y / 2
                    cone_x_right = player.centerx + width_at_y / 2
                    if cone_x_left <= enemy.rect.centerx <= cone_x_right:
                        enemies_hit.append(enemy)
                        for _ in range(15):
                            particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, random.uniform(-5, 5), random.uniform(-5, 5), color=(255, 255, 255)))
                        score += 1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3)
            for enemy in enemies_hit:
                try:
                    enemies.remove(enemy)
                except ValueError:
                    pass
            if orbital_beam_time <= 0:
                orbital_beam_active = False
                try:
                    if globals().get('orbital_sound', None):
                        globals()['orbital_sound'].stop()
                except Exception:
                    pass

        # --- Cutter update (orbiting blades + launch & explosion)
        if cutter_active:
            # spin phase
            if cutter_active_time > 0:
                cutter_active_time -= 1 / 30
                for blade in cutter_blades[:]:
                    if blade.state == 'orbit':
                        blade.update_orbit(spin_speed=0.16)
                        # instant destroy enemies that touch the blade while orbiting
                        for enemy in enemies[:]:
                            if blade.rect.colliderect(enemy.rect):
                                try:
                                    enemies.remove(enemy)
                                except ValueError:
                                    pass
                                for _ in range(12):
                                    particles.append(Particle(enemy.rect.centerx, enemy.rect.centery, random.uniform(-4,4), random.uniform(-4,4)))
                                score += 1 if enemy.type == EnemyType.DRONE else (2 if enemy.type == EnemyType.FIGHTER else 3)
                # if timer just reached 0, launch blades
                if cutter_active_time <= 0:
                    for blade in cutter_blades:
                        blade.launch()
                    play_sound(overdrive_sound if overdrive_active else powerup_sound)
            else:
                # launched phase
                for blade in cutter_blades[:]:
                    if blade.state == 'launched':
                        blade.update_launched()
                        # out of bounds removal
                        if blade.x < -50 or blade.x > WIDTH + 50 or blade.y < -50 or blade.y > HEIGHT + 50:
                            try:
                                cutter_blades.remove(blade)
                            except ValueError:
                                pass
                            continue
                        # check collision with enemies -> big explosion
                        collision_occurred = False
                        for enemy in enemies[:]:
                            if blade.rect.colliderect(enemy.rect):
                                collision_occurred = True
                                ex = int(blade.x)
                                ey = int(blade.y)
                                # explosion visuals
                                for _ in range(30):
                                    particles.append(Particle(ex + random.uniform(-8,8), ey + random.uniform(-8,8), random.uniform(-5,5), random.uniform(-5,5), lifetime=30, color=(255,180,60)))
                                shockwaves.append(Shockwave(ex, ey))
                                # remove/damage enemies within radius
                                for e in enemies[:]:
                                    dx = e.rect.centerx - ex
                                    dy = e.rect.centery - ey
                                    if dx*dx + dy*dy <= blade_explosion_radius * blade_explosion_radius:
                                        try:
                                            enemies.remove(e)
                                        except ValueError:
                                            pass
                                        score += 1 if e.type == EnemyType.DRONE else (2 if e.type == EnemyType.FIGHTER else 3)
                                # remove blade after explosion
                                try:
                                    cutter_blades.remove(blade)
                                except ValueError:
                                    pass
                                break
                        # if no immediate collision, blade continues until out of bounds
                # if all blades gone -> deactivate cutter
                if not cutter_blades:
                    cutter_active = False
                    cutter_active_time = 0.0

        # --- Artillery pending impact handling (after target picked)
        if artillery_pending:
            artillery_drop_timer -= 1 / 30
            if artillery_drop_timer <= 0:
                # Impact now
                ex, ey = artillery_target_pos
                # big explosion visuals
                for _ in range(80):
                    particles.append(Particle(ex + random.uniform(-24,24), ey + random.uniform(-24,24), random.uniform(-8,8), random.uniform(-8,8), lifetime=40, color=(255,180,60)))
                shockwaves.append(Shockwave(ex, ey))
                screen_shake = max(screen_shake, 12)
                play_sound(artillery_sound or hit_sound)
                # damage/remove enemies within radius
                for e in enemies[:]:
                    dx = e.rect.centerx - ex
                    dy = e.rect.centery - ey
                    if dx*dx + dy*dy <= artillery_radius * artillery_radius:
                        try:
                            enemies.remove(e)
                        except ValueError:
                            pass
                        score += 1 if e.type == EnemyType.DRONE else (2 if e.type == EnemyType.FIGHTER else 3)
                # damage player if within radius (can kill player)
                pdx = player.centerx - ex
                pdy = player.centery - ey
                if pdx*pdx + pdy*pdy <= artillery_radius * artillery_radius:
                    # heavy hit: remove a life and create visual
                    lives -= 1
                    for _ in range(20):
                        particles.append(Particle(player.centerx + random.uniform(-20,20), player.centery + random.uniform(-20,20), random.uniform(-5,5), random.uniform(-5,5), lifetime=30, color=(255,80,20)))
                    shockwaves.append(Shockwave(player.centerx, player.centery))
                    play_sound(hit_sound)
                    if lives <= 0:
                        game_state = GAME_OVER
                        if score > high_score:
                            high_score = score
                            save_high_score(high_score)
                # finalize
                artillery_pending = False
                artillery_drop_timer = 0.0

        draw_window()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
