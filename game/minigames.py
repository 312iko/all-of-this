import random
import pygame


class SimonSession:
    """memory (2x2).

    - rounds:  number of rounds to complete (THE JOURNEY has 3, WITHOUT ESCAPE has 5)
    - timing:  timing of flashes and input leniency is adjusted based on difficulty
    """

    PAD_COLORS = [(200, 30, 30), (30, 200, 30), (30, 30, 200), (200, 200, 30)]

    def __init__(self, rounds=3, pad_size=140, spacing=20, lang="en"):
        self.rounds = rounds
        self.pad_size = pad_size
        self.spacing = spacing
        self.lang = lang
        self.pattern = []
        self.current_round = 1
        self._generate_pattern(self.rounds + 1)

        self.showing_sequence = True
        self.seq_index = 0
        self.flash_timer = 0.6
        self.flash_cool = 0.2
        self.accept_input = False
        self.player_input = []
        self.success = False
        self.failed = False

        self._layout_pads()

    def _layout_pads(self):
        # center pads on screen
        w, h = pygame.display.get_surface().get_size()
        total_w = self.pad_size * 2 + self.spacing
        total_h = self.pad_size * 2 + self.spacing
        left = (w - total_w) // 2
        top = (h - total_h) // 2
        self.rects = []
        for row in range(2):
            for col in range(2):
                r = pygame.Rect(
                    left + col * (self.pad_size + self.spacing),
                    top + row * (self.pad_size + self.spacing),
                    self.pad_size,
                    self.pad_size,
                )
                self.rects.append(r)

    def _generate_pattern(self, length):
        for _ in range(length * 2):
            self.pattern.append(random.randrange(0, 4))

    def update(self, dt):
        if self.success or self.failed:
            return
        if self.showing_sequence:
            if self.flash_timer > 0:
                self.flash_timer -= dt
            else:
                # advance
                self.seq_index += 1
                if self.seq_index >= self.current_round:
                    # finished showing this round
                    self.showing_sequence = False
                    self.accept_input = True
                    self.player_input = []
                else:
                    # set next flash
                    self.flash_timer = 0.6
        # nothing else to tick here

    def get_flashing_index(self):
        if not self.showing_sequence:
            return None
        if self.seq_index < len(self.pattern):
            return self.pattern[self.seq_index]
        return None

    def handle_click(self, pos):
        if not self.accept_input or self.success or self.failed:
            return
        for idx, rect in enumerate(self.rects):
            if rect.collidepoint(pos):
                # check expected
                expected = self.pattern[len(self.player_input)]
                if idx != expected:
                    self.failed = True
                    self.accept_input = False
                    return
                self.player_input.append(idx)
                if len(self.player_input) >= self.current_round:
                    # round success
                    if self.current_round >= self.rounds:
                        self.success = True
                        self.accept_input = False
                        return
                    else:
                        self.current_round += 1
                        self.showing_sequence = True
                        self.seq_index = 0
                        self.flash_timer = 0.6
                        self.accept_input = False
                return

    def draw(self, surf):
        font = pygame.font.Font(None, 28)
        small = pygame.font.Font(None, 22)
        en = self.lang == "en"
        # draw pads
        for i, rect in enumerate(self.rects):
            color = self.PAD_COLORS[i]
            pygame.draw.rect(surf, color, rect)
            if self.showing_sequence and self.seq_index < len(self.pattern) and self.pattern[self.seq_index] == i and self.flash_timer > 0.15:
                s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                s.fill((255, 255, 255, 100))
                surf.blit(s, rect.topleft)
        round_txt = font.render(f"Round {self.current_round}/{self.rounds}", True, (230, 230, 230))
        surf.blit(round_txt, (10, 10))
        if self.showing_sequence:
            hint = font.render("Watch the sequence" if en else "Guarda la sequenza", True, (200, 200, 200))
            surf.blit(hint, (10, 40))
        if self.accept_input:
            hint = font.render("Repeat the sequence — click the pads" if en else "Ripeti la sequenza — clicca i riquadri", True, (200, 200, 200))
            surf.blit(hint, (10, 40))
            ctrl = small.render("Mouse to click pads" if en else "Mouse per cliccare i riquadri", True, (160, 160, 160))
            surf.blit(ctrl, (10, 66))
        if self.failed:
            f = font.render("Failed — restarting…" if en else "Fallito — ricomincia…", True, (240, 80, 80))
            surf.blit(f, (10, 70))
        if self.success:
            s = font.render("Completed — restarting…" if en else "Completato — ricomincia…", True, (80, 240, 80))
            surf.blit(s, (10, 70))


