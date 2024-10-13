import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
PLAYER_SPEED = 5
BULLET_SPEED = 10
ENEMY_SPEED = 2
POWER_UP_SPEED = 3
ENEMY_SPAWN_RATE = 30  # Lower is faster
LEVEL_UP_RATE = 150   # Frames to increase difficulty

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Initialize screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Alpha Passing Time")

# Load the icon
icon_image = pygame.image.load("background/icon.png").convert_alpha()
pygame.display.set_icon(icon_image)

clock = pygame.time.Clock()

# Load assets
player_image = pygame.image.load("background/player.png").convert_alpha()
enemy_image = pygame.image.load("background/enemy.png").convert_alpha()
bullet_image = pygame.image.load("background/bullet.png").convert_alpha()
explosion_sound = pygame.mixer.Sound("background/explosion.wav")
shoot_sound = pygame.mixer.Sound("background/shoot.wav")
pygame.mixer.music.load("background/background.mp3")
pygame.mixer.music.play(-1)  # Loop the background music

# Game entities
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = player_image
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        self.health = 100
        self.score = 0
        self.weapon_level = 1

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] and self.rect.right < SCREEN_WIDTH:
            self.rect.x += PLAYER_SPEED

    def upgrade_weapon(self):
        self.weapon_level += 1

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = bullet_image
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.rect.y -= BULLET_SPEED
        if self.rect.bottom < 0:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, speed):
        super().__init__()
        self.image = enemy_image
        self.rect = self.image.get_rect(center=(random.randint(0, SCREEN_WIDTH), 0))
        self.health = 50
        self.speed = speed

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

class PowerUp(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(center=(random.randint(0, SCREEN_WIDTH), 0))

    def update(self):
        self.rect.y += POWER_UP_SPEED
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

# Initialize sprite groups
player = Player()
player_group = pygame.sprite.Group(player)
bullet_group = pygame.sprite.Group()
enemy_group = pygame.sprite.Group()
power_up_group = pygame.sprite.Group()

# Game loop
score = 0
enemy_spawn_counter = 0
level_up_counter = 0
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                bullet_count = 1 + player.weapon_level  # Number of bullets increases with weapon level
                for i in range(bullet_count):
                    bullet_x = player.rect.centerx + (i - bullet_count // 2) * 15  # Spread bullets
                    bullet = Bullet(bullet_x, player.rect.top)
                    bullet_group.add(bullet)
                shoot_sound.play()

    # Update game entities
    player_group.update()
    bullet_group.update()
    enemy_group.update()
    power_up_group.update()

    # Spawn enemies
    enemy_spawn_counter += 1
    if enemy_spawn_counter >= ENEMY_SPAWN_RATE:
        speed = ENEMY_SPEED + (player.score // 100)  # Increase enemy speed based on score
        enemy = Enemy(speed)
        enemy_group.add(enemy)
        enemy_spawn_counter = 0

    # Spawn power-ups randomly
    if random.randint(1, 100) <= 5:  # 5% chance to spawn a power-up
        power_up = PowerUp()
        power_up_group.add(power_up)

    # Check collisions
    for bullet in bullet_group:
        hit_enemies = pygame.sprite.spritecollide(bullet, enemy_group, False)
        for enemy in hit_enemies:
            enemy.health -= 50
            bullet.kill()
            if enemy.health <= 0:
                enemy.kill()
                score += 10
                player.score += 10
                explosion_sound.play()
                # Spawn power-up when enemy is destroyed
                if random.random() < 0.3:  # 30% chance to drop a power-up
                    power_up = PowerUp()
                    power_up_group.add(power_up)

    # Check player collisions with power-ups
    if pygame.sprite.spritecollideany(player, power_up_group):
        power_up = pygame.sprite.spritecollideany(player, power_up_group)
        power_up.kill()
        player.upgrade_weapon()  # Upgrade player's weapon level

    # Check player collisions with enemies
    if pygame.sprite.spritecollideany(player, enemy_group):
        player.health -= 10
        if player.health <= 0:
            running = False

    # Draw everything
    screen.fill(BLACK)
    player_group.draw(screen)
    bullet_group.draw(screen)
    enemy_group.draw(screen)
    power_up_group.draw(screen)

    # Display health and score
    health_text = pygame.font.Font(None, 36).render(f"Health: {player.health}", True, WHITE)
    score_text = pygame.font.Font(None, 36).render(f"Score: {player.score}", True, WHITE)
    level_text = pygame.font.Font(None, 36).render(f"Weapon Level: {player.weapon_level}", True, WHITE)
    screen.blit(health_text, (10, 10))
    screen.blit(score_text, (10, 40))
    screen.blit(level_text, (10, 70))

    pygame.display.flip()
    clock.tick(FPS)

    # Level up system
    level_up_counter += 1
    if level_up_counter >= LEVEL_UP_RATE:
        ENEMY_SPAWN_RATE = max(10, ENEMY_SPAWN_RATE - 1)  # Increase difficulty by decreasing spawn rate
        level_up_counter = 0

# Game Over screen
while True:
    screen.fill(BLACK)
    game_over_text = pygame.font.Font(None, 74).render("GAME OVER", True, RED)
    score_text = pygame.font.Font(None, 36).render(f"Final Score: {player.score}", True, WHITE)
    screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
    screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2 + 10))
    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
