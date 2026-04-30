from __future__ import annotations

import pygame

#  utils for text wrapping and drawing text blocks with word wrapping
def wrap_lines(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for w in words[1:]:
            test = current + " " + w
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = w
        lines.append(current)
    return lines

# draw text with word wrapping inside a rect, with some padding
def draw_text_block(
    surf: pygame.Surface,
    text: str, # raw text with newlines
    font: pygame.font.Font, # preloaded font for performance
    color: tuple[int, int, int],
    rect: pygame.Rect,
    line_gap: int = 4,
) -> None:
    lines = wrap_lines(text, font, rect.width - 16)
    y = rect.y + 12
    for line in lines:
        s = font.render(line, True, color)
        surf.blit(s, (rect.x + 12, y))
        y += font.get_height() + line_gap
        if y > rect.bottom - 20:
            break
