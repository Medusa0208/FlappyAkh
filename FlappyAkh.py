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
    {
        "name": "Lucio101",
        "skin": "Lucio101_Skin.jpg",
        "avatar": "Lucio101_Avatar.jpg",
    },
]

# --- Collectibles-Konfiguration ---
# weight = Spawn-Gewicht (höhere Zahl = häufiger), points = Punktewert, size = Anzeigegröße
COLLECTIBLES = [
    {"key": "maka", "file": "Makatussin.png", "points": 5,  "size": 64, "weight": 6, "color": (255, 255, 255)},
    {"key": "hash", "file": "Hash.jpg",       "points": 10, "size": 64, "weight": 3, "color": (255, 230, 80), "mask": "autokey"},
    {"key": "ott",  "file": "Ott.png",        "points": 20, "size": 96, "weight": 3, "color": (255, 120, 220)},
]

# Wie oft und wie wahrscheinlich ein Collectible spawnt
COLLECTIBLE_EVERY = 2        # alle N Säulenpaare
COLLECTIBLE_PROB  = 0.75     # und zusätzlich diese Wahrscheinlichkeit


def weighted_choice(items, weight_key="weight"):
    total = sum(i[weight_key] for i in items)
    r = random.uniform(0, total)
    acc = 0.0
    for i in items:
        acc += i[weight_key]
        if r <= acc:
            return i
    return items[-1]

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

