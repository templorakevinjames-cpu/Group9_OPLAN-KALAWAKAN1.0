import pygame
import random
import sys
import math
import os
import json
import array

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_ANDROID = (sys.platform == "android") or ("ANDROID_ARGUMENT" in os.environ)

_ASSET_CACHE = {}
def asset_path(filename):
    filename = os.path.basename(filename)
    if filename in _ASSET_CACHE:
        return _ASSET_CACHE[filename]
    candidates = [
        os.path.join(BASE_DIR, filename),
        os.path.join(BASE_DIR, "assets", filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            _ASSET_CACHE[filename] = path
            return path
        try:
            for root, _, files in os.walk(BASE_DIR):
                if filename in files:
                    path = os.path.join(root, filename)
                    _ASSET_CACHE[filename] = path
                    return path
        except OSError:
            pass
    path = os.path.join(BASE_DIR, filename)
    _ASSET_CACHE[filename] = path
    return path

# Name of the custom title/UI font file. Drop "KawitExtended.ttf" (or .otf) next
# to this script, or in an "assets" subfolder, and it'll be picked up automatically.
CUSTOM_FONT_FILE = "KawitExtended.ttf"
_FONT_CACHE = {}
def load_game_font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    path = asset_path(CUSTOM_FONT_FILE)
    if os.path.isfile(path):
        font = pygame.font.Font(path, size)
        if bold:
            font.set_bold(True)
    else:
        font = pygame.font.SysFont("consolas", size, bold=bold)
    _FONT_CACHE[key] = font
    return font

# ---------------------------------------------------------------------------
# Config & Default Game Settings
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1000, 600
FPS = 60

BLACK = (5, 5, 15)
GREEN = (60, 220, 90)
RED = (220, 60, 60)
YELLOW = (240, 210, 60)
WHITE = (235, 235, 235)
CYAN = (80, 200, 220)
PURPLE = (150, 90, 220)
ORANGE = (240, 140, 60)
BLUE = (70, 120, 240)

BG_THEMES = [
    # Manila Bay sunset - deep indigo sky bleeding into that famous fiery orange
    {"top": (8, 12, 45),  "bottom": (255, 130, 55), "planets": [(255, 175, 90), (40, 130, 140)]},
    # Emerald island twilight - tropical sea green fading to warm dusk gold
    {"top": (3, 35, 38),  "bottom": (15, 150, 120), "planets": [(60, 200, 150), (230, 200, 90)]},
    # Watawat - the flag's royal blue field sinking into its scarlet red
    {"top": (8, 10, 55),  "bottom": (170, 20, 35),  "planets": [(255, 205, 60), (60, 90, 170)]},
]
SUN_COLOR = (255, 205, 70)
FLAG_STAR_COLOR = (255, 225, 130)
ISLAND_SILHOUETTE = (6, 10, 14)

class GameSettings:
    def __init__(self):
        self.player_speed = 7
        self.bullet_speed = 10
        self.enemy_bullet_speed = 6
        self.starting_lives = 5
        self.total_levels = 3
        self.win_level = 3
        self.kills_per_level = 10
        self.boss_hp_per_level = 25

SETTINGS = GameSettings()

PLAYER_MAX_X_RATIO = 0.5
STATE_MENU = "menu"
STATE_SETTINGS = "settings"
STATE_LEVEL_INTRO = "level_intro"
STATE_PLAYING = "playing"
STATE_BOSS_INTRO = "boss_intro"
STATE_BOSS = "boss"
STATE_PAUSED = "paused"
STATE_GAMEOVER = "gameover"
STATE_WIN = "win"
STATE_ENTER_NAME = "enter_name"
STATE_SKINS = "skins"
STATE_LEADERBOARD = "leaderboard"

INTRO_DURATION = 90
POWERUP_DROP_CHANCE = 0.18
POWERUP_FALL_SPEED = 1.2
POWERUP_DURATION = {"rapid": 8 * FPS, "spread": 8 * FPS, "shield": 6 * FPS}
POWERUP_COLORS = {"rapid": YELLOW, "spread": CYAN, "shield": GREEN, "life": (255, 90, 160)}
POWERUP_LETTERS = {"rapid": "R", "spread": "S", "shield": "SH", "life": "+1"}

LEADERBOARD_FILE = asset_path("space_impact_leaderboard.json")

SKIN_FILES = [
    "rocket_skin_1.png", "rocket_skin_2.png", "rocket_skin_3.png",
    "rocket_skin_4.png", "rocket_skin_5.png" 
]
SKIN_NAMES = ["Bakbakan Jeepney", "Trike Trooper", "Harurot", "Balangay Navigators", "Mabuhay Welkam to Philippine Airlines"]
BOSS_FILES = ["boss_level_1.png", "boss_level_2.png", "boss_level_3.png"]
ENEMY_FILES = {"grunt": "enemy_small.png", "mini": "enemy_large.png"}

# Title logo image. Drop "title_logo.png" (transparent background recommended)
# next to this script, or in an "assets" subfolder, to replace the text title.
TITLE_IMAGE_FILE = "title_logo.png"
TITLE_IMAGE_MAX_WIDTH = 560

# ---------------------------------------------------------------------------
# Sound & Audio System
# ---------------------------------------------------------------------------
class SoundFX:
    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self.enabled = True
            self.sounds = {
                "shoot": self.make_tone(520, 0.055, 0.18, 180),
                "enemy_hit": self.make_tone(180, 0.08, 0.20, 90),
                "explosion": self.make_explosion(),
                "powerup": self.make_tone(760, 0.12, 0.20, 1100),
                "boss": self.make_boss_warning(),
                "hurt": self.make_tone(110, 0.15, 0.25, 55),
                "level": self.make_tone(420, 0.18, 0.20, 900),
                "win": self.make_win(),
                "gameover": self.make_tone(95, 0.35, 0.22, 45),
            }
        except pygame.error:
            self.enabled = False
            self.sounds = {}

    def make_tone(self, start_freq, duration, volume, end_freq=None):
        rate = 44100
        count = max(1, int(rate * duration))
        end_freq = end_freq or start_freq
        samples = array.array("h")
        for i in range(count):
            t = i / rate
            freq = start_freq + (end_freq - start_freq) * (i / max(1, count - 1))
            envelope = min(1.0, i / max(1, int(rate * 0.01)))
            envelope *= min(1.0, (count - i) / max(1, int(rate * 0.03)))
            value = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * t))
            samples.append(value)
            samples.append(value)  # Stereo duplication
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def make_explosion(self):
        rate = 44100
        duration = 0.28
        count = int(rate * duration)
        samples = array.array("h")
        for i in range(count):
            t = i / rate
            noise = random.uniform(-1, 1)
            tone = math.sin(2 * math.pi * (90 - 55 * t) * t)
            envelope = max(0, 1 - t / duration)
            val = int(32767 * 0.30 * envelope * (0.75 * noise + 0.25 * tone))
            samples.append(val)
            samples.append(val)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def make_boss_warning(self):
        rate = 44100
        samples = array.array("h")
        notes = [(150, 0.18), (110, 0.18), (150, 0.18), (70, 0.35)]
        for freq, duration in notes:
            count = int(rate * duration)
            for i in range(count):
                t = i / rate
                envelope = min(1, i / (rate * 0.01)) * min(1, (count - i) / (rate * 0.04))
                val = int(32767 * 0.25 * envelope * math.sin(2 * math.pi * freq * t))
                samples.append(val)
                samples.append(val)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def make_win(self):
        rate = 44100
        samples = array.array("h")
        notes = [(523, 0.18), (659, 0.18), (784, 0.18), (1047, 0.38)]
        for freq, duration in notes:
            count = int(rate * duration)
            for i in range(count):
                t = i / rate
                envelope = min(1, i / (rate * 0.015)) * min(1, (count - i) / (rate * 0.06))
                val = int(32767 * 0.28 * envelope * math.sin(2 * math.pi * freq * t))
                samples.append(val)
                samples.append(val)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except pygame.error:
                pass

