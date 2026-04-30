from __future__ import annotations

from enum import Enum, auto

import pygame


class Action(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    CONFIRM = auto()
    CANCEL = auto()
    PAUSE = auto()


def keyboard_actions_from_events(events: list[pygame.event.Event]) -> set[Action]:
    pressed: set[Action] = set()
    for e in events:
        if e.type != pygame.KEYDOWN:
            continue
        k = e.key
        if k in (pygame.K_UP, pygame.K_w):
            pressed.add(Action.UP)
        elif k in (pygame.K_DOWN, pygame.K_s):
            pressed.add(Action.DOWN)
        elif k in (pygame.K_LEFT, pygame.K_a):
            pressed.add(Action.LEFT)
        elif k in (pygame.K_RIGHT, pygame.K_d):
            pressed.add(Action.RIGHT)
        elif k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            pressed.add(Action.CONFIRM)
        elif k in (pygame.K_ESCAPE, pygame.K_x):
            pressed.add(Action.CANCEL)
        elif k == pygame.K_F1:
            pressed.add(Action.PAUSE)
    return pressed


def _joy_index(e: pygame.event.Event) -> int | None:
    if hasattr(e, "joy"):
        return int(e.joy)
    return None


def _event_matches_joystick(e: pygame.event.Event, joystick: pygame.joystick.Joystick) -> bool:
    iid = getattr(e, "instance_id", None)
    if iid is not None:
        try:
            return int(iid) == int(joystick.get_instance_id())
        except (AttributeError, TypeError):
            pass
    ji = _joy_index(e)
    return ji is not None and ji == joystick.get_id()


def joystick_actions(
    joystick: pygame.joystick.Joystick | None,
    events: list[pygame.event.Event],
) -> set[Action]:
    """Buttons and D-pad (hat) for menus/dialogues; no analog stick input here."""
    pressed: set[Action] = set()
    if joystick is None:
        return pressed

    for e in events:
        if e.type == pygame.JOYBUTTONDOWN and _event_matches_joystick(e, joystick):
            if e.button == 0:
                pressed.add(Action.CONFIRM)
            elif e.button == 1:
                pressed.add(Action.CANCEL)
            elif e.button in (6, 7, 8, 9):
                pressed.add(Action.PAUSE)

        if e.type == pygame.JOYHATMOTION and _event_matches_joystick(e, joystick):
            hx, hy = e.value
            if hy == 1:
                pressed.add(Action.UP)
            elif hy == -1:
                pressed.add(Action.DOWN)
            if hx == -1:
                pressed.add(Action.LEFT)
            elif hx == 1:
                pressed.add(Action.RIGHT)

    return pressed


def joystick_move_vector(joystick: pygame.joystick.Joystick | None) -> tuple[float, float]:
    """Left stick for continuous movement (e.g. fragment puzzle)."""
    if joystick is None or joystick.get_numaxes() < 2:
        return (0.0, 0.0)
    return (float(joystick.get_axis(0)), float(joystick.get_axis(1)))


def merge_actions(*sets: set[Action]) -> set[Action]:
    out: set[Action] = set()
    for s in sets:
        out |= s
    return out
