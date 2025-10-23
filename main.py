# FlappyAkh – Flappy Bird mit Charakterwahl (Nizi19 & Yuyu19)
# Steuerung: [←]/[→] zum Auswählen, [ENTER] oder Klick zum Bestätigen
# Im Spiel: [SPACE]/Maus = Flap, [R] = Neustart, [ESC] = Beenden

import os
import sys
import random
import pygame
import math

# --- Grundeinstellungen ---
WIDTH, HEIGHT = 432, 768
FPS = 60
TITLE = "FlappyAkh"

# Farben
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Charakter-Definition (Dateien müssen im selben Ordner liegen wie dieses Skript)
CHARACTERS = [
    {
        "name": "Nizi19",
        "skin": "Nizi19_Skin.jpg",     # Auswahlbild
        "avatar": "Nizi19_Avatar.jpg", # Spielgesicht
    },
    {
        "name": "Yuyu19",
        "skin": "Yuyu19_Skin.jpg",
        "avatar": "Yuyu19_Avatar.jpg",
    },
]

# --- Hilfsfunktionen ---
def load_image_local(filename: str) -> pygame.Surface:
    path = os.path.join(os.path.dirname(__file__), filename)
    surf = pygame.image.load(path).convert_alpha()
    return surf

def make_face_circle_from_file(filename: str, size: int = 72) -> pygame.Surface:
    """Lädt ein Bild, skaliert es auf size x size und cropt es kreisförmig mit dünnem Rand."""
    img = load_image_local(filename)
    img = pygame.transform.smoothscale(img, (size, size))
    circle_mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(circle_mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)

    face_circle = pygame.Surface((size, size), pygame.SRCALPHA)
    face_circle.blit(img, (0, 0))
    face_circle.blit(circle_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.circle(face_circle, (0, 0, 0, 220), (size // 2, size // 2), size // 2, 3)
    return face_circle

# --- Collectible-Hilfsfunktion ---
def load_collectible_surface(size: int = 64) -> pygame.Surface:
    """Lädt Makatussin.png und skaliert es quadratisch."""
    img = load_image_local("Makatussin.png")
    img = pygame.transform.smoothscale(img, (size, size))
    return img

class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y, face_surface: pygame.Surface):
        super().__init__()
        # Basisbild aus der Charakterwahl
        self.base_image = face_surface
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = 0.0
        self.rotation = 0.0
        self.alive = True

        # Flügel-Animation (kontinuierlich + Flap-Boost)
        self.wing_flap_time = 0.0            # Sekunden, wie lange die Flügel „oben“ bleiben
        self.wing_color = (60, 200, 60)
        self.wing_phase = 0.0                # 0..1 Phase
        self.wing_speed = 6.0                # Schläge pro Sekunde
        self.wing_base_amp = 10              # Grund-Amplitude (Grad)
        self.wing_boost_dur = 0.15           # Dauer des Flap-Boosts

    def flap(self):
        self.vel = -8.5
        self.wing_flap_time = self.wing_boost_dur

    def draw_wings(self, surface):
        """Größere grüne Flügel mit weißen Federn + sanftem Dauerwippen"""
        cx, cy = self.rect.center

        # Flügel-Geometrie (größer + weiter außen)
        wing_w = 30
        outer_offset = 42

        # Sanftes Dauer-Wippen via Sinus + zusätzlicher Flap-Boost
        base = self.wing_base_amp * math.sin(self.wing_phase * math.tau)  # 2π
        boost = 16.0 * (self.wing_flap_time / self.wing_boost_dur) if self.wing_flap_time > 0 else 0.0
        angle = int(base - boost)  # bei Boost stärker nach oben

        # --- Hauptflügel (grün) ---
        left_base = [
            (cx - outer_offset, cy - 6),
            (cx - outer_offset - wing_w, cy - 6 + angle),
            (cx - outer_offset, cy + 6),
        ]
        right_base = [
            (cx + outer_offset, cy - 6),
            (cx + outer_offset + wing_w, cy - 6 + angle),
            (cx + outer_offset, cy + 6),
        ]
        pygame.draw.polygon(surface, self.wing_color, left_base)
        pygame.draw.polygon(surface, self.wing_color, right_base)
        pygame.draw.lines(surface, (30, 120, 30), True, left_base, 1)
        pygame.draw.lines(surface, (30, 120, 30), True, right_base, 1)

        # --- Untere Federn (weiß) ---
        feather_drop = 6
        feather_w = wing_w + 8
        left_feather = [
            (cx - outer_offset, cy + 2 + feather_drop),
            (cx - outer_offset - feather_w, cy + 2 + feather_drop + angle + 6),
            (cx - outer_offset, cy + 10 + feather_drop),
        ]
        right_feather = [
            (cx + outer_offset, cy + 2 + feather_drop),
            (cx + outer_offset + feather_w, cy + 2 + feather_drop + angle + 6),
            (cx + outer_offset, cy + 10 + feather_drop),
        ]
        pygame.draw.polygon(surface, (255, 255, 255), left_feather)
        pygame.draw.polygon(surface, (255, 255, 255), right_feather)
        pygame.draw.lines(surface, (200, 200, 200), True, left_feather, 1)
        pygame.draw.lines(surface, (200, 200, 200), True, right_feather, 1)

    def update(self, dt):
        # Physik
        self.vel += 20.0 * dt   # Gravitation
        self.rect.y += int(self.vel)

        # Flügelphase fortschreiben (0..1) für sanftes Dauerwippen
        self.wing_phase = (self.wing_phase + dt * self.wing_speed) % 1.0

        # Rotation abhängig von Geschwindigkeit
        self.rotation = max(-25, min(60, self.vel * 3.5))
        # Bild rotieren und Mittelpunkt behalten
        center_before = self.rect.center
        self.image = pygame.transform.rotozoom(self.base_image, -self.rotation, 1.0)
        self.rect = self.image.get_rect(center=center_before)

        # Kopfbegrenzung
        if self.rect.top < 0:
            self.rect.top = 0
            self.vel = 0

        # Flügel-Boost abbauen
        if self.wing_flap_time > 0:
            self.wing_flap_time -= dt
            if self.wing_flap_time < 0:
                self.wing_flap_time = 0

    def render(self, screen):
        # Vogel + Flügel zeichnen
        screen.blit(self.image, self.rect)
        self.draw_wings(screen)



class Pipe(pygame.sprite.Sprite):
    SPEED = 180  # px/s

    def __init__(self, x, height, flipped=False):
        super().__init__()
        self.width = 60
        self.color = (30, 200, 90) if not flipped else (30, 160, 70)
        surface_height = height
        surf = pygame.Surface((self.width, surface_height), pygame.SRCALPHA)
        surf.fill(self.color)
        pygame.draw.rect(surf, (10, 120, 50), (0, 0, self.width, surface_height), 6)
        self.image = surf
        self.rect = self.image.get_rect(midtop=(x, 0))
        if flipped:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect = self.image.get_rect(midbottom=(x, HEIGHT - 120))  # 120 = Bodenhöhe

        self.flipped = flipped

    def update(self, dt):
        self.rect.x -= int(self.SPEED * dt)
        if self.rect.right < -5:
            self.kill()


# --- Collectible-Klasse ---
class Collectible(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_collectible_surface(64)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, dt):
        # gleiche Geschwindigkeit wie die Pipes
        self.rect.x -= int(Pipe.SPEED * dt)
        if self.rect.right < -5:
            self.kill()

# --- ScorePopup-Klasse ---
class ScorePopup(pygame.sprite.Sprite):
    def __init__(self, x, y, text="+5"):
        super().__init__()
        self.text = text
        self.t = 0.0
        self.duration = 0.7  # Sekunden
        self.vy = -40        # Pixel/Sekunde nach oben
        # Eigenen Font anlegen (unabhängig vom globalen)
        self.font = pygame.font.SysFont("arial", 28, bold=True)
        self.image = self.font.render(self.text, True, (255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, dt):
        self.t += dt
        # Nach oben bewegen
        self.rect.y += int(self.vy * dt)
        # Alpha langsam ausblenden
        alpha = max(0, min(255, int(255 * (1.0 - self.t / self.duration))))
        # Neu rendern mit Alpha (Surface kopieren, dann Alpha setzen)
        surf = self.font.render(self.text, True, (255, 255, 255))
        surf.set_alpha(alpha)
        self.image = surf
        if self.t >= self.duration:
            self.kill()


class Ground(pygame.sprite.Sprite):
    SPEED = 180

    def __init__(self):
        super().__init__()
        self.height = 120
        self.image = pygame.Surface((WIDTH * 2, self.height))
        self.image.fill((230, 220, 180))
        for x in range(0, self.image.get_width(), 24):
            pygame.draw.rect(self.image, (205, 195, 150), (x, 0, 12, self.height))
        self.rect = self.image.get_rect(bottomleft=(0, HEIGHT))

    def update(self, dt):
        self.rect.x -= int(self.SPEED * dt)
        if self.rect.right <= WIDTH:
            self.rect.left = 0


def draw_background(screen):
    # einfacher Verlaufshimmel
    top = pygame.Color(45, 160, 230)
    bottom = pygame.Color(180, 230, 255)
    for y in range(HEIGHT - 120):  # bis Boden
        ratio = y / (HEIGHT - 120)
        color = (
            int(top.r + (bottom.r - top.r) * ratio),
            int(top.g + (bottom.g - top.g) * ratio),
            int(top.b + (bottom.b - top.b) * ratio),
        )
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))


def spawn_pipe_pair(group_all, group_pipes, x, gap_min, gap_max):
    gap = random.randint(gap_min, gap_max)  # dynamisch je nach Schwierigkeit
    top_min, top_max = 80, HEIGHT - 120 - gap - 80
    top_h = random.randint(top_min, top_max)
    bottom_h = HEIGHT - 120 - gap - top_h
    gap_center_y = top_h + gap // 2
    top_pipe = Pipe(x, top_h, flipped=False)
    bottom_pipe = Pipe(x, bottom_h, flipped=True)
    group_all.add(top_pipe, bottom_pipe)
    group_pipes.add(top_pipe, bottom_pipe)
    return (top_pipe, bottom_pipe, gap_center_y)


def character_select(screen, clock, font_big, font):
    """Zeigt die Auswahl für Nizi19/Yuyu19. Gibt Index (0/1) zurück."""
    # Skins laden & verkleinern
    skins = []
    for c in CHARACTERS:
        s = load_image_local(c["skin"])
        s = pygame.transform.smoothscale(s, (140, 140))
        skins.append(s)

    selected = 0
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit(0)
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % len(CHARACTERS)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % len(CHARACTERS)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return selected
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Klick-Hitboxen prüfen
                boxes = [
                    pygame.Rect(WIDTH//2 - 160 - 70, HEIGHT//2 - 80, 140, 140),
                    pygame.Rect(WIDTH//2 + 160 - 70, HEIGHT//2 - 80, 140, 140),
                ]
                for i, r in enumerate(boxes[:len(CHARACTERS)]):
                    if r.collidepoint(mx, my):
                        return i

        # Zeichnen
        draw_background(screen)

        title = font_big.render("FlappyAkh", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH//2, 120)))

        hint = font.render("Wähle deinen Charakter (←/→, ENTER oder Klick)", True, BLACK)
        screen.blit(hint, hint.get_rect(center=(WIDTH//2, 170)))

        # Positionen links/rechts
        centers = [(WIDTH//2 - 160, HEIGHT//2), (WIDTH//2 + 160, HEIGHT//2)]

        for i, c in enumerate(CHARACTERS):
            skin = skins[i]
            rect = skin.get_rect(center=centers[i])
            # Rahmen (Auswahl)
            border_col = (255, 220, 0) if i == selected else (0, 0, 0)
            pygame.draw.rect(screen, (255, 255, 255), rect.inflate(12, 12), border_radius=16)
            pygame.draw.rect(screen, border_col, rect.inflate(12, 12), width=4, border_radius=16)
            screen.blit(skin, rect)

            name_surf = font.render(c["name"], True, BLACK)
            screen.blit(name_surf, name_surf.get_rect(midtop=(rect.centerx, rect.bottom + 8)))

        pygame.display.flip()


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    clock = pygame.time.Clock()
    font_big = pygame.font.SysFont("arial", 48, bold=True)
    font = pygame.font.SysFont("arial", 24, bold=True)

    # --- Charakter-Auswahl ---
    # Prüfe, ob alle Bilder existieren
    missing = []
    for c in CHARACTERS:
        for k in ("skin", "avatar"):
            p = os.path.join(os.path.dirname(__file__), c[k])
            if not os.path.exists(p):
                missing.append(p)
    if missing:
        print("Fehlende Bilddateien:\n- " + "\n- ".join(missing))
        print("Bitte die Dateien in den gleichen Ordner wie das Skript legen.")
        pygame.quit(); sys.exit(1)

    selected_idx = character_select(screen, clock, font_big, font)
    chosen = CHARACTERS[selected_idx]
    face_surface = make_face_circle_from_file(chosen["avatar"], size=72)

    # Gruppen
    all_sprites = pygame.sprite.Group()
    pipe_group = pygame.sprite.Group()
    collect_group = pygame.sprite.Group()
    popup_group = pygame.sprite.Group()
    ground = Ground()
    all_sprites.add(ground)

    bird = Bird(100, HEIGHT // 2, face_surface)
    all_sprites.add(bird)

    # Startzustand
    running = True
    playing = False
    score = 0
    last_pipe_x = WIDTH + 200
    scored_pipes = set()
    pipe_spawn_count = 0

    # Anfangsschwierigkeit (leicht)
    gap_min, gap_max = 320, 400
    spawn_threshold = 320  # horizontaler Abstand, wann neue Pipes spawnen

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    # neu starten, wenn nicht playing ODER wenn tot
                    if not playing or not bird.alive:
                        playing = True
                        for p in pipe_group.sprites():
                            p.kill()
                        for c in collect_group.sprites():
                            c.kill()
                        for s in popup_group.sprites():
                            s.kill()
                        score = 0
                        scored_pipes.clear()
                        last_pipe_x = WIDTH + 120
                        bird.rect.center = (100, HEIGHT // 2)
                        bird.vel = 0
                        bird.alive = True
                        # Schwierigkeit zurücksetzen
                        gap_min, gap_max = 320, 400
                        Pipe.SPEED = 180
                        # spawn_threshold = 320
                    bird.flap()
                if event.key == pygame.K_RETURN and not bird.alive:
                    # zurück zur Charakterauswahl
                    selected_idx = character_select(screen, clock, font_big, font)
                    chosen = CHARACTERS[selected_idx]
                    face_surface = make_face_circle_from_file(chosen["avatar"], size=72)
                    bird.base_image = face_surface
                    bird.image = bird.base_image.copy()
                    # Zurück zum Startscreen (noch nicht spielend)
                    playing = False
                    for p in pipe_group.sprites():
                        p.kill()
                    for c in collect_group.sprites():
                        c.kill()
                    for s in popup_group.sprites():
                        s.kill()
                    score = 0
                    scored_pipes.clear()
                    last_pipe_x = WIDTH + 120
                    bird.rect.center = (100, HEIGHT // 2)
                    bird.vel = 0
                    bird.alive = True
                    # Schwierigkeit zurücksetzen
                    gap_min, gap_max = 320, 400
                    Pipe.SPEED = 180
                    # spawn_threshold = 320
                if event.key == pygame.K_r and not bird.alive:
                    playing = False  # zurück zum Startscreen (mit gewähltem Charakter behalten wir)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not playing:
                    playing = True
                    for p in pipe_group.sprites():
                        p.kill()
                    for c in collect_group.sprites():
                        c.kill()
                    for s in popup_group.sprites():
                        s.kill()
                    score = 0
                    scored_pipes.clear()
                    last_pipe_x = WIDTH + 120
                    bird.rect.center = (100, HEIGHT // 2)
                    bird.vel = 0
                    bird.alive = True
                    # Schwierigkeit zurücksetzen
                    gap_min, gap_max = 320, 400
                    Pipe.SPEED = 180
                    # spawn_threshold = 320
                bird.flap()

        # Logik
        if playing and bird.alive:
            # Pipes spawnen (größerer Abstand = leichter)
            if not pipe_group or (last_pipe_x - max([p.rect.x for p in pipe_group]) >= spawn_threshold):
                last_pipe_x = WIDTH + 120
                top_p, bot_p, gap_center_y = spawn_pipe_pair(all_sprites, pipe_group, last_pipe_x, gap_min, gap_max)
                pipe_spawn_count += 1

                # Alle 10 Säulen: ein bisschen schwieriger
                if pipe_spawn_count % 10 == 0:
                    # Lücke leicht verkleinern, aber nicht unter 240 px
                    gap_min = max(240, gap_min - 20)
                    gap_max = max(gap_min + 40, gap_max - 20)
                    # Pipes minimal beschleunigen (Deckel bei 240)
                    Pipe.SPEED = min(240, Pipe.SPEED + 10)
                    # Optional: horizontale Spawndistanz leicht verringern
                    # spawn_threshold = max(260, spawn_threshold - 10)

                # Collectible alle 3 Säulen
                if pipe_spawn_count % 3 == 0:
                    # Collectible mittig in die Lücke setzen (leicht nach rechts versetzt)
                    col = Collectible(last_pipe_x + 30, gap_center_y)
                    all_sprites.add(col)
                    collect_group.add(col)

            all_sprites.update(dt)

            # Kollisionen
            for p in pipe_group:
                if bird.rect.colliderect(p.rect):
                    bird.alive = False

            # Kollision mit Collectibles (Makatussin)
            for col in list(collect_group):
                if bird.rect.colliderect(col.rect):
                    score += 5
                    # Popup über dem Item anzeigen
                    popup = ScorePopup(col.rect.centerx, col.rect.top - 10, "+5")
                    all_sprites.add(popup)
                    popup_group.add(popup)
                    col.kill()

            # Boden
            if bird.rect.bottom >= HEIGHT - 120:
                bird.rect.bottom = HEIGHT - 120
                bird.alive = False

            # Score (wenn obere Pipe passiert)
            for p in pipe_group:
                if not getattr(p, "flipped", False):
                    if p.rect.right < bird.rect.left and p not in scored_pipes:
                        score += 1
                        scored_pipes.add(p)

        # Zeichnen
        draw_background(screen)
        for sprite in all_sprites:
            if isinstance(sprite, Bird):
                sprite.render(screen)
            else:
                screen.blit(sprite.image, sprite.rect)

        # UI / Texte
        if not playing:
            title_surf = font_big.render(f"FlappyAkh – {chosen['name']}", True, WHITE)
            hint = font.render("Drück SPACE oder klicke, um zu starten", True, BLACK)
            screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
            screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
        else:
            score_surf = font_big.render(str(score), True, WHITE)
            screen.blit(score_surf, score_surf.get_rect(midtop=(WIDTH//2, 20)))

        if playing and not bird.alive:
            over = font_big.render("Game Over", True, BLACK)
            hint_restart = font.render("Leertaste: Neustart", True, BLACK)
            hint_char = font.render("Enter: Charakterauswahl", True, BLACK)

            # Safe-Area: etwas höher platzieren, damit auf allen Geräten nichts abgeschnitten wird
            safe_y = HEIGHT // 2 - 60
            screen.blit(over, over.get_rect(center=(WIDTH//2, safe_y)))
            screen.blit(hint_restart, hint_restart.get_rect(center=(WIDTH//2, safe_y + 40)))
            screen.blit(hint_char, hint_char.get_rect(center=(WIDTH//2, safe_y + 70)))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()