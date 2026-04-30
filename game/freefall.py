from __future__ import annotations # future is a module that allows using features from future Python versions. In this case, it allows using annotations for type hints without needing to import from __future__ in every file.

import random
from dataclasses import dataclass, field

import pygame

from game.state import Difficulty, GameState


@dataclass
class FreeFallSession: # free fall game session, used in act 5 variant B
    target_distance: float
    hard_mode: bool
    distance: float = 0.0
    player_x: float = 480.0
    spawn_timer: float = 0.0
    obstacles: list[pygame.Rect] = field(default_factory=list)
    vertical_speed: float = 190.0

    def __post_init__(self) -> None:
        if self.hard_mode:
            self.vertical_speed = 280.0

    @property
    def player_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.player_x) - 22, 430, 44, 22)

    def update(self, dt: float, move_left: float, move_right: float, width: int) -> str:
        # move player, spawn obstacles, move obstacles, check collisions, check win/lose
        self.distance += self.vertical_speed * dt * 0.42
        self.player_x += (move_right - move_left) * 360 * dt
        self.player_x = max(70.0, min(float(width - 70), self.player_x))

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            w = random.randint(52, 110)
            h = random.randint(18, 36)
            x = random.randint(60, width - 60 - w)
            self.obstacles.append(pygame.Rect(x, -h - 10, w, h))
            base = 0.45 if not self.hard_mode else 0.28
            self.spawn_timer = base + random.random() * 0.35

        fall = self.vertical_speed * dt * 1.15
        for o in self.obstacles:
            o.y += int(fall)

        self.obstacles = [o for o in self.obstacles if o.y < 560]

        pr = self.player_rect # player rectangle for collision
        for o in self.obstacles:
            if pr.colliderect(o):
                return "lose"

        if self.distance >= self.target_distance: # win condition
            return "win"
        return "continue"


def new_session(state: GameState, target: float) -> FreeFallSession: 
    hard = state.difficulty == Difficulty.WITHOUT_ESCAPE
    return FreeFallSession(target_distance=target, hard_mode=hard)