# --- Collectible-Hilfsfunktion (mit Freistellung) ---
def load_collectible_surface_from_spec(spec: dict) -> pygame.Surface:
    """Lädt das Collectible-Bild, stellt es optional frei und skaliert auf spec['size'].
    Unterstützte spec["mask"]:
      - "autokey": Hintergrundfarbe vom Pixel (0,0) als transparent setzen (für JPG mit einfarbigem BG).
      - "circle": Rundmaskierung (kreisförmiger Zuschnitt, zentriert auf Bildmitte).
      - "circle_smart": Erst Hintergrund automatisch freistellen (wie autokey), dann den Inhalt erkennen
         und die Kreis-Zuschnitthilfe auf das **Inhaltszentrum** ausrichten (gegen Off-Center-Objekte).
    """
    file = spec["file"]
    size = spec.get("size", 64)

    # Laden (roh, ohne Alpha-Konvertierung, damit set_colorkey wirken kann)
    path = os.path.join(os.path.dirname(__file__), file)
    try:
        surf = pygame.image.load(path)
    except Exception:
        surf = load_image_local(file)

    mask_mode = spec.get("mask")

    if mask_mode == "autokey":
        if not surf.get_masks()[3]:
            surf = surf.convert()
        bg = surf.get_at((0, 0))
        surf.set_colorkey(bg)
        surf = surf.convert_alpha()

    elif mask_mode == "circle":
        # Normale Kreisfreistellung um die Bildmitte
        surf = surf.convert_alpha()
        w, h = surf.get_size()
        d = min(w, h)
        x0 = (w - d) // 2
        y0 = (h - d) // 2
        square = pygame.Surface((d, d), pygame.SRCALPHA)
        square.blit(surf, (0, 0), area=pygame.Rect(x0, y0, d, d))
        mask = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
        square.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf = square

    elif mask_mode == "circle_smart":
        # 1) Autokey anwenden, damit Hintergrund transparent wird
        if not surf.get_masks()[3]:
            surf = surf.convert()
        bg = surf.get_at((0, 0))
        surf.set_colorkey(bg)
        surf = surf.convert_alpha()
        # 2) Inhaltsmaske bestimmen und Bounding-Box holen
        try:
            m = pygame.mask.from_surface(surf)
            bbox = m.get_bounding_rect()
            if bbox.width > 0 and bbox.height > 0:
                # 3) Quadratisch um das Inhaltszentrum zuschneiden
                cx = bbox.centerx
                cy = bbox.centery
                d = max(bbox.width, bbox.height)
                # Sicherheitsrand (10%) hinzufügen
                pad = int(d * 0.1)
                d = min(max(d + pad, 1), min(surf.get_width(), surf.get_height()))
                x0 = max(0, cx - d // 2)
                y0 = max(0, cy - d // 2)
                # Korrektur, falls über Rand
                if x0 + d > surf.get_width():
                    x0 = surf.get_width() - d
                if y0 + d > surf.get_height():
                    y0 = surf.get_height() - d
                square = pygame.Surface((d, d), pygame.SRCALPHA)
                square.blit(surf, (0, 0), area=pygame.Rect(x0, y0, d, d))
                # 4) Kreis-Maske auf das quadratische Bild
                mask = pygame.Surface((d, d), pygame.SRCALPHA)
                pygame.draw.circle(mask, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
                square.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                surf = square
            else:
                # Fallback: keine erkennbare Box → normale circle-Mitte
                w, h = surf.get_size()
                d = min(w, h)
                x0 = (w - d) // 2
                y0 = (h - d) // 2
                square = pygame.Surface((d, d), pygame.SRCALPHA)
                square.blit(surf, (0, 0), area=pygame.Rect(x0, y0, d, d))
                mask = pygame.Surface((d, d), pygame.SRCALPHA)
                pygame.draw.circle(mask, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
                square.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                surf = square
        except Exception:
            # Fallback bei Problemen
            surf = surf.convert_alpha()

    else:
        # Kein spezieller Modus → nur Alpha sicherstellen
        surf = surf.convert_alpha()

    # Endgröße setzen
    surf = pygame.transform.smoothscale(surf, (size, size))
    return surf

class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y, face_surface: pygame.Surface):
        super().__init__()
        # Basisbild aus der Charakterwahl
        self.base_image = face_surface
        # Neue Flügelbilder laden
        self.left_wing_image = load_image_local("LinkerFluegel.png")
        self.right_wing_image = load_image_local("RechterFluegel.png")
        # Etwas kleiner skalieren für bessere Proportionen
        self.left_wing_image = pygame.transform.smoothscale(self.left_wing_image, (48, 48))
        self.right_wing_image = pygame.transform.smoothscale(self.right_wing_image, (48, 48))
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
        """Zeichnet die Flügelbilder (links/rechts) mit sanfter Animation, sodass das Gesicht sichtbar bleibt."""
        cx, cy = self.rect.center

        # Sanftes Dauerwippen + Flap-Boost
        base = self.wing_base_amp * math.sin(self.wing_phase * math.tau)
        boost = 18.0 * (self.wing_flap_time / self.wing_boost_dur) if self.wing_flap_time > 0 else 0.0
        angle = base - boost

        # Rotation auf separate Kopien anwenden
        left_rot = pygame.transform.rotozoom(self.left_wing_image, angle, 1.0)
        right_rot = pygame.transform.rotozoom(self.right_wing_image, -angle, 1.0)

        # Positionierung leicht hinter dem Kopf, damit der Avatar sichtbar bleibt
        offset_x = 54
        offset_y = -10
        left_rect = left_rot.get_rect(center=(cx - offset_x, cy + offset_y))
        right_rect = right_rot.get_rect(center=(cx + offset_x, cy + offset_y))

        # Flügel-Schatten für bessere Sichtbarkeit
        for img, rect in ((left_rot, left_rect), (right_rot, right_rect)):
            shadow = img.copy()
            shadow.fill((0, 0, 0, 70), None, pygame.BLEND_RGBA_MULT)
            surface.blit(shadow, rect.move(2, 2))

        # Flügel selbst zeichnen (links und rechts)
        surface.blit(left_rot, left_rect)
        surface.blit(right_rot, right_rect)

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
        # Flügel zuerst zeichnen (hinter dem Vogel)
        self.draw_wings(screen)
        screen.blit(self.image, self.rect)



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
    def __init__(self, spec: dict, x: int, y: int):
        super().__init__()
        self.spec = spec
        base = load_collectible_surface_from_spec(spec)
        # Sichtbarkeits-Halo: weicher weißer Schein hinter dem Item
        pad = 10
        w, h = base.get_size()
        halo = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
        cx, cy = halo.get_width() // 2, halo.get_height() // 2
        rad = int(max(w, h) / 2)
        for dr, alpha in [(8, 30), (5, 60), (2, 90)]:
            pygame.draw.circle(halo, (255, 255, 255, alpha), (cx, cy), rad + dr)
        halo.blit(base, (pad, pad))
        self.image = halo
        self.rect = self.image.get_rect(center=(x, y))
        self.points = spec["points"]
        self.pop_color = spec.get("color", (255, 255, 255))

    def update(self, dt):
        self.rect.x -= int(Pipe.SPEED * dt)
        if self.rect.right < -5:
            self.kill()

# --- ScorePopup-Klasse ---
class ScorePopup(pygame.sprite.Sprite):
    def __init__(self, x, y, text="+5", color=(255, 255, 255)):
        super().__init__()
        self.text = text
        self.color = color
        self.t = 0.0
        self.duration = 0.7  # Sekunden
        self.vy = -40        # Pixel/Sekunde nach oben
        # Eigenen Font anlegen (unabhängig vom globalen)
        self.font = pygame.font.SysFont("arial", 28, bold=True)
        self.image = self.font.render(self.text, True, self.color)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, dt):
        self.t += dt
        # Nach oben bewegen
        self.rect.y += int(self.vy * dt)
        # Alpha langsam ausblenden
        alpha = max(0, min(255, int(255 * (1.0 - self.t / self.duration))))
        # Neu rendern mit Alpha (Surface kopieren, dann Alpha setzen)
        surf = self.font.render(self.text, True, self.color)
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


def spawn_pipe_pair(group_all, group_pipes, x):
    gap = random.randint(320, 400)  # noch größerer Abstand = einfacher
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
                # Klick-Hitboxen dynamisch anhand der Anzahl der Charaktere
                spacing = 160
                n = len(CHARACTERS)
                startx = WIDTH//2 - int(spacing * (n - 1) / 2)
                centers = [(startx + i*spacing, HEIGHT//2) for i in range(n)]
                for i in range(n):
                    r = pygame.Rect(0, 0, 140, 140)
                    r.center = centers[i]
                    if r.collidepoint(mx, my):
                        return i

        # Zeichnen
        draw_background(screen)

        # --- Animated title & hints ---
        t = pygame.time.get_ticks() / 1000.0

        # Puls-Skalierung (sanft) für den Titel
        title_scale = 1.0 + 0.04 * math.sin(t * 2.0 * math.pi * 0.8)
        title = font_big.render("FlappyAkh", True, WHITE)
        title_anim = pygame.transform.rotozoom(title, 0, title_scale)
        screen.blit(title_anim, title_anim.get_rect(center=(WIDTH//2, 118)))

        # Hints: leichtes Atmen (Alpha) + kleines vertikales Wippen
        alpha = int(190 + 65 * (0.5 + 0.5 * math.sin(t * 2.0 * math.pi * 1.2)))  # 190..255
        bob1 = int(2 * math.sin(t * 2.0 * math.pi * 1.0))
        bob2 = int(2 * math.sin((t + 0.25) * 2.0 * math.pi * 1.0))

        hint1 = font.render("CHOOSE YOUR CHARACTER", True, BLACK)
        hint1.set_alpha(alpha)
        screen.blit(hint1, hint1.get_rect(center=(WIDTH//2, 170 + bob1)))

        hint2 = font.render("click to start", True, BLACK)
        hint2.set_alpha(alpha)
        screen.blit(hint2, hint2.get_rect(center=(WIDTH//2, 198 + bob2)))

        # Positionen dynamisch anhand der Anzahl der Charaktere
        spacing = 160
        n = len(CHARACTERS)
        startx = WIDTH//2 - int(spacing * (n - 1) / 2)
        centers = [(startx + i*spacing, HEIGHT//2) for i in range(n)]

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
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
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
    # Collectibles prüfen
    for spec in COLLECTIBLES:
        p = os.path.join(os.path.dirname(__file__), spec["file"])
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
    force_collectible_key = None  # Debug: mit Taste "O" nächsten Spawn auf OTT erzwingen

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
                if event.key == pygame.K_r and not bird.alive:
                    playing = False  # zurück zum Startscreen (mit gewähltem Charakter behalten wir)
                if event.key == pygame.K_o:
                    force_collectible_key = "ott"
                    pygame.display.set_caption(f"{TITLE}  [DEBUG: nächstes Collectible = OTT]")
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
                bird.flap()

        # Logik
        if playing and bird.alive:
            # Pipes spawnen (größerer Abstand = leichter)
            if not pipe_group or (last_pipe_x - max([p.rect.x for p in pipe_group]) >= 320):
                last_pipe_x = WIDTH + 120
                top_p, bot_p, gap_center_y = spawn_pipe_pair(all_sprites, pipe_group, last_pipe_x)
                pipe_spawn_count += 1
                spawn_collectible = False
                if pipe_spawn_count % COLLECTIBLE_EVERY == 0 and random.random() < COLLECTIBLE_PROB:
                    spawn_collectible = True
                if spawn_collectible:
                    if force_collectible_key:
                        # Spezifisches Item erzwingen (Debug)
                        spec = next((c for c in COLLECTIBLES if c["key"] == force_collectible_key), None)
                        force_collectible_key = None
                        pygame.display.set_caption(TITLE)
                        if spec is None:
                            spec = weighted_choice(COLLECTIBLES)
                    else:
                        spec = weighted_choice(COLLECTIBLES)
                    col = Collectible(spec, last_pipe_x + 30, gap_center_y)
                    all_sprites.add(col)
                    collect_group.add(col)

            all_sprites.update(dt)

            # Kollisionen
            for p in pipe_group:
                if bird.rect.colliderect(p.rect):
                    bird.alive = False

            # Kollision mit Collectibles (alle Typen)
            for col in list(collect_group):
                if bird.rect.colliderect(col.rect):
                    score += col.points
                    popup = ScorePopup(col.rect.centerx, col.rect.top - 10, f"+{col.points}", color=getattr(col, "pop_color", (255, 255, 255)))
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
            # Haupttitel
            title_surf = font_big.render("FlappyAkh", True, WHITE)
            screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))

            # Charaktername direkt darunter
            name_surf = font.render(f"{chosen['name']}", True, (255, 240, 0))
            screen.blit(name_surf, name_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 20)))

            # Hinweistext
            hint = font.render("Drück SPACE oder klicke, um zu starten", True, BLACK)
            screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT//2 + 30)))
        else:
            score_surf = font_big.render(str(score), True, WHITE)
            screen.blit(score_surf, score_surf.get_rect(midtop=(WIDTH//2, 20)))

        if playing and not bird.alive:
            over = font_big.render("Game Over", True, BLACK)
            restart = font.render("Drück R für Neustart", True, BLACK)
            screen.blit(over, over.get_rect(center=(WIDTH//2, HEIGHT//2 - 10)))
            screen.blit(restart, restart.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()