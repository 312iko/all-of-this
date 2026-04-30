from __future__ import annotations

import math
import random
import sys
from typing import Any

import pygame

from game.freefall import FreeFallSession, new_session
from game.input_bindings import (
    Action,
    joystick_actions,
    joystick_move_vector,
    keyboard_actions_from_events,
    merge_actions,
)
from game.narrative import apply_choice_effects, get_node, load_story, visible_choices, set_language
from game.puzzles import (
    click_precision_required,
    click_round_duration,
    keypad_max_attempts,
    keypad_solution,
    time_multiplier,
)
from game.routing import freefall_target_units, resolve_finale_entry
from game.save import can_load, load_game, save_game, slot_has_save, slot_path, slot_preview
from game.state import Difficulty, GameState
from game.trophies import all_trophy_dicts, check_story_trophies
from game.ui import draw_text_block
from game.minigames import SimonSession, StealthSession
from game import codex as codex_mod

WIDTH, HEIGHT = 960, 540
FPS = 60

COLOR_BG = (12, 14, 26)
COLOR_TEXT = (228, 230, 242)
COLOR_ACCENT = (130, 210, 255)
COLOR_MUTED = (130, 132, 155)
COLOR_BOX = (32, 36, 58)
COLOR_BOX_EDGE = (78, 92, 140)
COLOR_FLASH_TRUST = (80, 200, 140)
COLOR_FLASH_WARN = (220, 160, 90)
COLOR_CHOICE_HL = (48, 52, 78)
COLOR_CHOICE_HOVER = (56, 62, 92)


def substitute_name(text: str, name: str) -> str:
    return text.replace("[NOME]", name).replace("[NAME]", name)


def draw_panel(
    surf: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
) -> None:
    pygame.draw.rect(surf, fill, rect, border_radius=10)
    pygame.draw.rect(surf, border, rect, width=2, border_radius=10)


def format_time(seconds: float) -> str:
    s = int(max(0, seconds))
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


class GameApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.key.set_repeat(320, 90)
        pygame.joystick.init()
        self.fullscreen = False
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("ALL OF THIS — text adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.font_small = pygame.font.SysFont("consolas", 17)
        self.font_title = pygame.font.SysFont("consolas", 32, bold=True)
        # story will be loaded after language selection
        self.language: str | None = None
        self.story: dict[str, Any] | None = None
        self.joystick: pygame.joystick.Joystick | None = None
        self._init_joystick()

        # force language selection at startup
        self.mode = "language"
        self.lang_index = 0
        self.lang_options = [("Italiano", "it"), ("English", "en")]
        self.menu_index = 0
        self.menu_options: list[str] = []

        self.state = GameState()
        self.name_buffer = ""
        self.choice_index = 0
        self.trophies_unlocked: set[str] = set()
        self.active_slot = 1
        self.slot_pick_index = 0

        self.player_rect = pygame.Rect(WIDTH // 2, HEIGHT // 2 + 40, 18, 18)
        self._fragment_layouts = {
            "default": [
                pygame.Rect(120, 280, 24, 24),
                pygame.Rect(WIDTH // 2, 180, 24, 24),
                pygame.Rect(WIDTH - 160, 320, 24, 24),
            ],
            "echo": [
                pygame.Rect(100, 240, 22, 22),
                pygame.Rect(WIDTH - 130, 260, 22, 22),
                pygame.Rect(WIDTH // 2 - 11, HEIGHT - 210, 22, 22),
            ],
            "vault": [
                pygame.Rect(160, 200, 22, 22),
                pygame.Rect(WIDTH // 2, 300, 22, 22),
                pygame.Rect(WIDTH - 180, 200, 22, 22),
            ],
        }
        self.fragment_slots: list[pygame.Rect] = list(self._fragment_layouts["default"])
        self.fragments_done: set[int] = set()

        self.keypad_buffer = ""
        self.keypad_attempts_left = 2

        self.click_targets: list[pygame.Rect] = []
        self.click_spawn_timer = 0.0
        self.click_hits = 0
        self.click_misses = 0
        self.click_total_spawns = 0
        self.click_time_left = 14.0
        self.click_active = False

        self.ff_session: FreeFallSession | None = None

        self.tw_full: str = ""
        self.tw_shown: str = ""
        self.tw_cps: float = 42.0
        self.tw_accum: float = 0.0
        self.tw_done: bool = True

        self.dialogue_log: list[str] = []
        self.log_scroll: int = 0

        self.feedback_msg: str = ""
        self.feedback_timer: float = 0.0
        self.feedback_color: tuple[int, int, int] = COLOR_ACCENT

        self.flash_overlay: tuple[int, int, int] | None = None
        self.flash_time: float = 0.0

        self.message_line = ""
        self._last_autosave_playtime = 0.0
        self.pause_log_scroll = 0
        self.mouse_pos = (0, 0)
        self._keypad_digit_rects: list[tuple[pygame.Rect, str]] = []
        self._mode_before_quit = "menu"
        self.quit_index = 0
        self._menu_option_rects: list[pygame.Rect] = []
        self._choice_row_rects: list[pygame.Rect] = []
        # allocation UI state (points assigned at game start)
        self.alloc_points: int = 0
        self.alloc_stats: dict[str, int] = {
            "strength": 0,
            "kindness": 0,
            "stubbornness": 0,
        }
        self.alloc_index: int = 0
        self._alloc_rects: list[tuple[pygame.Rect, pygame.Rect]] = []

        # HUD stats chart state
        self._stats_bar_rects: list[tuple[pygame.Rect, str, int]] = []
        # minigame sessions
        self.simon_session: SimonSession | None = None
        self.stealth_session: StealthSession | None = None

        # trophies view scroll
        self.trophies_scroll: int = 0

        # settings / accessibility
        self.crt_enabled: bool = False
        self.text_size_mode: int = 0  # 0=normal, 1=large, 2=extra large
        self.high_contrast: bool = False
        self._settings_index: int = 0
        self._settings_rects: list[pygame.Rect] = []

        # journal / codex (F2)
        self._journal_tab: int = 0  # 0=clues, 1=codex
        self._journal_codex_index: int = 0
        self._journal_codex_scroll: int = 0
        self._journal_clue_rects: list[pygame.Rect] = []
        self._journal_codex_rects: list[pygame.Rect] = []

        # controller rumble
        self._rumble_cooldown: float = 0.0

        # debug: hold '+' for 10s to open debug menu
        self._debug_hold_time: float = 0.0
        self._debug_menu_index: int = 0
        self._minigame_mode: str | None = None
        self._debug_option_rects: list[pygame.Rect] = []

    def _enter_pause(self) -> None:
        self.pause_log_scroll = max(0, len(self.dialogue_log) - 8)
        if self.state.difficulty != Difficulty.WITHOUT_ESCAPE:
            try:
                save_game(self.state, sorted(self.trophies_unlocked), slot=self.active_slot)
            except OSError:
                pass
        self.mode = "pause"

    @property
    def _text_color(self) -> tuple[int, int, int]:
        return (255, 255, 255) if self.high_contrast else COLOR_TEXT

    @property
    def _accent_color(self) -> tuple[int, int, int]:
        return (160, 240, 255) if self.high_contrast else COLOR_ACCENT

    @property
    def _muted_color(self) -> tuple[int, int, int]:
        return (180, 180, 200) if self.high_contrast else COLOR_MUTED

    def _init_joystick(self) -> None:
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

    def _toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            info = pygame.display.Info()
            flags = pygame.FULLSCREEN | pygame.SCALED
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        else:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("ALL OF THIS — text adventure")

    def _maybe_autosave(self) -> None:
        if self.state.difficulty == Difficulty.WITHOUT_ESCAPE:
            return
        pt = self.state.playtime_seconds
        if pt - self._last_autosave_playtime < 90.0:
            return
        self._last_autosave_playtime = pt
        try:
            save_game(self.state, sorted(self.trophies_unlocked), slot=self.active_slot)
        except OSError:
            pass

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    if self.mode == "quit_confirm":
                        pygame.quit()
                        sys.exit(0)
                    self._mode_before_quit = self.mode
                    self.quit_index = 0
                    self.mode = "quit_confirm"
                    continue
                if e.type == pygame.MOUSEMOTION:
                    self.mouse_pos = e.pos
                if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    self._toggle_fullscreen()
                if (
                    e.type == pygame.KEYDOWN
                    and e.key == pygame.K_ESCAPE
                    and self.mode == "play"
                ):
                    self._enter_pause()
                if (
                    e.type == pygame.KEYDOWN
                    and e.key == pygame.K_F2
                    and self.mode == "play"
                ):
                    self._open_journal()

            actions = merge_actions(
                keyboard_actions_from_events(events),
                joystick_actions(self.joystick, events),
            )

            if self.mode == "menu":
                self._update_menu(events, actions)
            elif self.mode == "language":
                self._update_language(events, actions)
            elif self.mode == "slot_pick":
                self._update_slot_pick(events, actions)
            elif self.mode == "name":
                self._update_name(events)
            elif self.mode == "difficulty":
                self._update_difficulty(events, actions)
            elif self.mode == "allocate_stats":
                self._update_allocate_stats(events, actions)
            elif self.mode == "play":
                self.state.playtime_seconds += dt
                self._maybe_autosave()
                self._update_play(events, actions, dt)
                self._update_debug_hold(events, dt)
            elif self.mode == "pause":
                self._update_pause(events, actions)
            elif self.mode == "quit_confirm":
                self._update_quit_confirm(events, actions)
            elif self.mode == "trophies_screen":
                self._update_trophies(events, actions)
            elif self.mode == "settings":
                self._update_settings(events, actions)
            elif self.mode == "journal":
                self._update_journal(events, actions)
            elif self.mode == "debug_menu":
                self._update_debug_menu(events, actions)
            elif self.mode == "debug_minigame":
                self._update_debug_minigame(events, actions, dt)

            self._tick_feedback(dt)
            if self._rumble_cooldown > 0:
                self._rumble_cooldown -= dt
            self._draw()
            pygame.display.flip()

    def _draw_language(self) -> None:
        draw_panel(self.screen, pygame.Rect(80, 40, WIDTH - 160, HEIGHT - 80), (24, 28, 46), COLOR_BOX_EDGE)
        title = self.font_title.render("Scegli lingua / Choose language", True, COLOR_ACCENT)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 70))
        left = WIDTH // 2 - 180
        top = 200
        for i, (label, code) in enumerate(self.lang_options):
            r = pygame.Rect(left, top + i * 48, 360, 40)
            if i == self.lang_index:
                pygame.draw.rect(self.screen, COLOR_CHOICE_HL, r, border_radius=6)
            elif r.collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, COLOR_CHOICE_HOVER, r, border_radius=6)
            else:
                pygame.draw.rect(self.screen, COLOR_BOX, r, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, r, width=1, border_radius=6)
            lab = self.font.render(label, True, COLOR_TEXT)
            self.screen.blit(lab, (r.x + 12, r.y + 6))
        hint = self.font_small.render("Enter / clic per confermare | Enter / click to confirm", True, COLOR_MUTED)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 60))

    def _tick_feedback(self, dt: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
        if self.flash_time > 0:
            self.flash_time -= dt

    def _push_feedback(self, msg: str, color: tuple[int, int, int] = COLOR_ACCENT) -> None:
        self.feedback_msg = msg
        self.feedback_timer = 2.2
        self.feedback_color = color

    def _flash(self, color: tuple[int, int, int]) -> None:
        self.flash_overlay = color
        self.flash_time = 0.18

    def _effect_feedback(self, effects: list[str]) -> None:
        for raw in effects:
            # visual flash for trust changes; detailed numeric feedback moved to HUD chart
            if raw.startswith("trust_"):
                if "+" in raw:
                    self._flash(COLOR_FLASH_TRUST)
                elif "-" in raw:
                    self._flash(COLOR_FLASH_WARN)
                continue
            elif "corruption" in raw:
                self._push_feedback("Corruption +" if self.language == "en" else "Corruzione +", COLOR_FLASH_WARN)
                self._flash(COLOR_FLASH_WARN)
            elif raw.startswith("clue:"):
                self._push_feedback("Clue obtained" if self.language == "en" else "Indizio raccolto", COLOR_ACCENT)
            elif raw.startswith("set:ignored_shadows"):
                self._push_feedback("You ignored a signal…" if self.language == "en" else "Hai ignorato un segnale…", COLOR_MUTED)
            elif "trust_mirei+" in raw or "trust_kenji+" in raw:
                self._push_feedback("Narrative bond +" if self.language == "en" else "Legame narrativo +", COLOR_FLASH_TRUST)
            elif "trust_mirei-" in raw or "trust_kenji-" in raw:
                self._push_feedback("Narrative bond −" if self.language == "en" else "Legame narrativo −", COLOR_FLASH_WARN)
                self._flash(COLOR_FLASH_WARN)

    def _append_log(self, text: str) -> None:
        t = text.strip()
        if not t:
            return
        self.dialogue_log.append(t)
        if len(self.dialogue_log) > 120:
            self.dialogue_log = self.dialogue_log[-120:]

    def _reset_typewriter(self, full: str) -> None:
        self.tw_full = full
        self.tw_shown = ""
        self.tw_accum = 0.0
        self.tw_done = not full.strip()

    def _update_typewriter(self, dt: float) -> None:
        if self.tw_done or not self.tw_full:
            return
        self.tw_accum += dt * self.tw_cps
        while self.tw_accum >= 1.0 and len(self.tw_shown) < len(self.tw_full):
            self.tw_shown += self.tw_full[len(self.tw_shown)]
            self.tw_accum -= 1.0
        if len(self.tw_shown) >= len(self.tw_full):
            self.tw_done = True

    def _skip_typewriter(self) -> None:
        self.tw_shown = self.tw_full
        self.tw_done = True

    def _update_menu(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        cx = WIDTH // 2
        for i, _opt in enumerate(self.menu_options):
            r = pygame.Rect(cx - 200, 192 + i * 38, 400, 34)
            if i < len(self._menu_option_rects):
                self._menu_option_rects[i] = r
            else:
                self._menu_option_rects.append(r)
        mx, my = self.mouse_pos
        for i, r in enumerate(self._menu_option_rects[: len(self.menu_options)]):
            if r.collidepoint(mx, my):
                self.menu_index = i
                break

        if Action.CONFIRM in actions:
            opt = self.menu_options[self.menu_index]
            if opt in ("Nuova partita", "New Game"):
                self.mode = "name"
                self.name_buffer = ""
            elif opt in ("Carica partita", "Load Game"):
                self.mode = "slot_pick"
                self.slot_pick_index = 0
            elif opt in ("Trofei", "Trophies"):
                self.mode = "trophies_screen"
            elif opt in ("Impostazioni", "Settings"):
                self._settings_index = 0
                self.mode = "settings"
            elif opt in ("Esci", "Quit"):
                self._mode_before_quit = "menu"
                self.quit_index = 0
                self.mode = "quit_confirm"
        if Action.UP in actions:
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        if Action.DOWN in actions:
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(self._menu_option_rects[: len(self.menu_options)]):
                    if r.collidepoint(e.pos):
                        self.menu_index = i
                        opt = self.menu_options[i]
                        if opt in ("Nuova partita", "New Game"):
                            self.mode = "name"
                            self.name_buffer = ""
                        elif opt in ("Carica partita", "Load Game"):
                            self.mode = "slot_pick"
                            self.slot_pick_index = 0
                        elif opt in ("Trofei", "Trophies"):
                            self.mode = "trophies_screen"
                        elif opt in ("Impostazioni", "Settings"):
                            self._settings_index = 0
                            self.mode = "settings"
                        elif opt in ("Esci", "Quit"):
                            self._mode_before_quit = "menu"
                            self.quit_index = 0
                            self.mode = "quit_confirm"
                        break
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F5:
                self._try_save()

    def _update_slot_pick(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        slot_rects = [pygame.Rect(110, 172 + i * 44, WIDTH - 220, 40) for i in range(3)]
        mx, my = self.mouse_pos
        for i, r in enumerate(slot_rects):
            if r.collidepoint(mx, my):
                self.slot_pick_index = i
                break

        if Action.LEFT in actions:
            self.slot_pick_index = (self.slot_pick_index - 1) % 3
        if Action.RIGHT in actions:
            self.slot_pick_index = (self.slot_pick_index + 1) % 3
        if Action.CONFIRM in actions:
            self._try_load_slot(self.slot_pick_index + 1)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(slot_rects):
                    if r.collidepoint(e.pos):
                        self.slot_pick_index = i
                        self._try_load_slot(i + 1)
                        break

        if Action.CANCEL in actions:
            self.mode = "menu"

    def _try_load_slot(self, slot: int) -> None:
        loaded = load_game(slot=slot)
        if not loaded:
            self.message_line = f"Slot {slot} empty." if self.language == "en" else f"Slot {slot} vuoto."
            return
        st, tro = loaded
        if not can_load(st):
            self.message_line = "WITHOUT ESCAPE: load disabled." if self.language == "en" else "WITHOUT ESCAPE: caricamento disabilitato."
            return
        # restore language from save and load corresponding story
        self.state = st
        self.language = getattr(self.state, "language", "it")
        set_language(self.language)
        try:
            self.story = load_story(self.language)
        except Exception:
            self.story = load_story()
        self.trophies_unlocked = set(tro)
        self.active_slot = slot
        self._last_autosave_playtime = self.state.playtime_seconds
        self.dialogue_log.clear()
        self.mode = "play"
        self.choice_index = 0
        self._on_enter_node(self.state.current_node)
        self.message_line = ""

    def _update_pause(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        vis = 8
        max_scroll = max(0, len(self.dialogue_log) - vis)
        for e in events:
            if e.type == pygame.MOUSEWHEEL:
                self.pause_log_scroll = int(
                    max(0, min(max_scroll, self.pause_log_scroll - e.y))
                )
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_PAGEUP:
                    self.pause_log_scroll = max(0, self.pause_log_scroll - vis)
                elif e.key == pygame.K_PAGEDOWN:
                    self.pause_log_scroll = min(max_scroll, self.pause_log_scroll + vis)
        if Action.UP in actions:
            self.pause_log_scroll = max(0, self.pause_log_scroll - 1)
        if Action.DOWN in actions:
            self.pause_log_scroll = min(max_scroll, self.pause_log_scroll + 1)

        if Action.LEFT in actions:
            self.active_slot = 3 if self.active_slot == 1 else self.active_slot - 1
        if Action.RIGHT in actions:
            self.active_slot = 1 if self.active_slot == 3 else self.active_slot + 1
        if Action.CONFIRM in actions or Action.CANCEL in actions:
            self.mode = "play"
        if Action.PAUSE in actions:
            self.mode = "play"

    def _update_quit_confirm(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        no_rect = pygame.Rect(WIDTH // 2 - 160, 320, 150, 40)
        yes_rect = pygame.Rect(WIDTH // 2 + 10, 320, 150, 40)
        mx, my = self.mouse_pos
        if no_rect.collidepoint(mx, my):
            self.quit_index = 0
        if yes_rect.collidepoint(mx, my):
            self.quit_index = 1

        if Action.LEFT in actions:
            self.quit_index = 0
        if Action.RIGHT in actions:
            self.quit_index = 1
        if Action.CANCEL in actions:
            self.mode = self._mode_before_quit
        if Action.CONFIRM in actions:
            if self.quit_index == 1:
                pygame.quit()
                sys.exit(0)
            self.mode = self._mode_before_quit

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if no_rect.collidepoint(e.pos):
                    self.mode = self._mode_before_quit
                elif yes_rect.collidepoint(e.pos):
                    pygame.quit()
                    sys.exit(0)

    def _update_name(self, events: list[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.mode = "menu"
                elif e.key == pygame.K_BACKSPACE:
                    self.name_buffer = self.name_buffer[:-1]
                elif e.key == pygame.K_RETURN:
                    name = (self.name_buffer.strip() or "PLAYER")[:24]
                    lang = self.language or "it"
                    self.state = GameState(player_name=name, language=lang)
                    self.menu_index = 0
                    self.mode = "difficulty"
                elif e.unicode and e.unicode.isprintable() and len(self.name_buffer) < 24:
                    self.name_buffer += e.unicode

    def _update_difficulty(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        opt_rects = [
            pygame.Rect(70, 252, WIDTH - 140, 38),
            pygame.Rect(70, 292, WIDTH - 140, 38),
        ]
        mx, my = self.mouse_pos
        for i, r in enumerate(opt_rects):
            if r.collidepoint(mx, my):
                self.menu_index = i
                break

        if Action.UP in actions or Action.LEFT in actions:
            self.menu_index = 0
        if Action.DOWN in actions or Action.RIGHT in actions:
            self.menu_index = 1
        if Action.CONFIRM in actions:
            self._start_new_game_after_difficulty()

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(opt_rects):
                    if r.collidepoint(e.pos):
                        self.menu_index = i
                        self._start_new_game_after_difficulty()
                        break

    def _update_language(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        mx, my = self.mouse_pos
        # navigation
        if Action.UP in actions:
            self.lang_index = (self.lang_index - 1) % len(self.lang_options)
        if Action.DOWN in actions:
            self.lang_index = (self.lang_index + 1) % len(self.lang_options)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # detect click on options
                left = WIDTH // 2 - 180
                top = 200
                for i, (_label, _code) in enumerate(self.lang_options):
                    r = pygame.Rect(left, top + i * 48, 360, 40)
                    if r.collidepoint(e.pos):
                        self.lang_index = i
                        # confirm selection
                        self.language = self.lang_options[self.lang_index][1]
                        set_language(self.language)
                        try:
                            self.story = load_story(self.language)
                        except Exception:
                            self.story = load_story()
                        # set localized menu options
                        if self.language == "en":
                            self.menu_options = ["New Game", "Load Game", "Settings", "Trophies", "Quit"]
                        else:
                            self.menu_options = ["Nuova partita", "Carica partita", "Impostazioni", "Trofei", "Esci"]
                        self.mode = "menu"
                        break
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                self.language = self.lang_options[self.lang_index][1]
                set_language(self.language)
                try:
                    self.story = load_story(self.language)
                except Exception:
                    self.story = load_story()
                if self.language == "en":
                    self.menu_options = ["New Game", "Load Game", "Settings", "Trophies", "Quit"]
                else:
                    self.menu_options = ["Nuova partita", "Carica partita", "Impostazioni", "Trofei", "Esci"]
                self.mode = "menu"

    def _start_new_game_after_difficulty(self) -> None:
        # prepare initial game state, then enter stat-allocation screen
        self.state.difficulty = Difficulty.THE_JOURNEY if self.menu_index == 0 else Difficulty.WITHOUT_ESCAPE
        self.state.current_node = "intro_letter"
        self.state.playtime_seconds = 0.0
        self._last_autosave_playtime = 0.0
        self.choice_index = 0
        self.dialogue_log.clear()
        # initialize allocation points (easier difficulty grants more points)
        self.alloc_points = 4 if self.state.difficulty == Difficulty.THE_JOURNEY else 2
        self.alloc_stats = {"strength": 0, "kindness": 0, "stubbornness": 0}
        self.alloc_index = 0
        self._alloc_rects = []
        self.mode = "allocate_stats"
        self.menu_index = 0

    def _update_allocate_stats(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        stats_keys = ["strength", "kindness", "stubbornness"]
        mx, my = self.mouse_pos

        # keyboard / joystick navigation
        if Action.UP in actions:
            self.alloc_index = (self.alloc_index - 1) % len(stats_keys)
        if Action.DOWN in actions:
            self.alloc_index = (self.alloc_index + 1) % len(stats_keys)
        if Action.RIGHT in actions:
            key = stats_keys[self.alloc_index]
            if self.alloc_points > 0:
                self.alloc_stats[key] += 1
                self.alloc_points -= 1
        if Action.LEFT in actions:
            key = stats_keys[self.alloc_index]
            if self.alloc_stats[key] > 0:
                self.alloc_stats[key] -= 1
                self.alloc_points += 1

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # click +/- buttons
                for i, (minus_rect, plus_rect) in enumerate(self._alloc_rects):
                    if plus_rect.collidepoint(e.pos):
                        if self.alloc_points > 0:
                            k = stats_keys[i]
                            self.alloc_stats[k] += 1
                            self.alloc_points -= 1
                        break
                    if minus_rect.collidepoint(e.pos):
                        k = stats_keys[i]
                        if self.alloc_stats[k] > 0:
                            self.alloc_stats[k] -= 1
                            self.alloc_points += 1
                        break

        # finalize allocation
        if Action.CONFIRM in actions:
            if self.alloc_points <= 0:
                # commit to game state (these are the general stats, not trust)
                self.state.strength = int(self.alloc_stats.get("strength", 0))
                self.state.kindness = int(self.alloc_stats.get("kindness", 0))
                self.state.stubbornness = int(self.alloc_stats.get("stubbornness", 0))
                self.state.flags["allocated_stats"] = True
                # now start the game node
                self._on_enter_node(self.state.current_node)
                self.mode = "play"
                return
            else:
                # hint message until points spent
                if self.language == "en":
                    self.message_line = f"Spend all points before continuing ({self.alloc_points} remaining)."
                else:
                    self.message_line = f"Assegna tutti i punti prima di continuare ({self.alloc_points} rimanenti)."

    def _update_trophies(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        # scrolling support: mouse wheel and up/down
        # pass current game language so trophies are localized
        data = all_trophy_dicts(self.trophies_unlocked, getattr(self.state, "language", "it"))
        vis = max(6, (HEIGHT - 140) // 26)
        max_scroll = max(0, len(data) - vis)
        for e in events:
            if e.type == pygame.MOUSEWHEEL:
                self.trophies_scroll = int(max(0, min(max_scroll, self.trophies_scroll - e.y)))
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_PAGEUP:
                    self.trophies_scroll = max(0, self.trophies_scroll - vis)
                elif e.key == pygame.K_PAGEDOWN:
                    self.trophies_scroll = min(max_scroll, self.trophies_scroll + vis)

        if Action.UP in actions:
            self.trophies_scroll = max(0, self.trophies_scroll - 1)
        if Action.DOWN in actions:
            self.trophies_scroll = min(max_scroll, self.trophies_scroll + 1)

        if Action.CANCEL in actions or Action.CONFIRM in actions:
            self.mode = "menu"

    def _on_enter_node(self, node_id: str | None = None) -> None:
        nid = node_id if node_id is not None else self.state.current_node

        if nid == "after_vision":
            nid = "sentiero_group" if self.state.group_mode else "sentiero_solo"
        if nid == "act5_resolve":
            nid = resolve_finale_entry(self.state)

        self.state.current_node = nid
        node = get_node(self.story, self.state.current_node)

        new_t = check_story_trophies(self.state, self.state.current_node, self.trophies_unlocked)
        for t in new_t:
            self.trophies_unlocked.add(t)
            self._rumble(strength=0.4, duration_ms=300)

        if not node.get("kind"):
            txt = substitute_name(node.get("text", ""), self.state.player_name)
            self._append_log(txt)
            self._reset_typewriter(txt)

        if node.get("kind") == "fragment_hunt":
            self.fragments_done = set()
            layout_key = node.get("fragment_layout", "default")
            self.fragment_slots = [
                r.copy() for r in self._fragment_layouts.get(layout_key, self._fragment_layouts["default"])
            ]
            self.player_rect.center = (WIDTH // 2, HEIGHT // 2 + 60)
            self.tw_done = True
        if node.get("kind") == "keypad":
            self.keypad_buffer = ""
            self.keypad_attempts_left = keypad_max_attempts(self.state)
            self.tw_done = True
        if node.get("kind") == "click_sequence":
            self._reset_click_game()
            self.tw_done = True
        if node.get("kind") == "freefall":
            self.ff_session = new_session(self.state, freefall_target_units(self.state))
            self.tw_done = True
        if node.get("kind") == "simon":
            # rounds configurable in node (default 3)
            rounds = int(node.get("rounds", 3))
            self.simon_session = SimonSession(rounds=rounds, lang=self.language or "en")
            self.tw_done = True
        if node.get("kind") == "stealth":
            self.stealth_session = StealthSession(time_limit=float(node.get("time_limit", 6.0)), lang=self.language or "en")
            self.tw_done = True

    def _reset_click_game(self) -> None:
        self.click_targets = []
        self.click_spawn_timer = 0.0
        self.click_hits = 0
        self.click_misses = 0
        self.click_total_spawns = 0
        self.click_time_left = click_round_duration(self.state)
        self.click_active = True

    def _freefall_resolve(self, win: bool) -> None:
        node = get_node(self.story, self.state.current_node)
        variant = node.get("variant")
        self.ff_session = None
        if win:
            self._rumble(strength=0.6, duration_ms=400)
            if variant == "a":
                nxt = "finale_lost_with_them" if self.state.group_mode else "finale_astral_prison"
            elif variant == "b":
                nxt = "finale_true_distortion" if self.state.corruption >= 1 else "finale_escape"
            else:
                nxt = "finale_escape"
            self.state.current_node = nxt
        else:
            self._rumble(strength=0.8, duration_ms=500)
            self.state.current_node = node.get("next_fail", "finale_freefall_contain")
        self.choice_index = 0
        self._on_enter_node(self.state.current_node)

    def _update_play(self, events: list[pygame.event.Event], actions: set[Action], dt: float) -> None:
        node = get_node(self.story, self.state.current_node)
        kind = node.get("kind")

        if kind == "fragment_hunt":
            self._update_fragments(events, actions, dt)
            return
        if kind == "keypad":
            self._update_keypad(events, actions)
            return
        if kind == "click_sequence":
            self._update_click(events, actions, dt)
            return
        if kind == "freefall" and self.ff_session:
            self._update_freefall(events, actions, dt)
            return

        if kind == "simon":
            # handle Simon/Memory minigame
            if not self.simon_session:
                self.simon_session = SimonSession(rounds=int(get_node(self.story, self.state.current_node).get("rounds", 3)), lang=self.language or "en")
            # process input
            for e in events:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.simon_session.handle_click(e.pos)
            self.simon_session.update(dt)
            if self.simon_session.success or self.simon_session.failed:
                node = get_node(self.story, self.state.current_node)
                if self.simon_session.success:
                    self._rumble(strength=0.5, duration_ms=300)
                    # generic flag and node-specific flags
                    self.state.flags["simon_won"] = True
                    if self.state.current_node == "kenji_archive_minigame":
                        self.state.flags["kenji_subplot_done"] = True
                    if self.state.current_node == "mirei_archive_minigame":
                        self.state.flags["mirei_archive_done"] = True
                    self.state.current_node = node.get("next_success", "after_custodi_escape")
                else:
                    self._rumble(strength=0.7, duration_ms=400)
                    self.state.current_node = node.get("next_fail", "branch_captured")
                self.simon_session = None
                self.choice_index = 0
                self._on_enter_node(self.state.current_node)
            return

        if kind == "stealth":
            # handle stealth corridor
            if not self.stealth_session:
                self.stealth_session = StealthSession(time_limit=float(get_node(self.story, self.state.current_node).get("time_limit", 6.0)), lang=self.language or "en")
            self.stealth_session.update(dt)
            for e in events:
                # allow mouse to restart? (not used)
                pass
            if self.stealth_session.success or self.stealth_session.failed:
                node = get_node(self.story, self.state.current_node)
                if self.stealth_session.success:
                    self._rumble(strength=0.5, duration_ms=300)
                    self.state.flags["stealth_won"] = True
                    # map node-specific
                    if self.state.current_node == "hospital_stealth":
                        self.state.flags["hospital_helped"] = True
                    self.state.current_node = node.get("next_success", "act2_corridor")
                else:
                    self._rumble(strength=0.7, duration_ms=400)
                    self.state.current_node = node.get("next_fail", "game_over_door")
                self.stealth_session = None
                self.choice_index = 0
                self._on_enter_node(self.state.current_node)
            return

        self._update_typewriter(dt)

        choices = visible_choices(self.state, node)
        ready = self.tw_done

        if Action.CONFIRM in actions and not ready:
            self._skip_typewriter()
            return

        if not choices:
            if Action.PAUSE in actions:
                self._enter_pause()
            for e in events:
                if e.type == pygame.KEYDOWN and e.key == pygame.K_F5:
                    self._try_save()
            return

        if not ready:
            if Action.PAUSE in actions:
                self._enter_pause()
            for e in events:
                if e.type == pygame.KEYDOWN and e.key == pygame.K_F5:
                    self._try_save()
                    self.message_line = (
                        f"Saved (slot {self.active_slot})." if self.language == "en" else f"Salvato (slot {self.active_slot})."
                    )
            return

        y0 = HEIGHT - 148
        self._choice_row_rects = []
        mx, my = self.mouse_pos
        for i, _ch in enumerate(choices):
            r = pygame.Rect(48, y0 + i * 28, WIDTH - 96, 26)
            self._choice_row_rects.append(r)
            if r.collidepoint(mx, my):
                self.choice_index = i

        if Action.UP in actions:
            self.choice_index = (self.choice_index - 1) % len(choices)
        if Action.DOWN in actions:
            self.choice_index = (self.choice_index + 1) % len(choices)

        def _apply_choice(ch: dict[str, Any]) -> bool:
            eff = ch.get("effects") or []
            if isinstance(eff, str):
                eff = [eff]
            apply_choice_effects(self.state, ch)
            self._effect_feedback(list(eff))
            nxt = ch.get("next")
            if nxt == "__menu__":
                self.mode = "menu"
                return True
            self.state.current_node = nxt
            self.choice_index = 0
            self._on_enter_node(self.state.current_node)
            return False

        if Action.CONFIRM in actions:
            if _apply_choice(choices[self.choice_index]):
                return

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(self._choice_row_rects):
                    if r.collidepoint(e.pos) and i < len(choices):
                        self.choice_index = i
                        if _apply_choice(choices[i]):
                            return
                        break
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F5:
                self._try_save()
        if Action.PAUSE in actions:
            self._enter_pause()

    def _update_freefall(self, events: list[pygame.event.Event], actions: set[Action], dt: float) -> None:
        if not self.ff_session:
            return
        keys = pygame.key.get_pressed()
        ml = 1.0 if keys[pygame.K_LEFT] or Action.LEFT in actions else 0.0
        mr = 1.0 if keys[pygame.K_RIGHT] or Action.RIGHT in actions else 0.0
        jx, _ = joystick_move_vector(self.joystick)
        if abs(jx) > 0.2:
            if jx < 0:
                ml = abs(jx)
            else:
                mr = abs(jx)
        res = self.ff_session.update(dt, ml, mr, WIDTH)
        if res == "win":
            self._freefall_resolve(True)
        elif res == "lose":
            self._freefall_resolve(False)

    def _update_fragments(self, events: list[pygame.event.Event], actions: set[Action], dt: float) -> None:
        spd = 220 * dt
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or Action.LEFT in actions:
            self.player_rect.x -= int(spd)
        if keys[pygame.K_RIGHT] or Action.RIGHT in actions:
            self.player_rect.x += int(spd)
        if keys[pygame.K_UP] or Action.UP in actions:
            self.player_rect.y -= int(spd)
        if keys[pygame.K_DOWN] or Action.DOWN in actions:
            self.player_rect.y += int(spd)
        jx, jy = joystick_move_vector(self.joystick)
        dead = 0.35
        if abs(jx) > dead or abs(jy) > dead:
            self.player_rect.x += int(jx * spd * 1.2)
            self.player_rect.y += int(jy * spd * 1.2)

        self.player_rect.clamp_ip(pygame.Rect(60, 200, WIDTH - 120, HEIGHT - 260))

        for i, fr in enumerate(self.fragment_slots):
            if i not in self.fragments_done and self.player_rect.colliderect(fr):
                self.fragments_done.add(i)
                self._rumble(strength=0.3, duration_ms=150)

        if len(self.fragments_done) >= 3:
            node = get_node(self.story, self.state.current_node)
            nxt = node.get("next_after", "vision_fragment")
            mode = node.get("fragment_mode", "memory")
            if mode == "echo":
                self.state.flags["echo_hunt_complete"] = True
            else:
                self.state.fragments_collected = 3
            self.state.current_node = nxt
            self.choice_index = 0
            self._on_enter_node(self.state.current_node)

        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F5:
                self._try_save()

    def _keypad_button_layout(self) -> list[tuple[pygame.Rect, str]]:
        cell, gap = 46, 7
        left = WIDTH // 2 - (cell * 3 + gap * 2) // 2
        top = 318
        rows = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["bk", "0", "ok"],
        ]
        out: list[tuple[pygame.Rect, str]] = []
        for ri, row in enumerate(rows):
            for ci, key in enumerate(row):
                x = left + ci * (cell + gap)
                y = top + ri * (cell + gap)
                out.append((pygame.Rect(x, y, cell, cell), key))
        return out

    def _update_keypad(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.unicode.isdigit() and len(self.keypad_buffer) < 12:
                    self.keypad_buffer += e.unicode
                elif e.key == pygame.K_BACKSPACE:
                    self.keypad_buffer = self.keypad_buffer[:-1]
                elif e.key == pygame.K_RETURN:
                    self._submit_keypad()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for rect, key in self._keypad_button_layout():
                    if not rect.collidepoint(e.pos):
                        continue
                    if key.isdigit() and len(self.keypad_buffer) < 12:
                        self.keypad_buffer += key
                    elif key == "bk":
                        self.keypad_buffer = self.keypad_buffer[:-1]
                    elif key == "ok":
                        self._submit_keypad()
                    break

        if Action.CANCEL in actions:
            self.keypad_buffer = ""

    def _submit_keypad(self) -> None:
        node = get_node(self.story, self.state.current_node)
        override = node.get("keypad_answer")
        sol = str(override) if override is not None else keypad_solution(self.state)
        if self.keypad_buffer == sol:
            self.state.current_node = node.get("next_success", "institute_room")
            self.choice_index = 0
            self._on_enter_node(self.state.current_node)
            return
        self.keypad_attempts_left -= 1
        self.keypad_buffer = ""
        if self.keypad_attempts_left <= 0:
            self.state.current_node = node.get("next_fail", "game_over_door")
            self.choice_index = 0
            self._on_enter_node(self.state.current_node)

    def _update_click(self, events: list[pygame.event.Event], actions: set[Action], dt: float) -> None:
        mult = time_multiplier(self.state)
        self.click_time_left -= dt
        self.click_spawn_timer -= dt

        if self.click_active and self.click_spawn_timer <= 0:
            w, h = 56, 56
            self.click_targets.append(
                pygame.Rect(
                    random.randint(100, WIDTH - 100 - w),
                    random.randint(140, HEIGHT - 120 - h),
                    w,
                    h,
                )
            )
            self.click_total_spawns += 1
            base = 0.52 * mult
            self.click_spawn_timer = max(0.22, base)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = e.pos
                hit_any = False
                for r in self.click_targets[:]:
                    if r.collidepoint(pos):
                        hit_any = True
                        self.click_hits += 1
                        self.click_targets.remove(r)
                if not hit_any and self.click_targets:
                    self.click_misses += 1

        if Action.CONFIRM in actions and self.click_targets:
            r = self.click_targets[0]
            self.click_hits += 1
            self.click_targets.remove(r)

        total = self.click_hits + self.click_misses
        prec = (self.click_hits / total) if total > 0 else 1.0

        node = get_node(self.story, self.state.current_node)
        need = click_precision_required(self.state)

        if self.click_time_left <= 0 or total >= 44:
            self.click_active = False
            if total == 0:
                prec = 0.0
            if prec >= need:
                self.state.flags["click_minigame_won"] = True
                self.state.current_node = node.get("next_success", "after_custodi_escape")
            else:
                self.state.current_node = node.get("next_fail", "branch_captured")
            self.choice_index = 0
            self._on_enter_node(self.state.current_node)

    def _draw(self) -> None:
        self.screen.fill(COLOR_BG)
        if self.mode == "language":
            self._draw_language()
        elif self.mode == "menu":
            self._draw_menu()
        elif self.mode == "quit_confirm":
            self._draw_quit_confirm()
        elif self.mode == "slot_pick":
            self._draw_slot_pick()
        elif self.mode == "name":
            self._draw_name()
        elif self.mode == "difficulty":
            self._draw_difficulty()
        elif self.mode == "allocate_stats":
            self._draw_allocate_stats()
        elif self.mode == "play":
            self._draw_play()
        elif self.mode == "pause":
            self._draw_play()
            self._draw_pause_overlay()
        elif self.mode == "trophies_screen":
            self._draw_trophies()
        elif self.mode == "settings":
            self._draw_settings()
        elif self.mode == "journal":
            self._draw_journal()
        elif self.mode == "debug_menu":
            self._draw_debug_menu()
        elif self.mode == "debug_minigame":
            self._draw_debug_minigame()

        # draw persistent stats chart when in play/pause
        if self.mode in ("play", "pause"):
            self._draw_stats_chart()
        if self.mode == "play":
            self._draw_debug_hold_indicator()

        if self.flash_time > 0 and self.flash_overlay:
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            s.fill((*self.flash_overlay, 55))
            self.screen.blit(s, (0, 0))

        if self.crt_enabled:
            self._draw_crt_overlay()

    def _draw_pause_overlay(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 20, 210))
        self.screen.blit(overlay, (0, 0))
        draw_panel(self.screen, pygame.Rect(120, 60, WIDTH - 240, HEIGHT - 120), (26, 30, 48), COLOR_BOX_EDGE)
        title_text = "Pause" if self.language == "en" else "Pausa"
        title = self.font_title.render(title_text, True, COLOR_ACCENT)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        st = self.state
        can_save = st.difficulty != Difficulty.WITHOUT_ESCAPE
        if self.language == "en":
            save_info = f"Active slot: {self.active_slot} (←/→)" if can_save else f"Active slot: {self.active_slot} — NO SAVE (Without Escape)"
            lines = [
                f"Act: {st.act}",
                f"Stats Str/Kin/Stb: {st.strength} / {st.kindness} / {st.stubbornness}",
                f"Trust Ev/Art/Mi/Ke: {st.trust_evelyn} / {st.trust_artemis} / {st.trust_mirei} / {st.trust_kenji}",
                f"Corruption: {st.corruption}   Tension: {st.tension}",
                f"Fragments collected: {st.fragments_collected}",
                f"Clues: {', '.join(st.clues) if st.clues else '—'}",
                save_info,
                "F2: Journal  ·  Enter / Esc: resume",
            ]
        else:
            save_info = f"Slot attivo: {self.active_slot} (frecce sx/dx)" if can_save else f"Slot attivo: {self.active_slot} — NO SAVE (Without Escape)"
            lines = [
                f"Atto: {st.act}",
                f"Statistiche For/Gen/Cap: {st.strength} / {st.kindness} / {st.stubbornness}",
                f"Fiducia Ev/Art/Mi/Ke: {st.trust_evelyn} / {st.trust_artemis} / {st.trust_mirei} / {st.trust_kenji}",
                f"Corruzione: {st.corruption}   Tensione: {st.tension}",
                f"Frammenti raccolti: {st.fragments_collected}",
                f"Indizi: {', '.join(st.clues) if st.clues else '—'}",
                save_info,
                "F2: Quaderno  ·  Invio / Esc: riprendi",
            ]
        y = 130
        for line in lines:
            self.screen.blit(self.font_small.render(line, True, COLOR_TEXT), (150, y))
            y += 26

        y = 280
        vis = 8
        max_scroll = max(0, len(self.dialogue_log) - vis)
        self.screen.blit(
            self.font_small.render(
                (f"Log (mouse wheel / PgUp PgDn) — {len(self.dialogue_log)} lines" if self.language == "en" else f"Registro (rotella mouse / Pag ↑↓) — {len(self.dialogue_log)} righe"),
                True,
                COLOR_ACCENT,
            ),
            (150, y),
        )
        y += 26
        start = max(0, min(self.pause_log_scroll, max_scroll))
        tail = self.dialogue_log[start : start + vis]
        for row in tail:
            self.screen.blit(self.font_small.render(row[:85], True, COLOR_MUTED), (150, y))
            y += 22

    def _draw_menu(self) -> None:
        draw_panel(self.screen, pygame.Rect(80, 40, WIDTH - 160, HEIGHT - 80), (24, 28, 46), COLOR_BOX_EDGE)
        t = self.font_title.render("ALL OF THIS", True, COLOR_ACCENT)
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 70))
        sub_text = "Astral plane — text adventure" if self.language == "en" else "Piano astrale — avventura testuale"
        sub = self.font_small.render(sub_text, True, COLOR_MUTED)
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 112))
        for i, opt in enumerate(self.menu_options):
            col = COLOR_ACCENT if i == self.menu_index else COLOR_TEXT
            if i < len(self._menu_option_rects) and self._menu_option_rects[i].collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, COLOR_CHOICE_HOVER, self._menu_option_rects[i], border_radius=6)
            label = self.font.render(opt, True, col)
            self.screen.blit(label, (WIDTH // 2 - label.get_width() // 2, 200 + i * 38))
        if self.message_line:
            m = self.font_small.render(self.message_line, True, (255, 140, 140))
            self.screen.blit(m, (WIDTH // 2 - m.get_width() // 2, HEIGHT - 90))

    def _draw_slot_pick(self) -> None:
        title = "Load Game" if self.language == "en" else "Carica partita"
        self.screen.blit(self.font_title.render(title, True, COLOR_ACCENT), (WIDTH // 2 - 120, 80))
        for i in range(3):
            r = pygame.Rect(110, 172 + i * 44, WIDTH - 220, 40)
            if r.collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, COLOR_CHOICE_HOVER, r, border_radius=6)
            slot = i + 1
            has = slot_has_save(slot)
            prev = slot_preview(slot) or ("(empty)" if self.language == "en" else "(vuoto)")
            col = COLOR_ACCENT if i == self.slot_pick_index else COLOR_TEXT
            line = f"Slot {slot}: {prev}"
            if not has:
                line = f"Slot {slot}: {('(empty)' if self.language == 'en' else '(vuoto)')}"
            self.screen.blit(self.font.render(line[:80], True, col), (120, 180 + i * 44))
        slot_hint = (
            "Enter / click: load — Esc: back — F11 fullscreen" if self.language == "en" else "Invio / clic: carica — Esc: indietro — F11 schermo intero"
        )
        self.screen.blit(self.font_small.render(slot_hint, True, COLOR_MUTED), (120, HEIGHT - 60))
    # scrivere il nome 
    def _draw_name(self) -> None:
        prompt = (
            "Your name (Enter to confirm, Esc to menu):"
            if self.language == "en"
            else "Il tuo nome (Invio per conferma, Esc per menu):"
        )
        draw_text_block(
            self.screen,
            prompt,
            self.font,
            COLOR_TEXT,
            pygame.Rect(40, 80, WIDTH - 80, 120),
        )
        buf = self.font.render(self.name_buffer + "_", True, COLOR_ACCENT)
        self.screen.blit(buf, (40, 200))

    def _draw_difficulty(self) -> None:
        if self.language == "en":
            draw_text_block(
                self.screen,
                "Choose difficulty:\nTHE JOURNEY — standard experience.\nTHE JOURNEY... WITHOUT ESCAPE — harder; no reload save.",
                self.font_small,
                COLOR_TEXT,
                pygame.Rect(40, 40, WIDTH - 80, 200),
            )
            opts = ["THE JOURNEY", "THE JOURNEY... WITHOUT ESCAPE"]
        else:
            draw_text_block(
                self.screen,
                "Scegli la difficoltà:\nTHE JOURNEY — esperienza standard.\nTHE JOURNEY... WITHOUT ESCAPE — più severo; salvataggio senza ripristino.",
                self.font_small,
                COLOR_TEXT,
                pygame.Rect(40, 40, WIDTH - 80, 200),
            )
            opts = ["THE JOURNEY", "THE JOURNEY... WITHOUT ESCAPE"]
        for i, o in enumerate(opts):
            r = pygame.Rect(70, 252 + i * 40, WIDTH - 140, 36)
            col = COLOR_ACCENT if i == self.menu_index else COLOR_TEXT
            if r.collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, COLOR_CHOICE_HOVER, r, border_radius=6)
            self.screen.blit(self.font.render(o, True, col), (80, 260 + i * 40))

    def _draw_trophies(self) -> None:
        title = "Trophies" if self.language == "en" else "Trofei"
        self.screen.blit(self.font_title.render(title, True, COLOR_ACCENT), (40, 30))
        data = all_trophy_dicts(self.trophies_unlocked, getattr(self.state, "language", "it"))
        # paginated list with scroll
        y = 90
        vis = max(6, (HEIGHT - 140) // 26)
        start = max(0, min(self.trophies_scroll, max(0, len(data) - vis)))
        for item in data[start : start + vis]:
            status = "[OK]" if item["unlocked"] else "[  ]"
            line = f"{status} {item['title']} — {item['description']}"
            col = COLOR_TEXT if item["unlocked"] else (100, 100, 120)
            surf = self.font_small.render(line[:92], True, col)
            self.screen.blit(surf, (40, y))
            y += 26
        # scroll
        if len(data) > vis:
            pct = int(100 * (start / max(1, len(data) - vis)))
            if self.language == "en":
                bar = self.font_small.render(f"{start + 1}-{min(len(data), start + vis)} of {len(data)} ({pct}%)", True, COLOR_MUTED)
            else:
                bar = self.font_small.render(f"{start + 1}-{min(len(data), start + vis)} di {len(data)} ({pct}%)", True, COLOR_MUTED)
            self.screen.blit(bar, (WIDTH - 260, HEIGHT - 36))
        hint = "Enter/Esc: menu — mouse wheel to scroll" if self.language == "en" else "Invio/Esc: menu — rotella per scorrere"
        self.screen.blit(self.font_small.render(hint, True, COLOR_ACCENT), (40, HEIGHT - 36))

    def _draw_allocate_stats(self) -> None:
        draw_panel(self.screen, pygame.Rect(40, 40, WIDTH - 80, HEIGHT - 80), (24, 28, 46), COLOR_BOX_EDGE)
        title_text = "Assign stat points" if self.language == "en" else "Assegna punti statistica"
        title = self.font_title.render(title_text, True, COLOR_ACCENT)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))

        instr = (
            "Assign initial points: use ↑/↓ to select, ←/→ to remove/add. Enter to confirm."
            if self.language == "en"
            else "Assegna i punti iniziali: usa ↑↓ per selezionare, ←/→ per togliere/aggiungere. Invio per confermare."
        )
        self.screen.blit(self.font_small.render(instr, True, COLOR_MUTED), (80, 120))

        left = 120
        top = 160
        row_h = 46
        if self.language == "en":
            stats_display = [("Strength", "strength"), ("Kindness", "kindness"), ("Stubbornness", "stubbornness")]
        else:
            stats_display = [("Forza", "strength"), ("Gentilezza", "kindness"), ("Caparbietà", "stubbornness")]

        self._alloc_rects = []
        for i, (label, key) in enumerate(stats_display):
            y = top + i * row_h
            r = pygame.Rect(left, y, WIDTH - 320, 36)
            if i == self.alloc_index:
                pygame.draw.rect(self.screen, COLOR_CHOICE_HL, r, border_radius=6)
            else:
                pygame.draw.rect(self.screen, COLOR_BOX, r, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, r, width=1, border_radius=6)
            self.screen.blit(self.font.render(label, True, COLOR_TEXT), (r.x + 12, r.y + 6))

            val = int(self.alloc_stats.get(key, 0))
            val_surf = self.font.render(str(val), True, COLOR_ACCENT)
            self.screen.blit(val_surf, (r.right - 64, r.y + 6))

            # minus / plus buttons
            minus = pygame.Rect(r.right - 100, r.y + 6, 28, 24)
            plus = pygame.Rect(r.right - 36, r.y + 6, 28, 24)
            pygame.draw.rect(self.screen, COLOR_BOX, minus, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, minus, width=1, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_BOX, plus, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, plus, width=1, border_radius=4)
            mtxt = self.font.render("−", True, COLOR_TEXT)
            ptxt = self.font.render("+", True, COLOR_TEXT)
            self.screen.blit(mtxt, (minus.centerx - mtxt.get_width() // 2, minus.centery - mtxt.get_height() // 2))
            self.screen.blit(ptxt, (plus.centerx - ptxt.get_width() // 2, plus.centery - ptxt.get_height() // 2))
            self._alloc_rects.append((minus, plus))

        rem_text = f"Points remaining: {self.alloc_points}" if self.language == "en" else f"Punti rimanenti: {self.alloc_points}"
        rem = self.font_small.render(rem_text, True, COLOR_ACCENT)
        self.screen.blit(rem, (left, top + len(stats_display) * row_h + 8))

    def _draw_stats_chart(self) -> None:
        # small interactive bar chart bottom-right
        area = pygame.Rect(WIDTH - 240, HEIGHT - 120, 200, 96)
        pygame.draw.rect(self.screen, COLOR_BOX, area, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BOX_EDGE, area, width=1, border_radius=8)

        stats = [
            ("Str" if self.language == "en" else "For", self.state.strength, COLOR_FLASH_TRUST),
            ("Kin" if self.language == "en" else "Gen", self.state.kindness, COLOR_FLASH_TRUST),
            ("Stb" if self.language == "en" else "Cap", self.state.stubbornness, COLOR_FLASH_TRUST),
            ("Cor", self.state.corruption, COLOR_FLASH_WARN),
        ]

        vals = [max(0, int(v)) for _, v, _ in stats]
        max_v = max(max(vals) if vals else 0, 4)

        pad_x = 12
        gap = 8
        n = len(stats)
        bar_w = int((area.width - pad_x * 2 - gap * (n - 1)) / n)

        self._stats_bar_rects = []
        for i, (label, val, color) in enumerate(stats):
            x = area.x + pad_x + i * (bar_w + gap)
            h = int((max(0, int(val)) / max_v) * (area.height - 36))
            bar = pygame.Rect(x, area.y + area.height - 18 - h, bar_w, h)
            pygame.draw.rect(self.screen, color, bar, border_radius=4)
            # label
            lab = self.font_small.render(label, True, COLOR_TEXT)
            self.screen.blit(lab, (x + (bar_w - lab.get_width()) // 2, area.y + area.height - 14))
            self._stats_bar_rects.append((bar, label, int(val)))

        # tooltip on hover
        mx, my = self.mouse_pos
        for bar, label, val in self._stats_bar_rects:
            if bar.collidepoint((mx, my)):
                tip = f"{label}: {val}"
                surf = self.font_small.render(tip, True, COLOR_TEXT)
                tip_rect = pygame.Rect(mx + 12, my - 28, surf.get_width() + 8, surf.get_height() + 6)
                pygame.draw.rect(self.screen, (18, 20, 34), tip_rect, border_radius=6)
                pygame.draw.rect(self.screen, COLOR_BOX_EDGE, tip_rect, width=1, border_radius=6)
                self.screen.blit(surf, (tip_rect.x + 4, tip_rect.y + 3))

    def _draw_play(self) -> None:
        node = get_node(self.story, self.state.current_node)
        kind = node.get("kind")

        if kind == "fragment_hunt":
            self._draw_fragments(node)
            return
        if kind == "keypad":
            self._draw_keypad(node)
            return
        if kind == "click_sequence":
            self._draw_click(node)
            return
        if kind == "freefall" and self.ff_session:
            self._draw_freefall(node)
            return
        if kind == "simon" and self.simon_session:
            # draw the Simon minigame
            self.simon_session.draw(self.screen)
            return
        if kind == "stealth" and self.stealth_session:
            # draw the stealth minigame
            self.stealth_session.draw(self.screen)
            return

        text = self.tw_shown if self.tw_shown else substitute_name(node.get("text", ""), self.state.player_name)
        box = pygame.Rect(40, 52, WIDTH - 80, HEIGHT - 220)
        draw_panel(self.screen, box, COLOR_BOX, COLOR_BOX_EDGE)
        inner = pygame.Rect(box.x + 16, box.y + 16, box.width - 32, box.height - 32)
        clipped = self.screen.subsurface(inner).copy()
        draw_text_block(self.screen, text, self.font, COLOR_TEXT, inner)

        choices = visible_choices(self.state, node)
        y = HEIGHT - 148
        if self.tw_done:
            for i, ch in enumerate(choices):
                row = pygame.Rect(48, y + i * 28, WIDTH - 96, 26)
                hovered = row.collidepoint(self.mouse_pos)
                if i == self.choice_index:
                    pygame.draw.rect(self.screen, COLOR_CHOICE_HL, row, border_radius=5)
                    col = COLOR_ACCENT
                elif hovered:
                    pygame.draw.rect(self.screen, COLOR_CHOICE_HOVER, row, border_radius=5)
                    col = COLOR_TEXT
                else:
                    col = COLOR_TEXT
                line = f"› {ch['text']}" if i == self.choice_index else f"  {ch['text']}"
                self.screen.blit(self.font.render(line, True, col), (60, y + i * 28))

        self._draw_hud()

        if self.feedback_timer > 0 and self.feedback_msg:
            self.screen.blit(self.font_small.render(self.feedback_msg, True, self.feedback_color), (WIDTH // 2 - 120, 118))

        if self.message_line:
            self.screen.blit(self.font_small.render(self.message_line, True, (160, 255, 190)), (40, HEIGHT - 26))
            self.message_line = ""

    def _draw_hud(self) -> None:
        d = "Journey" if self.state.difficulty == Difficulty.THE_JOURNEY else "Without Escape"
        t = format_time(self.state.playtime_seconds)
        can_save = self.state.difficulty != Difficulty.WITHOUT_ESCAPE
        if self.language == "en":
            hud = (
                f"{self.state.player_name}  ·  {d}  ·  Act {self.state.act}  ·  {t}  ·  "
                f"F2 journal  ·  {'F5 save' if can_save else 'no save'}  ·  Esc pause  ·  F11"
            )
        else:
            hud = (
                f"{self.state.player_name}  ·  {d}  ·  Atto {self.state.act}  ·  {t}  ·  "
                f"F2 quaderno  ·  {'F5 salva' if can_save else 'no save'}  ·  Esc pausa  ·  F11"
            )
        self.screen.blit(self.font_small.render(hud, True, COLOR_MUTED), (36, 14))

    def _draw_fragments(self, node: dict[str, Any]) -> None:
        title = substitute_name(node.get("text", ""), self.state.player_name)
        draw_text_block(self.screen, title, self.font_small, COLOR_TEXT, pygame.Rect(30, 10, WIDTH - 60, 120))
        arena = pygame.Rect(40, 130, WIDTH - 80, HEIGHT - 180)
        draw_panel(self.screen, arena, (28, 32, 52), COLOR_BOX_EDGE)
        pulse = 1.0 + 0.14 * math.sin(pygame.time.get_ticks() / 280.0)
        for i, fr in enumerate(self.fragment_slots):
            base = (255, 230, 120) if i in self.fragments_done else (90, 200, 255)
            if i not in self.fragments_done:
                glow = pygame.Rect(
                    int(fr.x - 4 * pulse),
                    int(fr.y - 4 * pulse),
                    int(fr.w + 8 * pulse),
                    int(fr.h + 8 * pulse),
                )
                pygame.draw.rect(self.screen, (base[0] // 3, base[1] // 3, base[2] // 2), glow, width=2, border_radius=6)
            pygame.draw.rect(self.screen, base, fr, border_radius=4)
        pygame.draw.rect(self.screen, (240, 240, 255), self.player_rect)
        if self.language == "en":
            prog = f"Fragments: {len(self.fragments_done)}/3 — WASD / arrows / stick to move"
        else:
            prog = f"Frammenti: {len(self.fragments_done)}/3 — WASD / frecce / stick per muoverti"
        self.screen.blit(self.font_small.render(prog, True, COLOR_ACCENT), (40, HEIGHT - 36))
        self._draw_hud()

    def _draw_keypad(self, node: dict[str, Any]) -> None:
        draw_text_block(
            self.screen,
            substitute_name(node.get("text", ""), self.state.player_name),
            self.font_small,
            COLOR_TEXT,
            pygame.Rect(40, 30, WIDTH - 80, 150),
        )
        self.screen.blit(
            self.font_small.render(
                "Find the rule! THE_JOURNEY: current time HHMM | WITHOUT_ESCAPE: ASCII of your name (remove 0 digits)" if self.language == "en" else "THE_JOURNEY: ora attuale HHMM | WITHOUT_ESCAPE: ASCII del tuo nome (rimuovi le cifre 0)",
                True,
                COLOR_MUTED,
            ),
            (40, 188),
        )
        if self.state.difficulty == Difficulty.THE_JOURNEY:
            sol_hint = "Code = system time (HHMM)." if self.language == "en" else "Codice = ora di sistema (HHMM)."
        else:
            sol_hint = "Code = ASCII of name (without 0 digits)." if self.language == "en" else "Codice = ASCII del nome (senza carattere 0)."
        self.screen.blit(self.font_small.render(sol_hint, True, (150, 150, 170)), (40, 212))
        self.screen.blit(self.font.render(f"Digitato: {self.keypad_buffer}", True, COLOR_ACCENT), (40, 248))
        self.screen.blit(
            self.font_small.render(f"Tentativi: {self.keypad_attempts_left}", True, COLOR_TEXT),
            (40, 288),
        )
        labels = {"bk": "⌫", "ok": "OK", "0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9"}
        for rect, key in self._keypad_button_layout():
            pygame.draw.rect(self.screen, COLOR_BOX, rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, rect, width=1, border_radius=6)
            lab = labels.get(key, key)
            surf = self.font.render(lab, True, COLOR_TEXT)
            self.screen.blit(surf, (rect.centerx - surf.get_width() // 2, rect.centery - surf.get_height() // 2))
        hint = "Enter / OK · Backspace / ⌫ · click keys" if self.language == "en" else "Invio / OK · Backspace / ⌫ · clic sui tasti"
        self.screen.blit(self.font_small.render(hint, True, (120, 120, 140)), (40, HEIGHT - 52))
        self._draw_hud()

    def _draw_click(self, node: dict[str, Any]) -> None:
        draw_text_block(
            self.screen,
            substitute_name(node.get("text", ""), self.state.player_name),
            self.font_small,
            COLOR_TEXT,
            pygame.Rect(30, 10, WIDTH - 60, 90),
        )
        need = int(click_precision_required(self.state) * 100)
        for r in self.click_targets:
            pygame.draw.circle(self.screen, (255, 100, 120), r.center, r.w // 2)
            pygame.draw.circle(self.screen, (40, 20, 30), r.center, r.w // 2, 2)

        total = self.click_hits + self.click_misses
        prec = int((self.click_hits / total * 100)) if total else 100
        if self.language == "en":
            self.screen.blit(
                self.font.render(
                    f"Time: {self.click_time_left:.1f}s   Accuracy: {prec}% (min {need}%)",
                    True,
                    COLOR_ACCENT,
                ),
                (40, HEIGHT - 72),
            )
            self.screen.blit(
                self.font_small.render("Click circles with mouse or press A to hit — need " + str(need) + "% accuracy", True, COLOR_TEXT),
                (40, HEIGHT - 40),
            )
        else:
            self.screen.blit(
                self.font.render(
                    f"Tempo: {self.click_time_left:.1f}s   Precisione: {prec}% (min {need}%)",
                    True,
                    COLOR_ACCENT,
                ),
                (40, HEIGHT - 72),
            )
            self.screen.blit(
                self.font_small.render("Clicca i cerchi con mouse o premi A — serve " + str(need) + "% precisione", True, COLOR_TEXT),
                (40, HEIGHT - 40),
            )
        self._draw_hud()

    def _draw_freefall(self, node: dict[str, Any]) -> None:
        draw_text_block(
            self.screen,
            substitute_name(node.get("text", ""), self.state.player_name),
            self.font_small,
            COLOR_TEXT,
            pygame.Rect(24, 8, WIDTH - 48, 72),
        )
        ff = self.ff_session
        if not ff:
            return
        area = pygame.Rect(30, 88, WIDTH - 60, HEIGHT - 130)
        draw_panel(self.screen, area, (20, 22, 38), COLOR_BOX_EDGE)
        pygame.draw.line(self.screen, (60, 70, 110), (area.x + 40, area.y + 30), (area.right - 40, area.bottom - 30), 1)
        for o in ff.obstacles:
            pygame.draw.rect(self.screen, (200, 90, 110), o)
        pygame.draw.rect(self.screen, COLOR_ACCENT, ff.player_rect, border_radius=4)
        pct = min(100.0, 100.0 * ff.distance / max(1.0, ff.target_distance))
        if self.language == "en":
            self.screen.blit(self.font.render(f"Descent: {pct:.0f}% / goal", True, COLOR_ACCENT), (40, HEIGHT - 36))
            self.screen.blit(self.font_small.render("← → / stick to dodge red obstacles — one hit ends it", True, COLOR_MUTED), (40, HEIGHT - 58))
        else:
            self.screen.blit(self.font.render(f"Discesa: {pct:.0f}% / meta", True, COLOR_ACCENT), (40, HEIGHT - 36))
            self.screen.blit(self.font_small.render("← → / stick per evitare ostacoli rossi — un colpo e finisci", True, COLOR_MUTED), (40, HEIGHT - 58))
        self._draw_hud()

    def _draw_quit_confirm(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 230))
        self.screen.blit(overlay, (0, 0))
        draw_panel(self.screen, pygame.Rect(140, 140, WIDTH - 280, HEIGHT - 280), (28, 32, 50), COLOR_BOX_EDGE)
        title = "Quit game?" if self.language == "en" else "Uscire dal gioco?"
        t = self.font_title.render(title, True, COLOR_ACCENT)
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 180))
        sub_text = (
            "Autosave on pause; F5 to save manually." if self.language == "en" else "Salvataggio automatico in pausa; F5 salva manualmente."
        )
        sub = self.font_small.render(sub_text, True, COLOR_MUTED)
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 228))
        no_rect = pygame.Rect(WIDTH // 2 - 160, 320, 150, 40)
        yes_rect = pygame.Rect(WIDTH // 2 + 10, 320, 150, 40)
        if self.language == "en":
            opts = (("No, continue", no_rect, 0), ("Yes, quit", yes_rect, 1))
        else:
            opts = (("No, continua", no_rect, 0), ("Sì, esci", yes_rect, 1))
        for lab, r, idx in opts:
            if r.collidepoint(self.mouse_pos):
                bg = COLOR_CHOICE_HOVER
            elif self.quit_index == idx:
                bg = COLOR_CHOICE_HL
            else:
                bg = COLOR_BOX
            pygame.draw.rect(self.screen, bg, r, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, r, width=1, border_radius=8)
            s = self.font.render(lab, True, COLOR_TEXT)
            self.screen.blit(s, (r.centerx - s.get_width() // 2, r.centery - s.get_height() // 2))
        hint = (
            "← / → or click — Enter confirm — Esc cancel"
            if self.language == "en"
            else "← / → o clic — Invio conferma — Esc annulla"
        )
        self.screen.blit(self.font_small.render(hint, True, COLOR_MUTED), (WIDTH // 2 - 260, HEIGHT - 120))

    # ---- SETTINGS / ACCESSIBILITY ----
    _SETTINGS_KEYS = ["crt_filter", "text_size", "high_contrast"]

    def _update_settings(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        self._settings_rects = []
        y0 = 240
        for i in range(len(self._SETTINGS_KEYS)):
            r = pygame.Rect(WIDTH // 2 - 220, y0 + i * 52, 440, 46)
            self._settings_rects.append(r)

        mx, my = self.mouse_pos
        for i, r in enumerate(self._settings_rects):
            if r.collidepoint(mx, my):
                self._settings_index = i
                break

        if Action.UP in actions:
            self._settings_index = (self._settings_index - 1) % len(self._SETTINGS_KEYS)
        if Action.DOWN in actions:
            self._settings_index = (self._settings_index + 1) % len(self._SETTINGS_KEYS)

        def _toggle(idx: int) -> None:
            key = self._SETTINGS_KEYS[idx]
            if key == "crt_filter":
                self.crt_enabled = not self.crt_enabled
            elif key == "text_size":
                self.text_size_mode = (self.text_size_mode + 1) % 3
                self._apply_text_size()
            elif key == "high_contrast":
                self.high_contrast = not self.high_contrast

        if Action.CONFIRM in actions or Action.LEFT in actions or Action.RIGHT in actions:
            _toggle(self._settings_index)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(self._settings_rects):
                    if r.collidepoint(e.pos):
                        self._settings_index = i
                        _toggle(i)
                        break

        if Action.CANCEL in actions:
            self.mode = "menu"

    def _apply_text_size(self) -> None:
        sizes = [20, 24, 28]
        small_sizes = [17, 20, 24]
        title_sizes = [32, 38, 44]
        s = sizes[self.text_size_mode]
        ss = small_sizes[self.text_size_mode]
        ts = title_sizes[self.text_size_mode]
        self.font = pygame.font.SysFont("consolas", s)
        self.font_small = pygame.font.SysFont("consolas", ss)
        self.font_title = pygame.font.SysFont("consolas", ts, bold=True)

    def _draw_settings(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 230))
        self.screen.blit(overlay, (0, 0))
        draw_panel(self.screen, pygame.Rect(60, 30, WIDTH - 120, HEIGHT - 60), (28, 32, 50), COLOR_BOX_EDGE)

        title_text = "Settings" if self.language == "en" else "Impostazioni"
        t = self.font_title.render(title_text, True, COLOR_ACCENT)
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 50))

        sub = self.font_small.render(
            "Accessibility & display options" if self.language == "en" else "Opzioni accessibilita e visualizzazione",
            True, COLOR_MUTED,
        )
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 100))

        self._settings_rects = []
        y0 = 170
        for i, key in enumerate(self._SETTINGS_KEYS):
            r = pygame.Rect(WIDTH // 2 - 220, y0 + i * 52, 440, 46)
            self._settings_rects.append(r)
            if i == self._settings_index:
                pygame.draw.rect(self.screen, COLOR_CHOICE_HL, r, border_radius=6)
            elif r.collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, COLOR_CHOICE_HOVER, r, border_radius=6)
            else:
                pygame.draw.rect(self.screen, COLOR_BOX, r, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, r, width=1, border_radius=6)

            if key == "crt_filter":
                label = "CRT Filter"
                value = "ON" if self.crt_enabled else "OFF"
                desc = "Retro scanlines overlay" if self.language == "en" else "Overlay retro con righe CRT"
            elif key == "text_size":
                label = "Text Size"
                value = ["Normal", "Large", "Extra Large"][self.text_size_mode]
                if self.language != "en":
                    value = ["Normale", "Grande", "Molto Grande"][self.text_size_mode]
                desc = "Change font size" if self.language == "en" else "Cambia dimensione del testo"
            else:
                label = "High Contrast"
                value = "ON" if self.high_contrast else "OFF"
                desc = "Brighter text, stronger borders" if self.language == "en" else "Testo piu luminoso, bordi piu forti"

            self.screen.blit(self.font.render(label, True, COLOR_TEXT), (r.x + 12, r.y + 4))
            self.screen.blit(self.font_small.render(desc, True, COLOR_MUTED), (r.x + 12, r.y + 26))
            val_surf = self.font.render(value, True, (255, 200, 100))
            self.screen.blit(val_surf, (r.right - val_surf.get_width() - 14, r.y + 8))

        cancel_text = "Esc: back to menu" if self.language == "en" else "Esc: torna al menu"
        c = self.font_small.render(cancel_text, True, COLOR_MUTED)
        self.screen.blit(c, (WIDTH // 2 - c.get_width() // 2, HEIGHT - 50))

    def _draw_crt_overlay(self) -> None:
        # scanline grid CRT effect
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(self.screen, (0, 0, 0, 80), (0, y), (WIDTH, y))
        # subtle vignette
        for i in range(60):
            alpha = int(40 * (i / 60))
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(s, (0, 0, 0, alpha), (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 1)
            self.screen.blit(s, (0, 0))

    # ---- CONTROLLER RUMBLE ----
    def _rumble(self, strength: float = 0.5, duration_ms: int = 200) -> None:
        if self.joystick is None or self._rumble_cooldown > 0:
            return
        try:
            self.joystick.rumble(strength, strength, duration_ms)
            self._rumble_cooldown = duration_ms / 1000.0 + 0.3
        except (pygame.error, Exception):
            pass

    # ---- SAVE HELPER (blocks WITHOUT_ESCAPE) ----
    def _try_save(self) -> None:
        if self.state.difficulty == Difficulty.WITHOUT_ESCAPE:
            if self.language == "en":
                self.message_line = "Cannot save in WITHOUT ESCAPE mode."
            else:
                self.message_line = "Impossibile salvare in WITHOUT ESCAPE."
            return
        save_game(self.state, sorted(self.trophies_unlocked), slot=self.active_slot)
        self.message_line = f"Saved (slot {self.active_slot})." if self.language == "en" else f"Salvato (slot {self.active_slot})."

    # ---- JOURNAL / CODEX (F2) ----
    _JOURNAL_TABS = ["clues", "codex"]

    def _open_journal(self) -> None:
        self._journal_tab = 0
        self._journal_codex_index = 0
        self._journal_codex_scroll = 0
        self.mode = "journal"

    def _update_journal(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        lang = self.language or "it"
        unlocked = codex_mod.get_unlocked_entries(self.state)

        # tab switching
        tab_rects = [
            pygame.Rect(WIDTH // 2 - 220, 50, 180, 36),
            pygame.Rect(WIDTH // 2 + 40, 50, 180, 36),
        ]
        mx, my = self.mouse_pos
        for i, r in enumerate(tab_rects):
            if r.collidepoint(mx, my):
                self._journal_tab = i
                break

        if Action.LEFT in actions:
            self._journal_tab = 0
        if Action.RIGHT in actions:
            self._journal_tab = 1

        if self._journal_tab == 0:
            # clues tab - scroll support
            vis = max(6, (HEIGHT - 140) // 26)
            max_scroll = max(0, len(self.state.clues) - vis)
            for e in events:
                if e.type == pygame.MOUSEWHEEL:
                    self.log_scroll = int(max(0, min(max_scroll, self.log_scroll - e.y)))
            if Action.UP in actions:
                self.log_scroll = max(0, self.log_scroll - 1)
            if Action.DOWN in actions:
                self.log_scroll = min(max_scroll, self.log_scroll + 1)
        else:
            # codex tab
            self._journal_codex_rects = []
            y0 = 110
            for i, entry in enumerate(unlocked):
                r = pygame.Rect(WIDTH // 2 - 260, y0 + i * 32, 520, 28)
                self._journal_codex_rects.append(r)
                if r.collidepoint(mx, my):
                    self._journal_codex_index = i
                    break

            if Action.UP in actions:
                self._journal_codex_index = max(0, self._journal_codex_index - 1)
            if Action.DOWN in actions:
                self._journal_codex_index = min(len(unlocked) - 1, self._journal_codex_index + 1)

        if Action.CANCEL in actions:
            self.mode = "play"

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(tab_rects):
                    if r.collidepoint(e.pos):
                        self._journal_tab = i
                        break

    def _draw_journal(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 230))
        self.screen.blit(overlay, (0, 0))
        draw_panel(self.screen, pygame.Rect(40, 20, WIDTH - 80, HEIGHT - 40), (24, 28, 46), COLOR_BOX_EDGE)

        title = "Journal" if self.language == "en" else "Quaderno"
        t = self.font_title.render(title, True, COLOR_ACCENT)
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 28))

        lang = self.language or "it"
        unlocked = codex_mod.get_unlocked_entries(self.state)

        # tabs
        tab_rects = [
            pygame.Rect(WIDTH // 2 - 220, 72, 180, 36),
            pygame.Rect(WIDTH // 2 + 40, 72, 180, 36),
        ]
        tab_labels = [
            "Clues" if lang == "en" else "Indizi",
            "Codex" if lang == "en" else "Codex",
        ]
        for i, (r, label) in enumerate(zip(tab_rects, tab_labels)):
            bg = COLOR_CHOICE_HL if i == self._journal_tab else COLOR_BOX
            pygame.draw.rect(self.screen, bg, r, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, r, width=1, border_radius=6)
            txt = self.font.render(label, True, COLOR_TEXT if i == self._journal_tab else COLOR_MUTED)
            self.screen.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))

        if self._journal_tab == 0:
            self._draw_journal_clues()
        else:
            self._draw_journal_codex(unlocked)

        cancel_text = "Esc: back to game" if lang == "en" else "Esc: torna al gioco"
        c = self.font_small.render(cancel_text, True, COLOR_MUTED)
        self.screen.blit(c, (WIDTH // 2 - c.get_width() // 2, HEIGHT - 40))

    def _draw_journal_clues(self) -> None:
        clues = self.state.clues
        if not clues:
            empty = "No clues collected yet." if self.language == "en" else "Nessun indizio raccolto."
            self.screen.blit(self.font.render(empty, True, COLOR_MUTED), (WIDTH // 2 - 140, HEIGHT // 2))
            return

        # clue descriptions
        clue_descs: dict[str, str] = {
            "fear": ("The astral plane reacts to fear" if self.language == "en" else "Il piano astrale reagisce alla paura"),
            "exit_fake": ("Not all exits are real" if self.language == "en" else "Non tutte le uscite sono reali"),
            "monitoring": ("Real-world monitoring system connected" if self.language == "en" else "Sistema di monitoraggio reale collegato"),
            "memory_shard": ("Memory fragments weaken the Doctor" if self.language == "en" else "I frammenti indeboliscono il Dottore"),
            "brute_force": ("Violence leaves corruption" if self.language == "en" else "La violenza lascia corruzione"),
            "protocol": ("The Protocol's secret: continuity" if self.language == "en" else "Il segreto del Protocollo: continuita"),
            "graffiti": ("Others passed here before" if self.language == "en" else "Altri sono passati di qui"),
            "work_history": ("The factory where everything began" if self.language == "en" else "La fabbrica dove tutto e iniziato"),
            "kenji_truth": ("Unclassified error breaks the model" if self.language == "en" else "L'errore non classificato rompe il modello"),
        }

        vis = max(6, (HEIGHT - 180) // 34)
        max_scroll = max(0, len(clues) - vis)
        start = max(0, min(self.log_scroll, max_scroll))

        self._journal_clue_rects = []
        y = 120
        for i in range(start, min(len(clues), start + vis)):
            clue = clues[i]
            desc = clue_descs.get(clue, clue)
            r = pygame.Rect(80, y, WIDTH - 160, 30)
            self._journal_clue_rects.append(r)
            line = f"• {clue} — {desc}"
            self.screen.blit(self.font_small.render(line[:80], True, COLOR_TEXT), (r.x + 8, r.y + 4))
            y += 34

        if len(clues) > vis:
            pct = int(100 * (start / max(1, len(clues) - vis)))
            bar = self.font_small.render(f"{start + 1}-{min(len(clues), start + vis)} / {len(clues)} ({pct}%)", True, COLOR_MUTED)
            self.screen.blit(bar, (WIDTH // 2 - bar.get_width() // 2, HEIGHT - 60))

    def _draw_journal_codex(self, unlocked: list[codex_mod.CodexEntry]) -> None:
        if not unlocked:
            empty = "No entries unlocked yet. Explore the world to discover lore." if self.language == "en" else "Nessuna voce sbloccata. Esplora il mondo per scoprire la lore."
            txt = self.font_small.render(empty, True, COLOR_MUTED)
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2))
            return

        # left panel: list of unlocked entries
        panel = pygame.Rect(WIDTH // 2 - 280, 110, 240, HEIGHT - 190)
        draw_panel(self.screen, panel, (20, 24, 38), COLOR_BOX_EDGE)

        self._journal_codex_rects = []
        y = panel.y + 8
        for i, entry in enumerate(unlocked):
            data = codex_mod.get_entry_data(entry, self.language or "it")
            r = pygame.Rect(panel.x + 4, y, panel.width - 8, 26)
            self._journal_codex_rects.append(r)
            if i == self._journal_codex_index:
                pygame.draw.rect(self.screen, COLOR_CHOICE_HL, r, border_radius=4)
            col = COLOR_ACCENT if i == self._journal_codex_index else COLOR_TEXT
            self.screen.blit(self.font_small.render(data["title"][:22], True, col), (r.x + 6, r.y + 3))
            y += 28

        # right panel: selected entry content
        detail = pygame.Rect(WIDTH // 2 - 20, 110, 540, HEIGHT - 190)
        draw_panel(self.screen, detail, (24, 28, 46), COLOR_BOX_EDGE)

        sel = unlocked[self._journal_codex_index] if self._journal_codex_index < len(unlocked) else unlocked[0]
        data = codex_mod.get_entry_data(sel, self.language or "it")

        cat_labels = {"world": "World", "characters": "Characters", "experiment": "Experiment"}
        cat = cat_labels.get(sel.category, sel.category)
        cat_surf = self.font_small.render(f"[{cat}]", True, COLOR_MUTED)
        self.screen.blit(cat_surf, (detail.x + 16, detail.y + 8))

        title_surf = self.font.render(data["title"], True, COLOR_ACCENT)
        self.screen.blit(title_surf, (detail.x + 16, detail.y + 32))

        inner = pygame.Rect(detail.x + 16, detail.y + 60, detail.width - 32, detail.height - 76)
        draw_text_block(self.screen, data["text"], self.font_small, COLOR_TEXT, inner)

    # ---- DEBUG MENU ----
    _DEBUG_OPTIONS = [
        ("Fragment Hunt", "fragment_hunt"),
        ("Keypad", "keypad"),
        ("Click Sequence", "click_sequence"),
        ("Free Fall", "freefall"),
        ("Simon / Memory", "simon"),
        ("Stealth", "stealth"),
    ]

    def _update_debug_hold(self, events: list[pygame.event.Event], dt: float) -> None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_KP_PLUS] or keys[pygame.K_EQUALS]:
            self._debug_hold_time += dt
            if self._debug_hold_time >= 10.0:
                self._debug_hold_time = 0.0
                self._debug_menu_index = 0
                self._mode_before_quit = "play"
                self.mode = "debug_menu"
        else:
            self._debug_hold_time = 0.0

    def _draw_debug_hold_indicator(self) -> None:
        if self._debug_hold_time <= 0 or self.mode != "play":
            return
        pct = min(1.0, self._debug_hold_time / 10.0)
        w, h = 120, 8
        x, y = WIDTH - w - 20, 12
        pygame.draw.rect(self.screen, (40, 40, 60), (x, y, w, h), border_radius=3)
        pygame.draw.rect(self.screen, (255, 120, 120), (x, y, int(w * pct), h), border_radius=3)
        lbl = self.font_small.render("DEBUG", True, (255, 140, 140))
        self.screen.blit(lbl, (x, y - 16))

    def _update_debug_menu(self, events: list[pygame.event.Event], actions: set[Action]) -> None:
        self._debug_option_rects = []
        cx = WIDTH // 2
        for i, (label, _key) in enumerate(self._DEBUG_OPTIONS):
            r = pygame.Rect(cx - 200, 160 + i * 42, 400, 38)
            if i < len(self._debug_option_rects):
                self._debug_option_rects[i] = r
            else:
                self._debug_option_rects.append(r)

        mx, my = self.mouse_pos
        for i, r in enumerate(self._debug_option_rects[: len(self._DEBUG_OPTIONS)]):
            if r.collidepoint(mx, my):
                self._debug_menu_index = i
                break

        if Action.UP in actions:
            self._debug_menu_index = (self._debug_menu_index - 1) % len(self._DEBUG_OPTIONS)
        if Action.DOWN in actions:
            self._debug_menu_index = (self._debug_menu_index + 1) % len(self._DEBUG_OPTIONS)

        def _launch(idx: int) -> None:
            _, mg = self._DEBUG_OPTIONS[idx]
            self._launch_debug_minigame(mg)

        if Action.CONFIRM in actions:
            _launch(self._debug_menu_index)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(self._debug_option_rects[: len(self._DEBUG_OPTIONS)]):
                    if r.collidepoint(e.pos):
                        self._debug_menu_index = i
                        _launch(i)
                        break

        if Action.CANCEL in actions:
            self.mode = "play"

    def _launch_debug_minigame(self, minigame: str) -> None:
        self._minigame_mode = minigame
        self.dialogue_log.clear()
        if minigame == "fragment_hunt":
            self.fragments_done = set()
            self.fragment_slots = [r.copy() for r in self._fragment_layouts["default"]]
            self.player_rect.center = (WIDTH // 2, HEIGHT // 2 + 60)
        elif minigame == "keypad":
            self.keypad_buffer = ""
            self.keypad_attempts_left = 2
        elif minigame == "click_sequence":
            self._reset_click_game()
        elif minigame == "freefall":
            self.ff_session = new_session(self.state, freefall_target_units(self.state))
        elif minigame == "simon":
            self.simon_session = SimonSession(rounds=3, lang=self.language or "en")
        elif minigame == "stealth":
            self.stealth_session = StealthSession(time_limit=6.0, lang=self.language or "en")
        self.mode = "debug_minigame"

    def _update_debug_minigame(self, events: list[pygame.event.Event], actions: set[Action], dt: float) -> None:
        mg = self._minigame_mode
        if mg == "fragment_hunt":
            self._update_fragments(events, actions, dt)
            if len(self.fragments_done) >= 3:
                self.fragments_done = set()
                self.fragment_slots = [r.copy() for r in self._fragment_layouts["default"]]
                self.player_rect.center = (WIDTH // 2, HEIGHT // 2 + 60)
            if Action.CANCEL in actions:
                self.mode = "debug_menu"
        elif mg == "keypad":
            self._update_keypad(events, actions)
            if Action.CANCEL in actions:
                self.keypad_buffer = ""
                self.keypad_attempts_left = 2
                self.mode = "debug_menu"
        elif mg == "click_sequence":
            self._update_click(events, actions, dt)
            if not self.click_active:
                self._reset_click_game()
        elif mg == "freefall" and self.ff_session:
            self._update_freefall(events, actions, dt)
            if not self.ff_session:
                self.ff_session = new_session(self.state, freefall_target_units(self.state))
        elif mg == "simon" and self.simon_session:
            self.simon_session.update(dt)
            for e in events:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.simon_session.handle_click(e.pos)
            if self.simon_session.success or self.simon_session.failed:
                self.simon_session = SimonSession(rounds=3, lang=self.language or "en")
        elif mg == "stealth" and self.stealth_session:
            self.stealth_session.update(dt)
            if self.stealth_session.success or self.stealth_session.failed:
                self.stealth_session = StealthSession(time_limit=6.0, lang=self.language or "en")

        if Action.CANCEL in actions and mg not in ("fragment_hunt", "keypad"):
            self.mode = "debug_menu"

    def _draw_debug_menu(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 230))
        self.screen.blit(overlay, (0, 0))
        draw_panel(self.screen, pygame.Rect(60, 30, WIDTH - 120, HEIGHT - 60), (28, 32, 50), (255, 100, 100))

        t = self.font_title.render("DEBUG — Minigame Test", True, (255, 120, 120))
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 60))

        hint = self.font_small.render("Hold '+' for 10s during play to reopen this menu", True, COLOR_MUTED)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 100))

        self._debug_option_rects = []
        cx = WIDTH // 2
        for i, (label, _key) in enumerate(self._DEBUG_OPTIONS):
            r = pygame.Rect(cx - 200, 160 + i * 42, 400, 38)
            self._debug_option_rects.append(r)
            if i == self._debug_menu_index:
                pygame.draw.rect(self.screen, COLOR_CHOICE_HL, r, border_radius=6)
            elif r.collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, COLOR_CHOICE_HOVER, r, border_radius=6)
            else:
                pygame.draw.rect(self.screen, COLOR_BOX, r, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, r, width=1, border_radius=6)
            lab = self.font.render(label, True, COLOR_TEXT)
            self.screen.blit(lab, (r.x + 12, r.y + 6))

        cancel_text = "Esc: back to game" if self.language == "en" else "Esc: torna al gioco"
        c = self.font_small.render(cancel_text, True, COLOR_MUTED)
        self.screen.blit(c, (WIDTH // 2 - c.get_width() // 2, HEIGHT - 50))

    def _draw_debug_minigame(self) -> None:
        mg = self._minigame_mode
        if mg == "fragment_hunt":
            self._draw_debug_fragment_hunt()
        elif mg == "keypad":
            self._draw_debug_keypad()
        elif mg == "click_sequence":
            self._draw_debug_click()
        elif mg == "freefall":
            self._draw_debug_freefall()
        elif mg == "simon":
            if self.simon_session:
                self.simon_session.draw(self.screen)
        elif mg == "stealth":
            if self.stealth_session:
                self.stealth_session.draw(self.screen)

        # back hint
        hint = self.font_small.render("[Esc] back to debug menu", True, (255, 150, 150))
        self.screen.blit(hint, (WIDTH - 240, HEIGHT - 30))

    def _draw_debug_fragment_hunt(self) -> None:
        arena = pygame.Rect(40, 60, WIDTH - 80, HEIGHT - 120)
        draw_panel(self.screen, arena, (28, 32, 52), COLOR_BOX_EDGE)
        title = self.font_title.render("Fragment Hunt — Debug", True, (255, 150, 150))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))
        pulse = 1.0 + 0.14 * math.sin(pygame.time.get_ticks() / 280.0)
        for i, fr in enumerate(self.fragment_slots):
            base = (255, 230, 120) if i in self.fragments_done else (90, 200, 255)
            if i not in self.fragments_done:
                glow = pygame.Rect(int(fr.x - 4 * pulse), int(fr.y - 4 * pulse), int(fr.w + 8 * pulse), int(fr.h + 8 * pulse))
                pygame.draw.rect(self.screen, (base[0] // 3, base[1] // 3, base[2] // 2), glow, width=2, border_radius=6)
            pygame.draw.rect(self.screen, base, fr, border_radius=4)
        pygame.draw.rect(self.screen, (240, 240, 255), self.player_rect)
        if self.language == "en":
            self.screen.blit(self.font_small.render("WASD / arrows / stick to move — collect 3 fragments", True, COLOR_ACCENT), (50, HEIGHT - 55))
        else:
            self.screen.blit(self.font_small.render("WASD / frecce / stick per muoverti — raccogli 3 frammenti", True, COLOR_ACCENT), (50, HEIGHT - 55))
        prog = f"Fragments: {len(self.fragments_done)}/3"
        self.screen.blit(self.font.render(prog, True, COLOR_ACCENT), (50, HEIGHT - 35))

    def _draw_debug_keypad(self) -> None:
        title = self.font_title.render("Keypad — Debug", True, (255, 150, 150))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))
        if self.language == "en":
            hint = self.font_small.render("Type the code: HHMM (real time) or ASCII of name (no zeros). Enter to submit.", True, COLOR_MUTED)
        else:
            hint = self.font_small.render("Inserisci il codice: HHMM (ora reale) o ASCII del nome (senza zeri). Invio per confermare.", True, COLOR_MUTED)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 75))
        bx = pygame.Rect(WIDTH // 2 - 140, 130, 280, 40)
        draw_panel(self.screen, bx, (24, 28, 46), COLOR_BOX_EDGE)
        self.screen.blit(self.font.render(self.keypad_buffer or "_", True, COLOR_ACCENT), (bx.x + 12, bx.y + 5))
        att = f"Attempts: {self.keypad_attempts_left}" if self.language == "en" else f"Tentativi: {self.keypad_attempts_left}"
        self.screen.blit(self.font.render(att, True, COLOR_TEXT), (WIDTH // 2 - 70, 180))
        for rect, key in self._keypad_button_layout():
            label = "←" if key == "bk" else ("OK" if key == "ok" else key)
            pygame.draw.rect(self.screen, COLOR_BOX, rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_BOX_EDGE, rect, width=1, border_radius=6)
            ch = self.font.render(label, True, COLOR_TEXT)
            self.screen.blit(ch, (rect.centerx - ch.get_width() // 2, rect.centery - ch.get_height() // 2))
        if self.language == "en":
            self.screen.blit(self.font_small.render("Digit keys / click buttons — Backspace to delete — Enter / OK to submit", True, (120, 120, 140)), (40, HEIGHT - 52))
        else:
            self.screen.blit(self.font_small.render("Tasti numerici / clic sui pulsanti — Backspace per cancellare — Invio / OK per confermare", True, (120, 120, 140)), (40, HEIGHT - 52))

    def _draw_debug_click(self) -> None:
        title = self.font_title.render("Click Sequence — Debug", True, (255, 150, 150))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))
        need = int(click_precision_required(self.state) * 100)
        for r in self.click_targets:
            pygame.draw.circle(self.screen, (255, 100, 120), r.center, r.w // 2)
            pygame.draw.circle(self.screen, (40, 20, 30), r.center, r.w // 2, 2)
        total = self.click_hits + self.click_misses
        prec = int((self.click_hits / total * 100)) if total else 100
        if self.language == "en":
            self.screen.blit(self.font.render(f"Time: {self.click_time_left:.1f}s   Accuracy: {prec}% (min {need}%)", True, COLOR_ACCENT), (40, HEIGHT - 72))
            self.screen.blit(self.font_small.render("Click the circles with mouse or press A to hit the first one", True, COLOR_TEXT), (40, HEIGHT - 40))
        else:
            self.screen.blit(self.font.render(f"Tempo: {self.click_time_left:.1f}s   Precisione: {prec}% (min {need}%)", True, COLOR_ACCENT), (40, HEIGHT - 72))
            self.screen.blit(self.font_small.render("Clicca sui cerchi con il mouse o premi A per colpire il primo", True, COLOR_TEXT), (40, HEIGHT - 40))

    def _draw_debug_freefall(self) -> None:
        title = self.font_title.render("Free Fall — Debug", True, (255, 150, 150))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))
        ff = self.ff_session
        if not ff:
            return
        area = pygame.Rect(30, 58, WIDTH - 60, HEIGHT - 110)
        draw_panel(self.screen, area, (20, 22, 38), COLOR_BOX_EDGE)
        for o in ff.obstacles:
            pygame.draw.rect(self.screen, (200, 90, 110), o)
        pygame.draw.rect(self.screen, COLOR_ACCENT, ff.player_rect, border_radius=4)
        pct = min(100.0, 100.0 * ff.distance / max(1.0, ff.target_distance))
        if self.language == "en":
            self.screen.blit(self.font.render(f"Descent: {pct:.0f}% / goal", True, COLOR_ACCENT), (40, HEIGHT - 56))
            self.screen.blit(self.font_small.render("← → / stick to dodge obstacles — don't touch them!", True, COLOR_MUTED), (40, HEIGHT - 36))
        else:
            self.screen.blit(self.font.render(f"Discesa: {pct:.0f}% / meta", True, COLOR_ACCENT), (40, HEIGHT - 56))
            self.screen.blit(self.font_small.render("← → / stick per evitare gli ostacoli — non toccarli!", True, COLOR_MUTED), (40, HEIGHT - 36))


def main() -> None:
    GameApp().run()


if __name__ == "__main__":
    main()
