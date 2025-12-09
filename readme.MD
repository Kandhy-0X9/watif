I'll add pseudocode explanations for each part of your file. Due to the size, this document will start now and you can ask me to continue, modify, or expand any section.

# FULL PSEUDOCODE FOR **copilot.py**

Below is a complete pseudocode explanation of the entire file.

---

## **Imports and Initialization**

```python
import pygame
import random
import sys
import json
import os
from enum import Enum
```

**Pseudocode:** Load all needed modules for graphics, randomness, system functions, saving data, and defining enums.

```python
pygame.init()
pygame.mixer.init()
```

**Pseudocode:** Initialize Pygame and its sound system.

---

## **Screen Setup**

* Set width/height values
* Create display window
* Title the window "Starship Defense"
* Initialize screen shake variable

---

## **Color Definitions**

* Define RGB values for various sci‑fi colors used in the game.

---

## **EnemyType Enum**

* Create categories DRONE, FIGHTER, CAPITAL so enemies can have different stats.

---

## **PowerUpType Enum**

* Create categories SHIELD, RAPID_FIRE, INVINCIBILITY.

---

## **Particle System**

Class stores small effects for explosions.

* Constructor sets position, velocity, lifespan, and color.
* update(): moves particle and ages it.
* draw(): calculates fade and draws shrinking glowing circle.
* Particles list stores active particles.

---

## **Sound System**

* load_sound(): tries to load audio file, returns None if missing.
* play_sound(): plays sound only if loaded.
* Try loading shoot, hit, powerup, background music.

---

## **High Score System**

* SCORE_FILE = "highscore.json"
* load_high_score(): read the file if exists, else return 0.
* save_high_score(): write the new high score.

---

## **Player Setup**

* Create player rectangle.
* Movement speed.
* Shield, invincibility, rapid fire booleans + timers.

---

## **Enemy Class**

* Constructor: set rectangle, type, health based on type.
* draw(): draw unique shapes/colors depending on enemy type.

---

## **Enemy Variables**

* enemies list
* enemy_speed = 4
* spawn_rate = 25

---

## **PowerUp Class**

* Constructor: set rectangle + type.
* draw(): draw icon depending on power‑up type.

---

## **PowerUp Variables**

* powerups list

---

## **Missile Setup**

* missiles list
* missile_speed = 8

---

## **Score + UI Setup**

* score = 0
* Load high score
* lives = 3
* Create fonts
* clock = time manager

---

## **Game States**

* PLAYING, GAME_OVER, PAUSED = integer constants
* game_state starts at PLAYING

---

## **draw_window()**

* Apply screenshake offset
* Clear screen (black)
* Draw scrolling stars using score
* Draw all particles
* Draw player ship (flashes if invincible)
* Draw shield circle if shield is active
* Draw enemies
* Draw powerups
* Draw missiles
* Draw UI (score, lives, high score)
* Draw timers for active powerups
* Update display
* Reduce screen shake value

---

## **draw_game_over()**

* Clear screen
* Draw "MISSION FAILED" text, score, high score, restart instructions

---

## **draw_pause()**

* Clear screen
* Show pause message + resume instruction

---

## **reset_game()**

* Reset score, lives, enemy speed, spawn rate
* Clear enemies, missiles, powerups, particles
* Reset player position + powerup states
* Restart music

---

## **main()** — The Game Loop

* Start background music
* Loop while running:

### **If PAUSED:**

* Draw pause screen
* Wait for unpause

### **If GAME_OVER:**

* Draw game over
* Wait for restart or quit

### **Event Handling:**

* Quit closes game
* SPACE fires missile
* P pauses

### **Power‑Up Timer Updates**

* Decrease shield/rapid fire/invincible timers every frame
* Disable when timer hits 0

### **Player Movement**

* Move left/right with arrow keys

### **Difficulty Scaling**

* Every 10 score increase enemy speed and spawn faster

### **Enemy Spawning**

* Randomly create enemies using weighted selection of types

### **Enemy Movement + Player Collision**

* Move enemy based on type speed
* If enemy hits player:

  * If invincible → ignore
  * Else if shielded → remove shield
  * Else → reduce lives, shake screen, trigger particles
  * If lives reach 0 → GAME_OVER

### **Rapid Fire Mode**

* Auto shoot every few frames

### **Power‑Up Collection**

* If player touches power‑up:

  * Activate its effect
  * Set timer

### **Missile Movement + Enemy Collision**

* Move missile upward
* If missile hits enemy:

  * Reduce enemy health
  * Spawn explosion particles
  * If enemy dies:

    * Add score
    * Random chance to drop a power‑up
  * Remove missile

### **Particle Updates**

* Update particles, remove old ones

### **Draw Frame**

* Call draw_window()

---

## **Program End**

* When main loop ends, quit pygame + exit.

---

**Done!**

If you want, I can also:

* Add comments directly into the Python code
* Add flowcharts for game logic
* Add pseudocode grouped by functions instead of by file order