class StealthSession:
    """Simple stealth run: avoid moving detectors and reach the end.

    - time_limit: time to cross
    - player: rectangle controlled left/right
    - detectors: rectangles that move horizontally
    """

    def __init__(self, time_limit=6.0, lang="en"):
        self.time_limit = time_limit
        self.time_left = time_limit
        self.lang = lang
        self.w, self.h = pygame.display.get_surface().get_size()
        self.player = pygame.Rect(50, self.h // 2 - 20, 40, 40)
        self.goal_x = self.w - 140
        self.speed = 260
        self.detectors = []
        self._spawn_detectors()
        self.success = False
        self.failed = False

    def _spawn_detectors(self):
        # create a few horizontal moving detectors
        lanes = [self.h // 2 - 80, self.h // 2, self.h // 2 + 80]
        for i, y in enumerate(lanes):
            rect = pygame.Rect(random.randint(200, self.w - 200), y - 10, 120, 20)
            speed = random.choice([-120, 120])
            self.detectors.append({"rect": rect, "speed": speed})

    def update(self, dt):
        if self.success or self.failed:
            return
        keys = pygame.key.get_pressed()
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        self.player.x += int(dx * self.speed * dt)
        # clamp
        if self.player.x < 20:
            self.player.x = 20
        if self.player.x > self.w - self.player.w - 20:
            self.player.x = self.w - self.player.w - 20
        # move detectors
        for d in self.detectors:
            d["rect"].x += int(d["speed"] * dt)
            if d["rect"].right < 0:
                d["rect"].left = self.w
            if d["rect"].left > self.w:
                d["rect"].right = 0
        # collisions
        for d in self.detectors:
            if self.player.colliderect(d["rect"]):
                self.failed = True
                return
        # time
        self.time_left -= dt
        if self.time_left <= 0:
            # success if player reached goal
            if self.player.x >= self.goal_x:
                self.success = True
            else:
                self.failed = True

    def draw(self, surf):
        font = pygame.font.Font(None, 28)
        small = pygame.font.Font(None, 22)
        en = self.lang == "en"
        pygame.draw.rect(surf, (40, 40, 40), (0, self.h // 2 - 140, self.w, 280))
        pygame.draw.rect(surf, (80, 200, 80), (self.goal_x, self.h // 2 - 60, 80, 120))
        pygame.draw.rect(surf, (200, 200, 240), self.player)
        for d in self.detectors:
            pygame.draw.rect(surf, (200, 80, 80), d["rect"])
        t = font.render(f"Time: {int(self.time_left)}s", True, (230, 230, 230))
        surf.blit(t, (10, 10))
        hint = font.render("A/D or ← → to move — reach the green zone" if en else "A/D o ← → per muoverti — raggiungi la zona verde", True, (200, 200, 200))
        surf.blit(hint, (10, 40))
        ctrl = small.render("Avoid red detectors — don't get caught!" if en else "Evita i detector rossi — non farti scoprire!", True, (160, 160, 160))
        surf.blit(ctrl, (10, 66))
        if self.failed:
            f = font.render("Detected! — restarting…" if en else "Scoperto! — ricomincia…", True, (240, 80, 80))
            surf.blit(f, (10, 92))
        if self.success:
            s = font.render("Cleared! — restarting…" if en else "Superato! — ricomincia…", True, (80, 240, 80))
            surf.blit(s, (10, 92))
