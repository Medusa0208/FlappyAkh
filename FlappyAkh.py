import pygame
import random
import os
import sys

pygame.init()

# Bildschirmgröße
WIDTH, HEIGHT = 400, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FlappyAkh")

# Farben
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)

FONT = pygame.font.SysFont("arial", 26)

# ---------------------------------------------------------
# Hilfsfunktion zum Laden von Bildern (websicher)
# ---------------------------------------------------------
def load_image_local(filename: str) -> pygame.Surface:
    """Lädt ein Bild aus mehreren sinnvollen Suchpfaden.
    Vermeidet starre __file__-Pfade (Web/pygbag), damit nichts schwarz bleibt.
    """
    candidates = [filename]
    try:
        candidates.append(os.path.join(os.getcwd(), filename))
    except Exception:
        pass
    try:
        base = os.path.dirname(__file__)
        candidates.append(os.path.join(base, filename))
    except Exception:
        pass

    last_err = None
    for path in candidates:
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception as e:
            last_err = e
            continue

    raise FileNotFoundError(
        f"Bilddatei nicht gefunden: {filename} | Versucht: {candidates} | letzter Fehler: {last_err}"
    )

# ---------------------------------------------------------
# Charakterdefinitionen
# ---------------------------------------------------------
CHARACTERS = [
    {"name": "Nizi19", "skin": "Nizi19_Skin.jpg", "avatar": "Nizi19_Avatar.jpg"},
    {"name": "Yuyu19", "skin": "Yuyu19_Skin.jpg", "avatar": "Yuyu19_Avatar.jpg"},
]

# ---------------------------------------------------------
# Spiellogik
# ---------------------------------------------------------
def main():
    # Überprüfen, ob alle Bilder vorhanden sind
    missing = []
    for c in CHARACTERS:
        for k in ("skin", "avatar"):
            try:
                _ = load_image_local(c[k])  # web-sicher: echtes Laden testen
            except Exception:
                missing.append(c[k])
    if missing:
        print("Fehlende Bilddateien:\n- " + "\n- ".join(missing))
        print("Bitte die Dateien in den gleichen Ordner wie das Skript legen.")
        pygame.quit()
        sys.exit(1)

    clock = pygame.time.Clock()
    gravity = 0.5
    flap_strength = -8
    pipe_gap = 180
    pipe_width = 60
    pipe_speed = 3
    score = 0
    difficulty_counter = 0

    # Charakterauswahl
    character_index = character_select()

    player_img = load_image_local(CHARACTERS[character_index]["avatar"])
    player_rect = player_img.get_rect(center=(80, HEIGHT // 2))
    player_velocity = 0

    # Makatussin-Objekt
    makatussin_img = load_image_local("Makatussin.png")
    makatussin_img = pygame.transform.scale(makatussin_img, (70, 100))
    makatussin_rect = makatussin_img.get_rect(center=(-100, -100))
    makatussin_visible = False

    # Säulen
    pipes = []
    for i in range(3):
        height_offset = random.randint(-100, 100)
        x = 400 + i * 200
        y = HEIGHT // 2 + height_offset
        pipes.append((x, y))

    running = True
    game_over = False

    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game_over:
                        main()  # Neustart
                        return
                    else:
                        player_velocity = flap_strength
                if event.key == pygame.K_RETURN and game_over:
                    main()  # Zur Charakterauswahl
                    return

        if not game_over:
            player_velocity += gravity
            player_rect.y += player_velocity

            # Bewegung der Säulen
            for i in range(len(pipes)):
                pipes[i] = (pipes[i][0] - pipe_speed, pipes[i][1])

            # Neue Säulen erzeugen
            if pipes[0][0] < -pipe_width:
                pipes.pop(0)
                new_y = HEIGHT // 2 + random.randint(-100, 100)
                pipes.append((pipes[-1][0] + 200, new_y))
                score += 1
                difficulty_counter += 1

                # Alle 10 Säulen schwieriger
                if difficulty_counter % 10 == 0:
                    pipe_gap = max(120, pipe_gap - 10)
                    pipe_speed += 0.3

                # Chance auf Makatussin
                if random.randint(1, 3) == 1:
                    makatussin_visible = True
                    makatussin_rect.center = (pipes[-1][0] + 50, pipes[-1][1])

            # Kollisionsprüfung
            for (x, y) in pipes:
                top_rect = pygame.Rect(x, 0, pipe_width, y - pipe_gap // 2)
                bottom_rect = pygame.Rect(x, y + pipe_gap // 2, pipe_width, HEIGHT - y)
                if player_rect.colliderect(top_rect) or player_rect.colliderect(bottom_rect):
                    game_over = True

            # Boden oder Decke
            if player_rect.top <= 0 or player_rect.bottom >= HEIGHT:
                game_over = True

            # Makatussin-Kollision
            if makatussin_visible and player_rect.colliderect(makatussin_rect):
                score += 5
                makatussin_visible = False

        # -----------------------------
        # Zeichnen
        # -----------------------------
        screen.fill((135, 206, 235))  # Himmelblau

        for (x, y) in pipes:
            pygame.draw.rect(screen, GREEN, (x, 0, pipe_width, y - pipe_gap // 2))
            pygame.draw.rect(screen, GREEN, (x, y + pipe_gap // 2, pipe_width, HEIGHT - y))

        if makatussin_visible:
            screen.blit(makatussin_img, makatussin_rect)

        screen.blit(player_img, player_rect)
        score_text = FONT.render(f"Punkte: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        if game_over:
            text1 = FONT.render("Game Over!", True, WHITE)
            text2 = FONT.render("Leertaste: Neustart", True, WHITE)
            text3 = FONT.render("Enter: Charakterauswahl", True, WHITE)
            screen.blit(text1, (WIDTH // 2 - text1.get_width() // 2, HEIGHT // 2 - 60))
            screen.blit(text2, (WIDTH // 2 - text2.get_width() // 2, HEIGHT // 2 - 20))
            screen.blit(text3, (WIDTH // 2 - text3.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()

    pygame.quit()


# ---------------------------------------------------------
# Charakterauswahlbildschirm
# ---------------------------------------------------------
def character_select():
    clock = pygame.time.Clock()
    selected = 0
    waiting = True

    while waiting:
        clock.tick(30)
        screen.fill(BLACK)
        title = FONT.render("Wähle deinen Charakter", True, WHITE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))

        for i, c in enumerate(CHARACTERS):
            skin = load_image_local(c["skin"])
            skin = pygame.transform.scale(skin, (100, 100))
            x = 100 + i * 200
            y = 200
            screen.blit(skin, (x, y))
            name = FONT.render(c["name"], True, WHITE)
            screen.blit(name, (x + 10, y + 110))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return 0
                elif event.key == pygame.K_2:
                    return 1

        hint = FONT.render("Drücke 1 oder 2", True, WHITE)
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 60))
        pygame.display.flip()


# ---------------------------------------------------------
# Start
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
