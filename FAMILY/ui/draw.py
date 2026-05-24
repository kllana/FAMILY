# ui/draw.py
import pygame
import numpy as np
from config import RESOURCE_BASE, CELL_SIZE, INFO_PANEL_WIDTH
from colors import (
    COLOR_RESOURCE_LOW, COLOR_RESOURCE_HIGH, COLOR_PANEL, COLOR_PANEL_BORDER,
    COLOR_TEXT, COLOR_BG, COLOR_TEXT_DIM, COLOR_OUTLINE
)

def draw_world(screen, world, offset_x, offset_y, cell_size):
    for x in range(world.w):
        for y in range(world.h):
            val = world.resource[x, y]
            t = (val - RESOURCE_BASE * 0.2) / (RESOURCE_BASE * 2.8)
            t = max(0, min(1, t))
            color = (
                int(COLOR_RESOURCE_LOW[0] + t * (COLOR_RESOURCE_HIGH[0] - COLOR_RESOURCE_LOW[0])),
                int(COLOR_RESOURCE_LOW[1] + t * (COLOR_RESOURCE_HIGH[1] - COLOR_RESOURCE_LOW[1])),
                int(COLOR_RESOURCE_LOW[2] + t * (COLOR_RESOURCE_HIGH[2] - COLOR_RESOURCE_LOW[2]))
            )
            rect = pygame.Rect(offset_x + x * cell_size, offset_y + y * cell_size, cell_size, cell_size)
            pygame.draw.rect(screen, color, rect)
    for f in world.families:
        if not f.alive:
            continue
        rect = pygame.Rect(offset_x + f.x * cell_size, offset_y + f.y * cell_size, cell_size, cell_size)
        pygame.draw.rect(screen, f.get_color(), rect)
        pygame.draw.rect(screen, COLOR_OUTLINE, rect, 1)


def draw_simulation(screen, world, font, speed, paused, buttons, panel_rect, slider):
    pygame.draw.rect(screen, COLOR_PANEL, panel_rect)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, panel_rect, 2)
    y = panel_rect.top + 15
    lines = [
        f"ВРЕМЯ: {world.time}",
        f"ЧИСЛЕННОСТЬ СЕМЕЙ: {world.get_population()}",
        f"ФАЗА: {'КРИЗИС' if world.is_crisis else 'ПОДЪЁМ'}",
        f"СРЕДНИЙ РЕСУРС: {world.get_avg_resource():.1f}",
        f"СРЕДНИЙ КАПИТАЛ: {world.get_avg_capital():.0f}",
        f"РАБОТАЮЩИЕ ЖЕНЩИНЫ: {int(world.get_working_ratio() * 100)}%",
        "",
        f"ПОЛЕ: {world.w}×{world.h}",
        f"СЕМЕЙ: {world.get_population()}",
        f"boardRet: {world.config.get('boardRet', 180):.0f}" if hasattr(world, 'config') else f"boardRet: 180",
        f"boardSog: {world.config.get('boardSog', 60):.0f}" if hasattr(world, 'config') else f"boardSog: 60",
        f"maxVision: {world.max_vision}",
        f"cris: {world.config.get('cris', 400)}" if hasattr(world, 'config') else f"cris: 400",
    ]
    for line in lines:
        surf = font.render(line, True, COLOR_TEXT)
        screen.blit(surf, (panel_rect.left + 15, y))
        y += 24
    y += 10
    speed_label = font.render(f"СКОРОСТЬ: {speed}x", True, COLOR_TEXT_DIM)
    screen.blit(speed_label, (panel_rect.left + 15, y))
    slider.rect.x = panel_rect.left + 15
    slider.rect.y = y + 22
    slider.draw(screen)
    y += 50
    button_y = y + 10
    for btn in buttons:
        btn.rect.x = panel_rect.left + 15
        btn.rect.y = button_y
        btn.rect.width = panel_rect.width - 30
        btn.draw(screen, font)
        button_y += 50
    if len(world.pop_hist) > 5:
        gx = panel_rect.left + 15
        gy = button_y + 10
        gw = panel_rect.width - 30
        gh = 80
        pygame.draw.rect(screen, COLOR_BG, (gx, gy, gw, gh), border_radius=8)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, (gx, gy, gw, gh), 2, border_radius=8)
        max_pop = max(world.pop_hist) if world.pop_hist else 1
        if max_pop == 0:
            max_pop = 1
        points = []
        step = max(1, len(world.pop_hist) // 100)
        for i, p in enumerate(world.pop_hist):
            if i % step == 0:
                px = gx + int(i * gw / len(world.pop_hist))
                py = gy + gh - int(p / max_pop * gh)
                points.append((px, py))
        if len(points) > 1:
            pygame.draw.lines(screen, (100, 180, 255), False, points, 2)
