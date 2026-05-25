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
    avg_res = np.mean(world.resource) if len(world.resource) > 0 else 0

    phase_text = "КРИЗИС" if world.is_crisis else "ПОДЪЁМ"

    lines = [
        f"ВРЕМЯ: {world.time}",
        f"СЕМЕЙ: {world.get_population()}",
        f"ФАЗА: {phase_text}",
        f"СРЕДНИЙ РЕСУРС: {avg_res:.1f}",
        f"СРЕДНИЙ КАПИТАЛ: {world.cap_hist[-1] if world.cap_hist else 0:.0f}",
        f"РАБОТАЮЩИЕ ЖЕНЩИНЫ: {int(world.get_working_ratio() * 100)}%",
        "",
        f"ПОЛЕ: {world.w}×{world.h}",
        f"ГРАНИЦА КРИЗИСА: {world.config.get('boardRet', 180):.0f}" if hasattr(world, 'config') else "ГРАНИЦА КРИЗИСА: 180",
        f"ГРАНИЦА ТОЛЕРАНТНОСТИ: {world.config.get('boardSog', 60):.0f}" if hasattr(world, 'config') else "ГРАНИЦА ТОЛЕРАНТНОСТИ: 60",
        f"РАДИУС ВИДИМОСТИ: {world.max_vision}",
        f"ПЕРИОД КРИЗИСА: {world.config.get('cris', 400)}" if hasattr(world, 'config') else "ПЕРИОД КРИЗИСА: 400",
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
        button_y += 45

    # ===== МИНИ-ГРАФИК ПОПУЛЯЦИИ =====
    if len(world.pop_hist) > 5:
        gx = panel_rect.left + 15
        gy = button_y + 15
        gw = panel_rect.width - 30
        gh = 70
        pygame.draw.rect(screen, COLOR_BG, (gx, gy, gw, gh), border_radius=8)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, (gx, gy, gw, gh), 2, border_radius=8)

        pop_label = font.render("ДИНАМИКА ПОПУЛЯЦИИ", True, COLOR_TEXT_DIM)
        pop_label_rect = pop_label.get_rect(topleft=(gx + 5, gy - 18))
        screen.blit(pop_label, pop_label_rect)

        margin = 12
        inner_x = gx + margin
        inner_y = gy + margin
        inner_w = gw - margin * 2
        inner_h = gh - margin * 2

        if inner_w > 0 and inner_h > 0:
            max_pop = max(world.pop_hist) if world.pop_hist else 1
            if max_pop == 0:
                max_pop = 1

            points = []
            step = max(1, len(world.pop_hist) // 100)
            for i, p in enumerate(world.pop_hist):
                if i % step == 0:
                    px = inner_x + int(i * inner_w / len(world.pop_hist))
                    px = max(inner_x, min(inner_x + inner_w, px))
                    py = inner_y + inner_h - int(p / max_pop * inner_h)
                    py = max(inner_y, min(inner_y + inner_h, py))
                    points.append((px, py))

            if len(points) > 1:
                pygame.draw.lines(screen, (100, 180, 255), False, points, 2)

    button_y += 90

    # ===== ГИСТОГРАММА СОСТОЯНИЙ =====
    if world.get_population() > 0:
        state_counts = [0, 0, 0, 0, 0]
        for f in world.families:
            if f.alive:
                state = f.get_state(world.is_crisis)
                if 1 <= state <= 5:
                    state_counts[state - 1] += 1

        gx = panel_rect.left + 15
        gy = button_y + 15
        gw = panel_rect.width - 30
        gh = 85
        pygame.draw.rect(screen, COLOR_BG, (gx, gy, gw, gh), border_radius=8)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, (gx, gy, gw, gh), 2, border_radius=8)

        state_label = font.render("СТРАТЕГИИ СЕМЕЙ", True, COLOR_TEXT_DIM)
        state_label_rect = state_label.get_rect(topleft=(gx + 5, gy - 18))
        screen.blit(state_label, state_label_rect)

        margin = 12
        inner_x = gx + margin
        inner_y = gy + margin
        inner_w = gw - margin * 2
        inner_h = gh - margin * 2

        total = sum(state_counts)
        if total > 0 and inner_w > 0 and inner_h > 0:
            bar_width = inner_w // 5 - 8
            max_height = inner_h - 15
            colors = [(255, 200, 100), (255, 150, 100), (100, 200, 100), (100, 150, 255), (200, 100, 100)]
            labels = ["ПОИСК", "ЭКОН", "СТАБ", "БОГАТ", "РИСК"]

            for i in range(5):
                count = state_counts[i]
                height = int(count / total * max_height) if total > 0 else 0
                bar_x = inner_x + i * (bar_width + 8) + 4
                bar_y = inner_y + inner_h - height - 8
                if height > 0:
                    pygame.draw.rect(screen, colors[i], (bar_x, bar_y, bar_width, height))

                label = font.render(labels[i], True, COLOR_TEXT_DIM)
                label_rect = label.get_rect(center=(bar_x + bar_width//2, inner_y + inner_h + 6))
                screen.blit(label, label_rect)