class MusicPlayer:
    EXTERNAL_NAMES = ("bg_music.ogg", "bg_music.mp3", "bg_music.wav", "music.ogg", "music.mp3")
    LEVEL_MUSIC_EXTS = ("mp3", "ogg", "wav")
    BAND_SIZE = 3  # how many levels share one "set" track before switching

    def __init__(self):
        self.enabled = False
        self.default_track = None
        self.channel = None
        self.loop_sound = None
        self.volume = 100
        self.current_source = None  # path of the pygame.mixer.music track currently loaded, or None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

            for name in self.EXTERNAL_NAMES:
                path = asset_path(name)
                if os.path.isfile(path):
                    self.default_track = path
                    break

            # Scan for "set1_music.mp3", "set2_music.mp3", ... - each one covers
            # BAND_SIZE consecutive levels, and the list cycles once you run out.
            self.band_tracks = []
            i = 1
            while i <= 50:
                found = None
                for ext in self.LEVEL_MUSIC_EXTS:
                    p = asset_path(f"set{i}_music.{ext}")
                    if os.path.isfile(p):
                        found = p
                        break
                if found is None:
                    break
                self.band_tracks.append(found)
                i += 1

            # Always build the generated chiptune loop as a guaranteed fallback,
            # used for any level that doesn't have its own music file.
            self.loop_sound = self._make_loop()
            if self.loop_sound is not None:
                if pygame.mixer.get_num_channels() < 16:
                    pygame.mixer.set_num_channels(16)
                self.channel = pygame.mixer.Channel(pygame.mixer.get_num_channels() - 1)

            self.enabled = bool(self.default_track) or bool(self.band_tracks) or self.loop_sound is not None
        except pygame.error:
            self.enabled = False

    def _level_track_path(self, level):
        # Exact override: "level1_music.mp3" / .ogg / .wav, "level2_music.mp3", etc.
        # Takes priority over the every-3-levels "set" tracks below.
        for ext in self.LEVEL_MUSIC_EXTS:
            path = asset_path(f"level{level}_music.{ext}")
            if os.path.isfile(path):
                return path
        return None

    def _band_track_path(self, level):
        if not self.band_tracks:
            return None
        band_idx = ((level - 1) // self.BAND_SIZE) % len(self.band_tracks)
        return self.band_tracks[band_idx]

    def _make_loop(self):
        try:
            rate = 44100
            beat = 60 / 128
            bass_notes = [110.0, 110.0, 146.8, 146.8, 130.8, 130.8, 98.0, 98.0]
            arp_notes = [220.0, 261.6, 329.6, 392.0, 349.2, 293.7, 246.9, 220.0]
            samples = array.array("h")
            step = int(rate * beat)
            sub = max(1, step // 4)
            for bass_f, arp_f in zip(bass_notes, arp_notes):
                for i in range(step):
                    t = i / rate
                    env = min(1.0, i / max(1, int(rate * 0.01))) * min(1.0, (step - i) / max(1, int(rate * 0.05)))
                    arp_env = 1.0 if (i // sub) % 2 == 0 else 0.35
                    bass = 0.55 * math.sin(2 * math.pi * bass_f * t)
                    arp = 0.25 * arp_env * math.sin(2 * math.pi * arp_f * t)
                    value = (bass + arp) * env
                    val = int(max(-32767, min(32767, value * 32767)))
                    samples.append(val)
                    samples.append(val)
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except pygame.error:
            return None

    def play(self, level=None):
        if not self.enabled:
            return
        # Priority: this level's own track > its every-3-levels "set" track >
        # the general fallback track > generated loop
        track = self._level_track_path(level) if level is not None else None
        if track is None and level is not None:
            track = self._band_track_path(level)
        if track is None:
            track = self.default_track
        try:
            if track:
                if track != self.current_source:
                    pygame.mixer.music.load(track)
                    self.current_source = track
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play(loops=-1)
                if self.channel is not None:
                    self.channel.stop()
            elif self.channel is not None and self.loop_sound is not None:
                pygame.mixer.music.stop()
                self.current_source = None
                self.channel.set_volume(self.volume)
                self.channel.play(self.loop_sound, loops=-1)
        except pygame.error:
            pass

    def set_enabled(self, on):
        if not self.enabled:
            return
        vol = self.volume if on else 0.0
        try:
            if self.current_source:
                pygame.mixer.music.set_volume(vol)
            if self.channel is not None:
                self.channel.set_volume(vol)
        except pygame.error:
            pass

# ---------------------------------------------------------------------------
# Helpers & UI Components
# ---------------------------------------------------------------------------
def load_leaderboard():
    try:
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return sorted(data, key=lambda x: x.get("score", 0), reverse=True)[:10]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return []

def save_leaderboard(entries):
    try:
        with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(entries[:10], f, indent=2)
    except OSError:
        pass

def add_score_to_leaderboard(name, score):
    name = (name.strip() or "Player 1")[:12]
    entries = load_leaderboard()
    entries.append({"name": name, "score": int(score)})
    entries.sort(key=lambda x: x.get("score", 0), reverse=True)
    save_leaderboard(entries)
    return entries[:10]

class Button:
    def __init__(self, rect, text, font, base_color=(30, 30, 55),
                 hover_color=(55, 55, 95), text_color=WHITE, border_color=YELLOW):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        color = self.hover_color if hovered else self.base_color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, self.border_color, self.rect, width=2, border_radius=8)
        label = self.font.render(self.text, True, self.text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def hit_test(self, pos):
        return self.rect.collidepoint(pos)

class TouchButton:
    def __init__(self, rect, label):
        self.rect = pygame.Rect(rect)
        self.label = label

    def draw(self, surface, font):
        pygame.draw.rect(surface, (35, 35, 70), self.rect, border_radius=12)
        pygame.draw.rect(surface, ORANGE, self.rect, width=2, border_radius=12)
        cx, cy = self.rect.center
        if self.label in ("<", ">", "^", "v"):
            if self.label == "<": points = [(cx-14, cy), (cx+7, cy-13), (cx+7, cy+13)]
            elif self.label == ">": points = [(cx+14, cy), (cx-7, cy-13), (cx-7, cy+13)]
            elif self.label == "^": points = [(cx, cy-14), (cx-13, cy+7), (cx+13, cy+7)]
            else: points = [(cx, cy+14), (cx-13, cy-7), (cx+13, cy-7)]
            pygame.draw.polygon(surface, WHITE, points)
        else:
            text = font.render(self.label, True, WHITE)
            surface.blit(text, text.get_rect(center=self.rect.center))

# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------
class Background:
    def __init__(self):
        self.theme_index = -1
        self.layers = []
        for count, speed, size_range, color in [
            (70, 0.6, (1, 2), (150, 150, 180)),
            (50, 1.4, (1, 2), (200, 200, 230)),
            (35, 2.6, (2, 3), WHITE),
        ]:
            stars = [
                [random.randint(0, WIDTH), random.randint(0, HEIGHT), speed,
                 random.choice(size_range), color]
                for _ in range(count)
            ]
            self.layers.append(stars)

        self.planets = [
            {"x": WIDTH * 0.8, "y": HEIGHT * 0.25, "r": 55, "speed": 0.15, "ring": True},
            {"x": WIDTH * 0.35, "y": HEIGHT * 0.85, "r": 30, "speed": 0.3, "ring": False},
        ]

        # Philippine sun - the flag's 8-rayed sun, glowing low over the horizon
        self.sun = {"x": WIDTH * 0.17, "y": HEIGHT * 0.34, "r": 38, "angle": 0.0}

        # The flag's three stars (Luzon, Visayas, Mindanao), arced above the sun
        self.flag_stars = [
            {"x": WIDTH * 0.04, "y": HEIGHT * 0.09, "r": 9, "phase": 0.0},
            {"x": WIDTH * 0.19, "y": HEIGHT * 0.05, "r": 9, "phase": 2.1},
            {"x": WIDTH * 0.33, "y": HEIGHT * 0.10, "r": 9, "phase": 4.2},
        ]

        # Distant island silhouettes with coconut palms, drifting like a parallax shoreline
        self.islands = []
        for _ in range(4):
            self.islands.append(self._make_island(random.randint(0, WIDTH)))

        self.time = 0
        self.set_theme(0)

    def _make_island(self, x):
        return {
            "x": x,
            "w": random.randint(140, 260),
            "h": random.randint(22, 42),
            "y": HEIGHT - random.randint(0, 14),
            "speed": random.uniform(0.3, 0.7),
            "palms": random.randint(1, 3),
        }

    def set_theme(self, theme_index):
        theme_index %= len(BG_THEMES)
        if theme_index == self.theme_index:
            return
        self.theme_index = theme_index
        theme = BG_THEMES[theme_index]
        self.gradient = self._make_gradient(theme["top"], theme["bottom"])
        for planet, color in zip(self.planets, theme["planets"]):
            planet["color"] = color

    def _make_gradient(self, top, bottom):
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            pygame.draw.line(surf, color, (0, y), (WIDTH, y))
        return surf

    def update(self):
        self.time += 1
        for stars in self.layers:
            for star in stars:
                star[0] -= star[2]
                if star[0] < 0:
                    star[0] = WIDTH
                    star[1] = random.randint(0, HEIGHT)
        for planet in self.planets:
            planet["x"] -= planet["speed"]
            if planet["x"] < -planet["r"] * 2:
                planet["x"] = WIDTH + planet["r"] * 2
                planet["y"] = random.randint(20, HEIGHT - 20)

        self.sun["angle"] = (self.sun["angle"] + 0.15) % 360

        for island in self.islands:
            island["x"] -= island["speed"]
            if island["x"] < -island["w"]:
                island.update(self._make_island(WIDTH + island["w"]))

    @staticmethod
    def _star_points(cx, cy, outer_r, inner_r, rotation_deg=0.0):
        points = []
        for i in range(10):
            ang = math.radians(rotation_deg + i * 36)
            rad = outer_r if i % 2 == 0 else inner_r
            points.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
        return points

    def _draw_sun(self, surface):
        cx, cy, r, angle = self.sun["x"], self.sun["y"], self.sun["r"], self.sun["angle"]
        for i in range(8):
            a = math.radians(angle + i * 45)
            length = r * 1.9
            width = r * 0.5
            perp = a + math.pi / 2
            tip = (cx + math.cos(a) * length, cy + math.sin(a) * length)
            base1 = (cx + math.cos(a) * r * 0.3 + math.cos(perp) * width * 0.5,
                      cy + math.sin(a) * r * 0.3 + math.sin(perp) * width * 0.5)
            base2 = (cx + math.cos(a) * r * 0.3 - math.cos(perp) * width * 0.5,
                      cy + math.sin(a) * r * 0.3 - math.sin(perp) * width * 0.5)
            pygame.draw.polygon(surface, SUN_COLOR, [base1, base2, tip])
        pygame.draw.circle(surface, SUN_COLOR, (int(cx), int(cy)), int(r * 0.65))
        pygame.draw.circle(surface, tuple(min(255, c + 30) for c in SUN_COLOR),
                            (int(cx), int(cy)), int(r * 0.4))

    def _draw_flag_stars(self, surface):
        for star in self.flag_stars:
            pulse = 1.0 + 0.18 * math.sin(self.time * 0.05 + star["phase"])
            outer = star["r"] * pulse
            points = self._star_points(star["x"], star["y"], outer, outer * 0.42, rotation_deg=-90)
            pygame.draw.polygon(surface, FLAG_STAR_COLOR, points)

    def _draw_islands(self, surface):
        for island in self.islands:
            x, y, w, h = island["x"], island["y"], island["w"], island["h"]
            mound = pygame.Rect(int(x), int(y - h), int(w), int(h * 2))
            pygame.draw.ellipse(surface, ISLAND_SILHOUETTE, mound)
            for p in range(island["palms"]):
                px = x + w * (0.2 + 0.3 * p)
                trunk_top = (px, y - h - 26)
                pygame.draw.line(surface, ISLAND_SILHOUETTE, (px, y - h), trunk_top, 3)
                for fa in (-60, -20, 20, 60):
                    a = math.radians(fa - 90)
                    frond = (trunk_top[0] + math.cos(a) * 20, trunk_top[1] + math.sin(a) * 12)
                    pygame.draw.line(surface, ISLAND_SILHOUETTE, trunk_top, frond, 3)

    def draw(self, surface):
        surface.blit(self.gradient, (0, 0))
        self._draw_sun(surface)
        self._draw_flag_stars(surface)

        for planet in self.planets:
            x, y, r = int(planet["x"]), int(planet["y"]), planet["r"]
            pygame.draw.circle(surface, planet["color"], (x, y), r)
            pygame.draw.circle(
                surface, tuple(min(255, c + 40) for c in planet["color"]),
                (x - r // 3, y - r // 3), r // 3
            )
            if planet["ring"]:
                ring_rect = pygame.Rect(int(x - r * 1.6), int(y - r * 0.4), int(r * 3.2), int(r * 0.8))
                pygame.draw.ellipse(surface, (200, 190, 220), ring_rect, width=3)

        for stars in self.layers:
            for x, y, speed, size, color in stars:
                pygame.draw.circle(surface, color, (int(x), int(y)), size)

        self._draw_islands(surface)

# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, color, owner="player1", kind="normal"):
        super().__init__()
        self.kind = kind
        self.image = self._make_image(kind, color)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx, self.vy = vx, vy
        self.owner = owner
        self.pos = pygame.Vector2(x, y)

    @staticmethod
    def _make_image(kind, color):
        glow = (*color, 90)
        hot = tuple(min(255, c + 90) for c in color)

        if kind == "spread":
            # Small round plasma orb, fired in a fan.
            surf = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(surf, glow, (7, 7), 7)
            pygame.draw.circle(surf, color, (7, 7), 4)
            pygame.draw.circle(surf, hot, (7, 7), 2)
            return surf

        if kind == "rapid":
            # Thin, hot streak for the fast-firing weapon.
            surf = pygame.Surface((20, 8), pygame.SRCALPHA)
            pygame.draw.line(surf, glow, (0, 4), (20, 4), 6)
            pygame.draw.line(surf, hot, (6, 4), (20, 4), 3)
            pygame.draw.circle(surf, WHITE, (18, 4), 2)
            return surf

        if kind == "enemy":
            # Jagged bolt pointed left, toward the player.
            surf = pygame.Surface((16, 10), pygame.SRCALPHA)
            pygame.draw.polygon(surf, glow, [(16, 5), (7, 0), (0, 5), (7, 10)])
            pygame.draw.polygon(surf, color, [(13, 5), (6, 2), (2, 5), (6, 8)])
            pygame.draw.circle(surf, WHITE, (6, 5), 2)
            return surf

        if kind == "boss":
            # Larger glowing orb for boss attacks.
            surf = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(surf, glow, (10, 10), 10)
            pygame.draw.circle(surf, color, (10, 10), 7)
            pygame.draw.circle(surf, WHITE, (10, 10), 3)
            return surf

        # "normal" - a streamlined energy bolt.
        surf = pygame.Surface((16, 7), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, glow, (0, 0, 16, 7))
        pygame.draw.ellipse(surf, color, (3, 1, 11, 5))
        pygame.draw.ellipse(surf, hot, (9, 2, 6, 3))
        return surf

    def update(self):
        self.pos.x += self.vx
        self.pos.y += self.vy
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if self.rect.right < 0 or self.rect.left > WIDTH or self.rect.bottom < 0 or self.rect.top > HEIGHT:
            self.kill()

class Explosion:
    def __init__(self, x, y, size=25):
        self.x, self.y = x, y
        self.timer = 0
        self.duration = 24
        self.size = size
        self.particles = []
        for _ in range(12):
            a = random.uniform(0, math.tau)
            speed = random.uniform(1.5, 4.5)
            self.particles.append([0.0, 0.0, math.cos(a) * speed, math.sin(a) * speed, random.randint(3, 7)])

    def update(self):
        self.timer += 1
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] = max(1, p[4] - 0.15)

    def draw(self, surface):
        ratio = self.timer / self.duration
        for px, py, _, _, radius in self.particles:
            r = max(1, int(radius * (1.3 - ratio * 0.5)))
            pygame.draw.circle(surface, ORANGE, (int(self.x + px), int(self.y + py)), r)
        pygame.draw.circle(surface, YELLOW, (int(self.x), int(self.y)), max(1, int(self.size * (1 - ratio))), width=2)

    @property
    def done(self):
        return self.timer >= self.duration

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, kind):
        super().__init__()
        self.kind = kind
        color = POWERUP_COLORS[kind]
        size = 26
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        pygame.draw.circle(self.image, WHITE, (size // 2, size // 2), size // 2, width=2)
        font = pygame.font.SysFont("consolas", 12, bold=True)
        letter = font.render(POWERUP_LETTERS[kind], True, BLACK)
        self.image.blit(letter, letter.get_rect(center=(size // 2, size // 2)))
        self.rect = self.image.get_rect(center=(x, y))
        self.t = random.uniform(0, 6.28)
        self.base_x = x

    def update(self):
        self.rect.y += POWERUP_FALL_SPEED
        self.t += 0.1
        self.rect.centerx = self.base_x + int(6 * math.sin(self.t))
        if self.rect.top > HEIGHT:
            self.kill()

class Player(pygame.sprite.Sprite):
    def __init__(self, player_num=1, skin_index=0):
        super().__init__()
        self.player_num = player_num
        self.skin_index = skin_index
        self.image = self.make_skin(skin_index)
        self.rect = self.image.get_rect(midleft=(30, HEIGHT // 2 + (70 if player_num == 2 else 0)))
        self.lives = SETTINGS.starting_lives
        self.invincible_timer = 0
        self.cooldown = 0
        self.rapid_timer = 0
        self.spread_timer = 0
        self.shield_timer = 0
        self.thruster_t = random.uniform(0, 10)

    def make_skin(self, index):
        index %= len(SKIN_FILES)
        filename = asset_path(SKIN_FILES[index])
        if os.path.isfile(filename):
            try:
                img = pygame.image.load(filename).convert_alpha()
                return pygame.transform.smoothscale(img, (88, 54))
            except pygame.error:
                pass

        bodies = [GREEN, BLUE, RED, PURPLE, ORANGE, CYAN]
        noses = [CYAN, WHITE, ORANGE, WHITE, YELLOW, WHITE]
        body, nose = bodies[index], noses[index]
        surf = pygame.Surface((88, 54), pygame.SRCALPHA)
        pygame.draw.polygon(surf, body, [(0, 27), (38, 5), (72, 27), (38, 49)])
        pygame.draw.polygon(surf, nose, [(0, 27), (22, 17), (22, 37)])
        pygame.draw.circle(surf, WHITE, (42, 27), 6)
        if index in (3, 4, 5):
            pygame.draw.line(surf, nose, (38, 8), (55, 4), 3)
            pygame.draw.line(surf, nose, (38, 46), (55, 50), 3)
        if index == 4:
            pygame.draw.line(surf, YELLOW, (54, 27), (78, 27), 4)
        if index == 5:
            pygame.draw.circle(surf, PURPLE, (58, 27), 5)
        return surf

    def update(self, keys, controls):
        dx = dy = 0
        p_speed = SETTINGS.player_speed
        if keys[controls["up"]]: dy -= p_speed
        if keys[controls["down"]]: dy += p_speed
        if keys[controls["left"]]: dx -= p_speed
        if keys[controls["right"]]: dx += p_speed

        self.rect.x += dx
        self.rect.y += dy

        max_x = int(WIDTH * PLAYER_MAX_X_RATIO)
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(max_x, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(HEIGHT, self.rect.bottom)

        for attr in ("cooldown", "invincible_timer", "rapid_timer", "spread_timer", "shield_timer"):
            value = getattr(self, attr)
            if value > 0:
                setattr(self, attr, value - 1)

        self.thruster_t += 1

    def shoot(self, bullets_group, all_sprites):
        if self.cooldown != 0:
            return
        color = BLUE if self.player_num == 2 else YELLOW
        b_speed = SETTINGS.bullet_speed
        if self.spread_timer > 0:
            for angle in (-15, 0, 15):
                rad = math.radians(angle)
                b = Bullet(
                    self.rect.right, self.rect.centery,
                    b_speed * math.cos(rad), b_speed * math.sin(rad),
                    color, f"player{self.player_num}", kind="spread"
                )
                bullets_group.add(b)
                all_sprites.add(b)
        else:
            kind = "rapid" if self.rapid_timer > 0 else "normal"
            b = Bullet(self.rect.right, self.rect.centery, b_speed, 0, color, f"player{self.player_num}", kind=kind)
            bullets_group.add(b)
            all_sprites.add(b)
        self.cooldown = 5 if self.rapid_timer > 0 else 12
        if hasattr(self, "game"):
            self.game.sfx.play("shoot")

    def hit(self):
        if self.shield_timer > 0:
            return False
        if self.invincible_timer == 0:
            self.lives -= 1
            self.invincible_timer = 90
            return True
        return False

    def apply_powerup(self, kind):
        if kind == "rapid": self.rapid_timer = POWERUP_DURATION["rapid"]
        elif kind == "spread": self.spread_timer = POWERUP_DURATION["spread"]
        elif kind == "shield": self.shield_timer = POWERUP_DURATION["shield"]
        elif kind == "life": self.lives += 1

    def draw(self, surface):
        if self.invincible_timer % 10 < 5:
            self._draw_thruster(surface)
            surface.blit(self.image, self.rect)
        if self.shield_timer > 0:
            radius = max(self.rect.width, self.rect.height) // 2 + 8
            ring = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*GREEN, 120), (radius, radius), radius, width=3)
            surface.blit(ring, ring.get_rect(center=self.rect.center))

    def _draw_thruster(self, surface):
        # Flickering flame at the rear of the ship (opposite the firing edge).
        flicker = 0.8 + 0.2 * math.sin(self.thruster_t * 0.9) + random.uniform(-0.12, 0.12)
        flicker = max(0.4, flicker)
        boost = 1.35 if self.rapid_timer > 0 else 1.0

        base_x, base_y = self.rect.left + 4, self.rect.centery
        outer_len = 22 * flicker * boost
        outer_w = 13 * flicker
        outer = [
            (base_x, base_y - outer_w / 2),
            (base_x - outer_len, base_y + random.uniform(-2, 2)),
            (base_x, base_y + outer_w / 2),
        ]
        pygame.draw.polygon(surface, ORANGE, outer)

        mid_len = outer_len * 0.62
        mid_w = outer_w * 0.6
        mid = [
            (base_x, base_y - mid_w / 2),
            (base_x - mid_len, base_y),
            (base_x, base_y + mid_w / 2),
        ]
        pygame.draw.polygon(surface, YELLOW, mid)

        core_len = outer_len * 0.3
        pygame.draw.circle(surface, WHITE, (int(base_x - core_len), int(base_y)), max(2, int(3 * flicker)))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, kind="grunt", level=1):
        super().__init__()
        self.kind = kind
        size = 45 if kind == "grunt" else 65
        self.image = self.make_enemy_image(kind, size)
        self.rect = self.image.get_rect(
            midleft=(WIDTH + random.randint(0, 200), random.randint(20, HEIGHT - 20))
        )
        speed_bonus = (level - 1) * 0.4
        self.speed = (random.uniform(2.0, 4.0) if kind == "grunt" else random.uniform(1.2, 2.2)) + speed_bonus
        self.hp = 1 if kind == "grunt" else 3
        self.base_y = self.rect.centery
        self.t = random.uniform(0, 6.28)
        self.shoot_timer = random.randint(60, 180)

    def make_enemy_image(self, kind, size):
        filename = ENEMY_FILES.get(kind)
        if filename and os.path.exists(filename):
            try:
                img = pygame.image.load(filename).convert_alpha()
                return pygame.transform.smoothscale(img, (size, size))
            except pygame.error:
                pass

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        color = RED if kind == "grunt" else PURPLE
        pygame.draw.polygon(
            surf, color,
            [(size, size // 2), (0, 0), (size * 0.3, size // 2), (0, size)]
        )
        pygame.draw.circle(surf, WHITE, (int(size * .62), size // 2), max(3, size // 8))
        return surf

    def update(self):
        self.rect.x -= self.speed
        self.t += 0.05
        self.rect.centery = self.base_y + int(25 * math.sin(self.t))
        if self.rect.right < 0:
            self.kill()
        if self.kind == "mini":
            self.shoot_timer -= 1

    def take_hit(self):
        self.hp -= 1
        return self.hp <= 0

class Boss(pygame.sprite.Sprite):
    def __init__(self, level):
        super().__init__()
        self.level = level
        self.cycle = (level - 1) % max(1, SETTINGS.total_levels)
        size = 110 + self.cycle * 10

        self.image = self.make_boss_image(level, size)
        self.rect = self.image.get_rect(midleft=(WIDTH + 60, HEIGHT // 2))
        self.max_hp = SETTINGS.boss_hp_per_level * level
        self.hp = self.max_hp
        self.entering = True
        self.target_x = WIDTH - size // 2 - 30
        self.t = 0.0
        self.shoot_timer = 60
        self.pattern_toggle = 0

    def make_boss_image(self, level, size):
        filename = BOSS_FILES[(level - 1) % len(BOSS_FILES)]
        filename = asset_path(filename)
        if os.path.exists(filename):
            try:
                img = pygame.image.load(filename).convert_alpha()
                return pygame.transform.smoothscale(img, (size, size))
            except pygame.error:
                pass

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = (max(0, min(255, 200 - level * 20)), 60, min(255, 90 + level * 20))

        cycle_lvl = (level - 1) % 3 + 1
        if cycle_lvl == 1:
            pygame.draw.ellipse(surf, c, (5, size // 2 - 18, size - 10, 42))
            pygame.draw.ellipse(surf, YELLOW, (size // 4, size // 4, size // 2, size // 2))
            for x in (size // 4, size // 2, size * 3 // 4):
                pygame.draw.circle(surf, YELLOW, (int(x), int(size * .68)), 5)
        elif cycle_lvl == 2:
            pygame.draw.ellipse(surf, GREEN, (size * .18, size * .12, size * .64, size * .65))
            pygame.draw.polygon(surf, c, [
                (size * .18, size * .55), (size * .05, size * .92),
                (size * .35, size * .78), (size * .65, size * .78),
                (size * .95, size * .92), (size * .82, size * .55)
            ])
            pygame.draw.ellipse(surf, BLACK, (size * .30, size * .34, size * .14, size * .22))
            pygame.draw.ellipse(surf, BLACK, (size * .56, size * .34, size * .14, size * .22))
        else:
            pygame.draw.polygon(surf, c, [
                (size, size // 2), (size * .62, size * .12), (size * .12, size * .25),
                (0, size // 2), (size * .12, size * .75), (size * .62, size * .88)
            ])
            pygame.draw.polygon(surf, ORANGE, [
                (size * .15, size * .45), (size * .72, size * .45),
                (size * .85, size // 2), (size * .72, size * .55), (size * .15, size * .55)
            ])
        return surf

    def update(self):
        if self.entering:
            self.rect.x -= 3
            if self.rect.centerx <= self.target_x:
                self.entering = False
        else:
            self.t += 0.03
            self.rect.centery = HEIGHT // 2 + int(90 * math.sin(self.t))
            self.shoot_timer -= 1

    def ready_to_shoot(self):
        return not self.entering and self.shoot_timer <= 0

    def reset_shoot_timer(self):
        self.shoot_timer = max(35, 70 - self.level * 8)
        self.pattern_toggle = (self.pattern_toggle + 1) % 2

    def take_hit(self):
        self.hp -= 1
        return self.hp <= 0

    def draw_healthbar(self, surface):
        bar_w, bar_h = 350, 18
        x = WIDTH // 2 - bar_w // 2
        y = 14
        pygame.draw.rect(surface, (40, 40, 50), (x, y, bar_w, bar_h), border_radius=4)
        fill_w = int(bar_w * max(0, self.hp) / self.max_hp)
        color = GREEN if self.hp > self.max_hp * .5 else (ORANGE if self.hp > self.max_hp * .2 else RED)
        pygame.draw.rect(surface, color, (x, y, fill_w, bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE, (x, y, bar_w, bar_h), width=2, border_radius=4)

class Asteroid(pygame.sprite.Sprite):
    def __init__(self, level):
        super().__init__()
        size = random.randint(25, 55)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        points = []
        for i in range(9):
            a = math.tau * i / 9
            r = size * .42 * random.uniform(.75, 1.1)
            points.append((size / 2 + math.cos(a) * r, size / 2 + math.sin(a) * r))
        pygame.draw.polygon(self.image, (105, 100, 110), points)
        pygame.draw.circle(self.image, (65, 65, 75), (size // 3, size // 3), max(2, size // 8))
        self.rect = self.image.get_rect(
            midleft=(WIDTH + random.randint(0, 250), random.randint(15, HEIGHT - 15))
        )
        self.speed = random.uniform(2.0, 4.0) + (level - 3) * .4
        self.angle = random.uniform(0, 360)
        self.spin = random.uniform(-3, 3)

    def update(self):
        self.rect.x -= self.speed
        self.angle += self.spin
        if self.rect.right < 0:
            self.kill()

# ---------------------------------------------------------------------------
# Main Game Loop & Game Manager
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.sfx = SoundFX()
        self.music = MusicPlayer()
        self.music_on = True
        
        self.fullscreen = False
        self.display = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        pygame.display.set_caption("Space Impact")
        self.clock = pygame.time.Clock()

        self.font = load_game_font(22)
        self.big_font = load_game_font(52, bold=True)
        self.mid_font = load_game_font(30, bold=True)
        self.small_font = load_game_font(17)

        self.title_image = self.load_title_image()

        self.background = Background()
        self.state = STATE_MENU
        self.prev_state = STATE_PLAYING
        
        self.render_scale = 1.0
        self.render_offset = (0, 0)
        self.player_name = "Player 1"
        self.leaderboard_saved = False
        self.selected_skin = 0
        self.selected_skin2 = 1
        self.skins_editing = 1
        self.two_player = False
        self.touch_mode = IS_ANDROID
        self.active_touches = {}

        self.shake_magnitude = 0
        self.shake_timer = 0
        self.shake_max_timer = 1
        self.explosions = []

        self._build_buttons()
        self.full_reset()
        self.music.play()

    def set_fullscreen(self, enable):
        self.fullscreen = enable
        if self.fullscreen:
            self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.display = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    def _build_buttons(self):
        cx = WIDTH // 2
        self.start_button = Button((cx - 110, 200, 220, 44), "1 PLAYER", self.mid_font)
        self.two_player_button = Button((cx - 110, 255, 220, 44), "2 PLAYERS", self.mid_font)
        self.settings_button = Button((cx - 110, 310, 220, 44), "SETTINGS", self.mid_font)
        self.skin_button = Button((cx - 110, 365, 220, 44), "ROCKET SKINS", self.mid_font)
        self.lb_button = Button((cx - 110, 420, 220, 44), "LEADERBOARD", self.mid_font)
        self.quit_button = Button((cx - 110, 475, 220, 44), "QUIT", self.mid_font)
        self.touch_toggle_button = Button((cx - 115, 530, 110, 40), "TOUCH: OFF", self.small_font)
        self.music_toggle_button = Button((cx + 5, 530, 110, 40), "MUSIC: ON", self.small_font)

        self.set_btn_pspeed = Button((cx + 80, 100, 40, 30), "+", self.mid_font)
        self.set_btn_pspeed_sub = Button((cx - 120, 100, 40, 30), "-", self.mid_font)
        
        self.set_btn_bspeed = Button((cx + 80, 145, 40, 30), "+", self.mid_font)
        self.set_btn_bspeed_sub = Button((cx - 120, 145, 40, 30), "-", self.mid_font)

        self.set_btn_ebspeed = Button((cx + 80, 190, 40, 30), "+", self.mid_font)
        self.set_btn_ebspeed_sub = Button((cx - 120, 190, 40, 30), "-", self.mid_font)

        self.set_btn_lives = Button((cx + 80, 235, 40, 30), "+", self.mid_font)
        self.set_btn_lives_sub = Button((cx - 120, 235, 40, 30), "-", self.mid_font)

        self.set_btn_totlvl = Button((cx + 80, 280, 40, 30), "+", self.mid_font)
        self.set_btn_totlvl_sub = Button((cx - 120, 280, 40, 30), "-", self.mid_font)

        self.set_btn_winlvl = Button((cx + 80, 325, 40, 30), "+", self.mid_font)
        self.set_btn_winlvl_sub = Button((cx - 120, 325, 40, 30), "-", self.mid_font)

        self.set_btn_kills = Button((cx + 80, 370, 40, 30), "+", self.mid_font)
        self.set_btn_kills_sub = Button((cx - 120, 370, 40, 30), "-", self.mid_font)

        self.set_btn_bosshp = Button((cx + 80, 415, 40, 30), "+", self.mid_font)
        self.set_btn_bosshp_sub = Button((cx - 120, 415, 40, 30), "-", self.mid_font)

        self.set_fullscreen_btn = Button((cx - 110, 465, 220, 40), "FULLSCREEN: OFF", self.small_font)
        self.settings_back = Button((cx - 110, 520, 220, 45), "BACK", self.mid_font)

        self.resume_button = Button((cx - 110, 235, 220, 48), "RESUME", self.mid_font)
        self.pause_quit_button = Button((cx - 110, 295, 220, 48), "QUIT TO MENU", self.mid_font)
        self.restart_button = Button((cx - 110, 360, 220, 48), "RESTART", self.mid_font)
        self.menu_button = Button((cx - 110, 420, 220, 48), "MAIN MENU", self.mid_font)
        self.pause_button = Button((875, 82, 110, 42), "PAUSE", self.small_font)

        self.name_submit_button = Button((cx - 110, 380, 220, 48), "SUBMIT", self.mid_font)
        self.name_backspace_button = Button((cx - 110, 440, 220, 40), "BACKSPACE", self.small_font)

        self.skin_left = Button((120, 450, 100, 48), "<", self.mid_font)
        self.skin_right = Button((780, 450, 100, 48), ">", self.mid_font)
        self.skin_back = Button((cx - 110, 510, 220, 45), "BACK", self.mid_font)
        self.skin_player_toggle = Button((cx - 110, 172, 220, 42), "EDITING: PLAYER 1", self.small_font)
        self.lb_back = Button((cx - 110, 520, 220, 45), "BACK", self.mid_font)

        self.touch_left = TouchButton((20, 470, 52, 52), "<")
        self.touch_right = TouchButton((132, 470, 52, 52), ">")
        self.touch_up = TouchButton((76, 414, 52, 52), "^")
        self.touch_down = TouchButton((76, 526, 52, 52), "v")
        self.touch_fire = TouchButton((875, 470, 100, 52), "FIRE")
        self.touch1_fire_2p = TouchButton((205, 470, 100, 52), "FIRE")

        self.touch2_left = TouchButton((756, 470, 52, 52), "<")
        self.touch2_right = TouchButton((868, 470, 52, 52), ">")
        self.touch2_up = TouchButton((812, 414, 52, 52), "^")
        self.touch2_down = TouchButton((812, 526, 52, 52), "v")
        self.touch2_fire = TouchButton((650, 470, 100, 52), "FIRE")

    def full_reset(self):
        self.level = 1
        self.player = Player(1, self.selected_skin)
        self.player.game = self
        self.player2 = Player(2, self.selected_skin2) if self.two_player else None
        if self.player2:
            self.player2.game = self
        self.score = 0
        self.score2 = 0
        self.leaderboard_saved = False
        self.name_entry = ""
        self.pending_end_state = None
        self.level_reset()

    def level_reset(self):
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.asteroids = pygame.sprite.Group()
        self.all_sprites.add(self.player)
        if self.player2:
            self.all_sprites.add(self.player2)

        self.kills_this_level = 0
        self.kills_needed = SETTINGS.kills_per_level * self.level
        self.background.set_theme((self.level - 1) % max(1, SETTINGS.total_levels))
        self.music.play(self.level)
        self.spawn_timer = 30
        self.asteroid_timer = 100
        self.boss = None
        self.intro_timer = INTRO_DURATION

    def spawn_enemy(self):
        kind = "mini" if random.random() < 0.2 else "grunt"
        e = Enemy(kind, self.level)
        self.enemies.add(e)
        self.all_sprites.add(e)

    def spawn_asteroid(self):
        a = Asteroid(self.level)
        self.asteroids.add(a)
        self.all_sprites.add(a)

    def maybe_drop_powerup(self, x, y, guaranteed=False):
        if not guaranteed and random.random() > POWERUP_DROP_CHANCE:
            return
        kind = random.choices(["rapid", "spread", "shield", "life"], weights=[35, 30, 25, 10], k=1)[0]
        p = PowerUp(x, y, kind)
        self.powerups.add(p)
        self.all_sprites.add(p)

    def enemy_shoot(self, enemy):
        b = Bullet(enemy.rect.left, enemy.rect.centery, -SETTINGS.enemy_bullet_speed, 0, RED, "enemy", kind="enemy")
        self.enemy_bullets.add(b)
        self.all_sprites.add(b)

    def boss_shoot(self):
        bx, by = self.boss.rect.left, self.boss.rect.centery
        e_speed = SETTINGS.enemy_bullet_speed
        if self.boss.pattern_toggle == 0:
            for angle in (-20, 0, 20):
                rad = math.radians(angle)
                b = Bullet(bx, by, -e_speed * math.cos(rad), e_speed * math.sin(rad), ORANGE, "enemy", kind="boss")
                self.enemy_bullets.add(b)
                self.all_sprites.add(b)
        else:
            for dy in (-14, 14):
                b = Bullet(bx, by + dy, -e_speed - 1, 0, ORANGE, "enemy", kind="boss")
                self.enemy_bullets.add(b)
                self.all_sprites.add(b)
        self.boss.reset_shoot_timer()

    def trigger_shake(self, magnitude, duration):
        self.shake_magnitude = magnitude
        self.shake_timer = duration
        self.shake_max_timer = duration

    def get_shake_offset(self):
        if self.shake_timer <= 0:
            return (0, 0)
        ratio = self.shake_timer / self.shake_max_timer
        mag = self.shake_magnitude * ratio
        return (random.randint(-int(mag), int(mag)), random.randint(-int(mag), int(mag)))

    def controls_for_player(self, num):
        if num == 1:
            return {"up": pygame.K_w, "down": pygame.K_s, "left": pygame.K_a, "right": pygame.K_d, "fire": pygame.K_SPACE}
        return {"up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT, "fire": pygame.K_RCTRL}

    def touch_pressed(self, rect):
        if not self.touch_mode:
            return False
        return any(rect.collidepoint(pos) for pos in self.active_touches.values())

    def update_player(self, player, controls, mobile=False, touch_prefix="p1"):
        keys = pygame.key.get_pressed()
        player.update(keys, controls)

        if mobile and self.touch_mode:
            if touch_prefix == "p1":
                fire_button = self.touch1_fire_2p if self.two_player else self.touch_fire
                left, right, up, down, fire = self.touch_left, self.touch_right, self.touch_up, self.touch_down, fire_button
            else:
                left, right, up, down, fire = self.touch2_left, self.touch2_right, self.touch2_up, self.touch2_down, self.touch2_fire

            p_speed = SETTINGS.player_speed
            if self.touch_pressed(left.rect): player.rect.x -= p_speed
            if self.touch_pressed(right.rect): player.rect.x += p_speed
            if self.touch_pressed(up.rect): player.rect.y -= p_speed
            if self.touch_pressed(down.rect): player.rect.y += p_speed

            max_x = int(WIDTH * PLAYER_MAX_X_RATIO)
            player.rect.left = max(0, self.rect.left if hasattr(self, 'rect') else 0)
            player.rect.left = max(0, player.rect.left)
            player.rect.right = min(max_x, player.rect.right)
            player.rect.top = max(0, player.rect.top)
            player.rect.bottom = min(HEIGHT, player.rect.bottom)

            if self.touch_pressed(fire.rect):
                player.shoot(self.player_bullets, self.all_sprites)

    def update(self):
        self.background.update()
        if self.shake_timer > 0:
            self.shake_timer -= 1

        for exp in self.explosions:
            exp.update()
        self.explosions = [e for e in self.explosions if not e.done]

        if self.state == STATE_LEVEL_INTRO:
            self.intro_timer -= 1
            if self.intro_timer <= 0:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_BOSS_INTRO:
            self.intro_timer -= 1
            if self.intro_timer <= 0:
                self.boss = Boss(self.level)
                self.all_sprites.add(self.boss)
                self.state = STATE_BOSS
            return

        if self.state not in (STATE_PLAYING, STATE_BOSS):
            return

        p1c = self.controls_for_player(1)
        self.update_player(self.player, p1c, mobile=True)
        if pygame.key.get_pressed()[p1c["fire"]]:
            self.player.shoot(self.player_bullets, self.all_sprites)

        if self.player2:
            p2c = self.controls_for_player(2)
            self.update_player(self.player2, p2c, mobile=True, touch_prefix="p2")
            if pygame.key.get_pressed()[p2c["fire"]]:
                self.player2.shoot(self.player_bullets, self.all_sprites)

        self.player_bullets.update()
        self.enemy_bullets.update()

        if self.state == STATE_PLAYING:
            self.enemies.update()
            self.asteroids.update()

            self.spawn_timer -= 1
            if self.spawn_timer <= 0 and self.kills_this_level < self.kills_needed:
                self.spawn_enemy()
                self.spawn_timer = random.randint(45, 85)

            if self.level >= 3:
                self.asteroid_timer -= 1
                if self.asteroid_timer <= 0:
                    self.spawn_asteroid()
                    self.asteroid_timer = random.randint(80, 150)

            for enemy in list(self.enemies):
                if enemy.kind == "mini" and enemy.shoot_timer <= 0:
                    self.enemy_shoot(enemy)
                    enemy.shoot_timer = random.randint(70, 140)

            hits = pygame.sprite.groupcollide(self.enemies, self.player_bullets, False, True)
            for enemy, bullets in hits.items():
                if enemy.take_hit():
                    x, y = enemy.rect.center
                    enemy.kill()
                    self.explosions.append(Explosion(x, y, enemy.rect.width))
                    
                    pts = 10 if enemy.kind == "grunt" else 25
                    scorer = bullets[0].owner if bullets else "player1"
                    if scorer == "player2":
                        self.score2 += pts
                    else:
                        self.score += pts
                    
                    self.sfx.play("explosion")
                    self.kills_this_level += 1
                    self.maybe_drop_powerup(x, y)
                    self.trigger_shake(3, 6)

            asteroid_hits = pygame.sprite.groupcollide(self.asteroids, self.player_bullets, True, True)
            for asteroid, bullets in asteroid_hits.items():
                self.explosions.append(Explosion(*asteroid.rect.center, 18))
                self.sfx.play("explosion")
                scorer = bullets[0].owner if bullets else "player1"
                if scorer == "player2":
                    self.score2 += 15
                else:
                    self.score += 15

            for player in [self.player] + ([self.player2] if self.player2 else []):
                if pygame.sprite.spritecollide(player, self.asteroids, True):
                    if player.hit() and player.lives <= 0:
                        self.sfx.play("hurt")
                        self.handle_player_death(player)
                    else:
                        self.sfx.play("hurt")
                        self.trigger_shake(8, 14)

            for player in [self.player] + ([self.player2] if self.player2 else []):
                if pygame.sprite.spritecollide(player, self.enemies, True):
                    if player.hit() and player.lives <= 0:
                        self.sfx.play("hurt")
                        self.handle_player_death(player)
                    else:
                        self.trigger_shake(8, 14)

            if self.kills_this_level >= self.kills_needed:
                self.enemies.empty()
                self.state = STATE_BOSS_INTRO
                self.intro_timer = INTRO_DURATION
                self.sfx.play("boss")

        elif self.state == STATE_BOSS:
            self.boss.update()
            if self.boss.ready_to_shoot():
                self.boss_shoot()

            boss_hits = pygame.sprite.spritecollide(self.boss, self.player_bullets, True)
            for bullet in boss_hits:
                self.trigger_shake(4, 8)
                if self.boss.take_hit():
                    x, y = self.boss.rect.center
                    self.explosions.append(Explosion(x, y, 50))
                    
                    pts = 200 * self.level
                    if bullet.owner == "player2":
                        self.score2 += pts
                    else:
                        self.score += pts

                    self.maybe_drop_powerup(x, y, guaranteed=True)
                    self.boss.kill()
                    self.boss = None
                    self.trigger_shake(20, 35)
                    if self.level >= SETTINGS.win_level:
                        self.begin_name_entry(STATE_WIN)
                    else:
                        self.sfx.play("level")
                        self.level += 1
                        self.level_reset()
                        self.state = STATE_LEVEL_INTRO
                    break

            if self.boss is not None:
                for player in [self.player] + ([self.player2] if self.player2 else []):
                    if pygame.sprite.collide_rect(player, self.boss):
                        if player.hit() and player.lives <= 0:
                            self.handle_player_death(player)
                        else:
                            self.sfx.play("hurt")
                            self.trigger_shake(10, 16)

        if self.state in (STATE_PLAYING, STATE_BOSS):
            self.powerups.update()
            for p in pygame.sprite.spritecollide(self.player, self.powerups, True):
                self.player.apply_powerup(p.kind)
                self.sfx.play("powerup")
            if self.player2:
                for p in pygame.sprite.spritecollide(self.player2, self.powerups, True):
                    self.player2.apply_powerup(p.kind)
                    self.sfx.play("powerup")

            for player in [self.player] + ([self.player2] if self.player2 else []):
                if pygame.sprite.spritecollide(player, self.enemy_bullets, True):
                    if player.hit() and player.lives <= 0:
                        self.sfx.play("hurt")
                        self.handle_player_death(player)
                    else:
                        self.sfx.play("hurt")
                        self.trigger_shake(6, 10)

    def handle_player_death(self, player):
        if self.two_player and self.player.lives <= 0 and self.player2 and self.player2.lives > 0:
            self.player.kill()
            return
        if self.two_player and self.player2 and self.player2.lives <= 0 and self.player.lives > 0:
            self.player2.kill()
            return
        self.sfx.play("gameover")
        self.trigger_shake(18, 30)
        self.begin_name_entry(STATE_GAMEOVER)

    def begin_name_entry(self, pending_state):
        self.pending_end_state = pending_state
        self.name_entry = (self.player_name or "")[:12]
        self.state = STATE_ENTER_NAME
        if pending_state == STATE_WIN:
            self.sfx.play("win")
        try:
            pygame.key.start_text_input()
        except Exception:
            pass

    def submit_name_entry(self):
        name = (self.name_entry.strip() or "Player 1")[:12]
        self.player_name = name
        final_score = max(self.score, self.score2) if self.two_player else self.score
        add_score_to_leaderboard(name, final_score)
        self.leaderboard_saved = True
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass
        self.state = self.pending_end_state or STATE_GAMEOVER

    def draw(self):
        self.background.draw(self.screen)

        if self.state == STATE_MENU:
            self.draw_menu()
            self.present()
            return

        for enemy in self.enemies: self.screen.blit(enemy.image, enemy.rect)
        for asteroid in self.asteroids: self.screen.blit(asteroid.image, asteroid.rect)
        if self.boss is not None: self.screen.blit(self.boss.image, self.boss.rect)
        for bullet in self.player_bullets: self.screen.blit(bullet.image, bullet.rect)
        for bullet in self.enemy_bullets: self.screen.blit(bullet.image, bullet.rect)
        for p in self.powerups: self.screen.blit(p.image, p.rect)

        self.player.draw(self.screen)
        if self.player2: self.player2.draw(self.screen)
        for exp in self.explosions: exp.draw(self.screen)

        self.draw_hud()

        if self.state == STATE_LEVEL_INTRO: self.draw_level_intro()
        elif self.state == STATE_BOSS_INTRO: self.draw_boss_intro()
        elif self.state == STATE_BOSS and self.boss is not None: self.boss.draw_healthbar(self.screen)
        elif self.state == STATE_PAUSED: self.draw_pause()
        elif self.state == STATE_GAMEOVER: self.draw_gameover()
        elif self.state == STATE_WIN: self.draw_win()
        elif self.state == STATE_ENTER_NAME: self.draw_enter_name()
        elif self.state == STATE_SKINS: self.draw_skins()
        elif self.state == STATE_LEADERBOARD: self.draw_leaderboard()
        elif self.state == STATE_SETTINGS: self.draw_settings()

        if self.state in (STATE_PLAYING, STATE_BOSS):
            self.pause_button.draw(self.screen, self.to_virtual_pos(pygame.mouse.get_pos()))

        if self.touch_mode and self.state in (STATE_PLAYING, STATE_BOSS):
            self.touch_left.draw(self.screen, self.small_font)
            self.touch_right.draw(self.screen, self.small_font)
            self.touch_up.draw(self.screen, self.small_font)
            self.touch_down.draw(self.screen, self.small_font)
            (self.touch1_fire_2p if self.two_player else self.touch_fire).draw(self.screen, self.small_font)
            if self.two_player:
                self.touch2_left.draw(self.screen, self.small_font)
                self.touch2_right.draw(self.screen, self.small_font)
                self.touch2_up.draw(self.screen, self.small_font)
                self.touch2_down.draw(self.screen, self.small_font)
                self.touch2_fire.draw(self.screen, self.small_font)

        self.present()

    def present(self):
        self.display.fill(BLACK)
        dw, dh = self.display.get_size()
        scale = min(dw / WIDTH, dh / HEIGHT) if dw and dh else 1.0
        scale = max(scale, 0.0001)
        sw, sh = max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale))
        self.render_scale = scale
        self.render_offset = ((dw - sw) // 2, (dh - sh) // 2)

        shake = self.get_shake_offset()
        scaled = pygame.transform.smoothscale(self.screen, (sw, sh))
        self.display.blit(scaled, (self.render_offset[0] + shake[0], self.render_offset[1] + shake[1]))
        pygame.display.flip()

    def to_virtual_pos(self, pos):
        x, y = pos
        ox, oy = self.render_offset
        return ((x - ox) / self.render_scale, (y - oy) / self.render_scale)

    def draw_hud(self):
        self.screen.blit(self.font.render(f"P1 Score: {self.score}", True, WHITE), (10, 10))
        self.screen.blit(self.font.render(f"P1 Lives: {self.player.lives}", True, WHITE), (10, 38))
        if self.player2:
            self.screen.blit(self.font.render(f"P2 Score: {self.score2}", True, CYAN), (10, 66))
            self.screen.blit(self.font.render(f"P2 Lives: {self.player2.lives}", True, CYAN), (10, 94))
        level = self.font.render(f"Level: {self.level}/{SETTINGS.total_levels}", True, WHITE)
        self.screen.blit(level, (WIDTH - level.get_width() - 10, 10))

        if self.state == STATE_PLAYING:
            prog = self.font.render(f"Cleared: {self.kills_this_level}/{self.kills_needed}", True, WHITE)
            self.screen.blit(prog, (WIDTH - prog.get_width() - 10, 38))

    def load_title_image(self):
        filename = asset_path(TITLE_IMAGE_FILE)
        if os.path.isfile(filename):
            try:
                img = pygame.image.load(filename).convert_alpha()
                w, h = img.get_size()
                if w > TITLE_IMAGE_MAX_WIDTH:
                    scale = TITLE_IMAGE_MAX_WIDTH / w
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                return img
            except pygame.error:
                pass
        return None

    def draw_menu(self):
        if self.title_image:
            self.screen.blit(self.title_image, self.title_image.get_rect(center=(WIDTH // 2, 90)))
        else:
            title = self.big_font.render("OPLAN KALAWAKAN", True, YELLOW)
            self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 90)))
        sub = self.small_font.render(
            "WASD + SPACE = P1   |   ARROWS + Right Ctrl = P2   |   Touch controls supported",
            True, WHITE
        )
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 140)))
        self.touch_toggle_button.text = "TOUCH: ON" if self.touch_mode else "TOUCH: OFF"
        self.music_toggle_button.text = "MUSIC: ON" if self.music_on else "MUSIC: OFF"

        mp = self.to_virtual_pos(pygame.mouse.get_pos())
        for b in (self.start_button, self.two_player_button, self.settings_button, self.skin_button,
                  self.lb_button, self.quit_button, self.touch_toggle_button, self.music_toggle_button):
            b.draw(self.screen, mp)

    def draw_settings(self):
        self.overlay(180)
        self.center_text("SETTINGS", self.big_font, CYAN, -240)
        mp = self.to_virtual_pos(pygame.mouse.get_pos())
        
        cx = WIDTH // 2
        items = [
            ("Player Speed", SETTINGS.player_speed, 100, self.set_btn_pspeed_sub, self.set_btn_pspeed),
            ("Bullet Speed", SETTINGS.bullet_speed, 145, self.set_btn_bspeed_sub, self.set_btn_bspeed),
            ("Enemy Bullet Speed", SETTINGS.enemy_bullet_speed, 190, self.set_btn_ebspeed_sub, self.set_btn_ebspeed),
            ("Starting Lives", SETTINGS.starting_lives, 235, self.set_btn_lives_sub, self.set_btn_lives),
            ("Total Levels", SETTINGS.total_levels, 280, self.set_btn_totlvl_sub, self.set_btn_totlvl),
            ("Win Level", SETTINGS.win_level, 325, self.set_btn_winlvl_sub, self.set_btn_winlvl),
            ("Kills / Level", SETTINGS.kills_per_level, 370, self.set_btn_kills_sub, self.set_btn_kills),
            ("Boss HP / Level", SETTINGS.boss_hp_per_level, 415, self.set_btn_bosshp_sub, self.set_btn_bosshp),
        ]

        for label, val, y, btn_sub, btn_add in items:
            lbl_surf = self.small_font.render(f"{label}:", True, WHITE)
            val_surf = self.small_font.render(str(val), True, YELLOW)
            self.screen.blit(lbl_surf, (cx - 320, y + 5))
            self.screen.blit(val_surf, (cx - 20, y + 5))
            btn_sub.draw(self.screen, mp)
            btn_add.draw(self.screen, mp)

        self.set_fullscreen_btn.text = "FULLSCREEN: ON" if self.fullscreen else "FULLSCREEN: OFF"
        self.set_fullscreen_btn.draw(self.screen, mp)
        self.settings_back.draw(self.screen, mp)

    def draw_level_intro(self):
        self.overlay(140)
        self.center_text(f"LEVEL {self.level}", self.big_font, CYAN, -20)
        boss_names = ["SPACEBALANG", "PLANET EATER BAKUNAWA", "HALO2 DESTROYER"]
        boss_name = boss_names[(self.level - 1) % len(boss_names)]
        sub = self.font.render(
            f"Defeat {self.kills_needed} enemies • Boss: {boss_name}",
            True, WHITE
        )
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))

    def draw_boss_intro(self):
        self.overlay(150)
        self.center_text("WARNING", self.big_font, RED, -30)
        boss_names = ["SPACEBALANG", "PLANET EATER BAKUNAWA", "HALO2 DESTROYER"]
        boss_name = boss_names[(self.level - 1) % len(boss_names)]
        sub = self.mid_font.render(f"{boss_name} BOSS INCOMING", True, ORANGE)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

    def draw_pause(self):
        self.overlay(160)
        self.center_text("PAUSED", self.big_font, WHITE, -70)
        mp = self.to_virtual_pos(pygame.mouse.get_pos())
        self.resume_button.draw(self.screen, mp)
        self.pause_quit_button.draw(self.screen, mp)

    def draw_gameover(self):
        self.overlay(180)
        self.center_text("GAME OVER", self.big_font, RED, -120)
        score_txt = f"Score: {self.score}" if not self.two_player else f"P1: {self.score}  P2: {self.score2}"
        s = self.mid_font.render(f"{score_txt}   Level {self.level}", True, WHITE)
        self.screen.blit(s, s.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
        mp = self.to_virtual_pos(pygame.mouse.get_pos())
        self.restart_button.draw(self.screen, mp)
        self.menu_button.draw(self.screen, mp)
        hint = self.small_font.render("or press R to restart", True, (170, 170, 170))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 480)))

    def draw_win(self):
        self.overlay(180)
        self.center_text("YOU WIN!", self.big_font, YELLOW, -110)
        score_txt = f"Final Score: {self.score}" if not self.two_player else f"P1: {self.score}  P2: {self.score2}"
        s = self.mid_font.render(score_txt, True, WHITE)
        self.screen.blit(s, s.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 55)))
        mp = self.to_virtual_pos(pygame.mouse.get_pos())
        self.restart_button.draw(self.screen, mp)
        self.menu_button.draw(self.screen, mp)
        hint = self.small_font.render("or press R to restart • ESC for menu", True, (170, 170, 170))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 480)))

    def draw_enter_name(self):
        self.overlay(180)
        title = "YOU WIN!" if self.pending_end_state == STATE_WIN else "GAME OVER"
        color = YELLOW if self.pending_end_state == STATE_WIN else RED
        self.center_text(title, self.big_font, color, -170)
        score_val = max(self.score, self.score2) if self.two_player else self.score
        s = self.mid_font.render(f"Score: {score_val}", True, WHITE)
        self.screen.blit(s, s.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 115)))
        self.center_text("Enter your name for the leaderboard:", self.font, WHITE, -70)

        box_rect = pygame.Rect(WIDTH // 2 - 160, HEIGHT // 2 - 40, 320, 48)
        pygame.draw.rect(self.screen, (25, 25, 45), box_rect, border_radius=8)
        pygame.draw.rect(self.screen, ORANGE, box_rect, width=2, border_radius=8)
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        name_surf = self.mid_font.render(self.name_entry + cursor, True, WHITE)
        self.screen.blit(name_surf, name_surf.get_rect(midleft=(box_rect.x + 12, box_rect.centery)))

        mp = self.to_virtual_pos(pygame.mouse.get_pos())
        self.name_submit_button.draw(self.screen, mp)
        self.name_backspace_button.draw(self.screen, mp)
        self.center_text("or press Enter to submit", self.small_font, (170, 170, 170), 145)

    def draw_skins(self):
        self.overlay(170)
        self.center_text("ROCKET SKINS", self.big_font, RED, -180)

        editing_index = self.selected_skin if self.skins_editing == 1 else self.selected_skin2
        name = SKIN_NAMES[editing_index]
        label = self.mid_font.render(name, True, WHITE)
        self.screen.blit(label, label.get_rect(center=(WIDTH // 2, 350)))

        preview = Player(self.skins_editing, editing_index)
        preview.rect.center = (WIDTH // 2, 270)
        preview.draw(self.screen)

        self.skin_player_toggle.text = f"EDITING: PLAYER {self.skins_editing}"
        self.skin_player_toggle.border_color = WHITE if self.skins_editing == 1 else ORANGE

        mp = self.to_virtual_pos(pygame.mouse.get_pos())
        self.skin_player_toggle.draw(self.screen, mp)
        self.skin_left.draw(self.screen, mp)
        self.skin_right.draw(self.screen, mp)
        self.skin_back.draw(self.screen, mp)

    def draw_leaderboard(self):
        self.overlay(170)
        self.center_text("LEADERBOARD", self.big_font, YELLOW, -220)
        entries = load_leaderboard()
        if not entries:
            self.center_text("No scores yet — be the first!", self.mid_font, WHITE, -30)
        else:
            y = 175
            for i, entry in enumerate(entries[:10], 1):
                line = self.font.render(
                    f"{i:>2}. {entry.get('name','Player 1'):<12} {entry.get('score',0):>6}",
                    True, WHITE
                )
                self.screen.blit(line, line.get_rect(center=(WIDTH // 2, y)))
                y += 32
        self.lb_back.draw(self.screen, self.to_virtual_pos(pygame.mouse.get_pos()))

    def overlay(self, alpha):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        self.screen.blit(shade, (0, 0))

    def center_text(self, text, font, color, offset=0):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + offset)))

    def start_game(self, two_player=False):
        self.two_player = two_player
        self.full_reset()
        self.state = STATE_LEVEL_INTRO

    def pointer_virtual_pos(self, event):
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            dw, dh = self.display.get_size()
            return self.to_virtual_pos((event.x * dw, event.y * dh))
        return self.to_virtual_pos(event.pos)

    def pointer_id(self, event):
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return getattr(event, "finger_id", 0)
        return -1

    def handle_pointer_down(self, pos, pointer_id):
        self.active_touches[pointer_id] = pos

        if self.state == STATE_MENU:
            if self.start_button.hit_test(pos):
                self.touch_mode = self.touch_mode or IS_ANDROID
                self.start_game(False)
            elif self.two_player_button.hit_test(pos):
                self.touch_mode = self.touch_mode or IS_ANDROID
                self.start_game(True)
            elif self.settings_button.hit_test(pos):
                self.state = STATE_SETTINGS
            elif self.skin_button.hit_test(pos):
                self.state = STATE_SKINS
            elif self.lb_button.hit_test(pos):
                self.state = STATE_LEADERBOARD
            elif self.quit_button.hit_test(pos):
                pygame.quit(); sys.exit()
            elif self.touch_toggle_button.hit_test(pos):
                self.touch_mode = not self.touch_mode
            elif self.music_toggle_button.hit_test(pos):
                self.music_on = not self.music_on
                self.music.set_enabled(self.music_on)

        elif self.state == STATE_SETTINGS:
            if self.set_btn_pspeed.hit_test(pos): SETTINGS.player_speed = min(20, SETTINGS.player_speed + 1)
            elif self.set_btn_pspeed_sub.hit_test(pos): SETTINGS.player_speed = max(1, SETTINGS.player_speed - 1)
            elif self.set_btn_bspeed.hit_test(pos): SETTINGS.bullet_speed = min(30, SETTINGS.bullet_speed + 1)
            elif self.set_btn_bspeed_sub.hit_test(pos): SETTINGS.bullet_speed = max(1, SETTINGS.bullet_speed - 1)
            elif self.set_btn_ebspeed.hit_test(pos): SETTINGS.enemy_bullet_speed = min(20, SETTINGS.enemy_bullet_speed + 1)
            elif self.set_btn_ebspeed_sub.hit_test(pos): SETTINGS.enemy_bullet_speed = max(1, SETTINGS.enemy_bullet_speed - 1)
            elif self.set_btn_lives.hit_test(pos): SETTINGS.starting_lives = min(20, SETTINGS.starting_lives + 1)
            elif self.set_btn_lives_sub.hit_test(pos): SETTINGS.starting_lives = max(1, SETTINGS.starting_lives - 1)
            elif self.set_btn_totlvl.hit_test(pos): SETTINGS.total_levels = min(10, SETTINGS.total_levels + 1)
            elif self.set_btn_totlvl_sub.hit_test(pos): SETTINGS.total_levels = max(1, SETTINGS.total_levels - 1)
            elif self.set_btn_winlvl.hit_test(pos): SETTINGS.win_level = min(SETTINGS.total_levels, SETTINGS.win_level + 1)
            elif self.set_btn_winlvl_sub.hit_test(pos): SETTINGS.win_level = max(1, SETTINGS.win_level - 1)
            elif self.set_btn_kills.hit_test(pos): SETTINGS.kills_per_level = min(100, SETTINGS.kills_per_level + 5)
            elif self.set_btn_kills_sub.hit_test(pos): SETTINGS.kills_per_level = max(5, SETTINGS.kills_per_level - 5)
            elif self.set_btn_bosshp.hit_test(pos): SETTINGS.boss_hp_per_level = min(200, SETTINGS.boss_hp_per_level + 5)
            elif self.set_btn_bosshp_sub.hit_test(pos): SETTINGS.boss_hp_per_level = max(5, SETTINGS.boss_hp_per_level - 5)
            elif self.set_fullscreen_btn.hit_test(pos): self.set_fullscreen(not self.fullscreen)
            elif self.settings_back.hit_test(pos): self.state = STATE_MENU

        elif self.state in (STATE_PLAYING, STATE_BOSS):
            if self.pause_button.hit_test(pos):
                self.prev_state = self.state
                self.state = STATE_PAUSED

        elif self.state == STATE_PAUSED:
            if self.resume_button.hit_test(pos):
                self.state = getattr(self, "prev_state", STATE_PLAYING)
            elif self.pause_quit_button.hit_test(pos):
                self.state = STATE_MENU

        elif self.state in (STATE_GAMEOVER, STATE_WIN):
            if self.restart_button.hit_test(pos):
                self.full_reset()
                self.state = STATE_LEVEL_INTRO
            elif self.menu_button.hit_test(pos):
                self.state = STATE_MENU

        elif self.state == STATE_ENTER_NAME:
            if self.name_submit_button.hit_test(pos):
                self.submit_name_entry()
            elif self.name_backspace_button.hit_test(pos):
                self.name_entry = self.name_entry[:-1]

        elif self.state == STATE_SKINS:
            if self.skin_player_toggle.hit_test(pos):
                self.skins_editing = 2 if self.skins_editing == 1 else 1
            elif self.skin_left.hit_test(pos):
                if self.skins_editing == 1: self.selected_skin = (self.selected_skin - 1) % len(SKIN_NAMES)
                else: self.selected_skin2 = (self.selected_skin2 - 1) % len(SKIN_NAMES)
            elif self.skin_right.hit_test(pos):
                if self.skins_editing == 1: self.selected_skin = (self.selected_skin + 1) % len(SKIN_NAMES)
                else: self.selected_skin2 = (self.selected_skin2 + 1) % len(SKIN_NAMES)
            elif self.skin_back.hit_test(pos):
                self.state = STATE_MENU

        elif self.state == STATE_LEADERBOARD:
            if self.lb_back.hit_test(pos):
                self.state = STATE_MENU

    def handle_pointer_motion(self, pos, pointer_id):
        if pointer_id in self.active_touches:
            self.active_touches[pointer_id] = pos

    def handle_pointer_up(self, pointer_id):
        self.active_touches.pop(pointer_id, None)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    pos = self.pointer_virtual_pos(event)
                    pid = self.pointer_id(event)
                    self.handle_pointer_down(pos, pid)
                    continue

                if event.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
                    if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                        self.handle_pointer_motion(self.pointer_virtual_pos(event), -1)
                    elif event.type == pygame.FINGERMOTION:
                        self.handle_pointer_motion(self.pointer_virtual_pos(event), self.pointer_id(event))
                    continue

                if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                    self.handle_pointer_up(self.pointer_id(event))
                    continue

                if event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.display = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    continue

                if event.type == pygame.TEXTINPUT and self.state == STATE_ENTER_NAME:
                    if len(self.name_entry) < 12:
                        self.name_entry += event.text
                    continue

                if event.type == pygame.KEYDOWN:
                    if self.state == STATE_ENTER_NAME:
                        if event.key == pygame.K_BACKSPACE:
                            self.name_entry = self.name_entry[:-1]
                        elif event.key == pygame.K_RETURN:
                            self.submit_name_entry()
                        continue

                    if event.key == pygame.K_F11:
                        self.set_fullscreen(not self.fullscreen)

                    if event.key == pygame.K_ESCAPE:
                        if self.state in (STATE_PLAYING, STATE_BOSS):
                            self.prev_state = self.state
                            self.state = STATE_PAUSED
                        elif self.state == STATE_PAUSED:
                            self.state = getattr(self, "prev_state", STATE_PLAYING)
                        elif self.state in (STATE_SKINS, STATE_LEADERBOARD, STATE_SETTINGS):
                            self.state = STATE_MENU
                        elif self.state not in (STATE_MENU,):
                            self.state = STATE_MENU

                    if event.key == pygame.K_t:
                        self.touch_mode = not self.touch_mode

                    if event.key == pygame.K_m:
                        self.music_on = not self.music_on
                        self.music.set_enabled(self.music_on)

                    if event.key == pygame.K_r and self.state in (STATE_GAMEOVER, STATE_WIN):
                        self.full_reset()
                        self.state = STATE_LEVEL_INTRO

            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()