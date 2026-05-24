#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import numpy as np
import random
from collections import deque
import matplotlib.pyplot as plt

# ====================== ПАРАМЕТРЫ (как в книге) ======================
NUM_FAMILIES = 50
BOARD_RET = 180.0
BOARD_SOG = 60.0
BOARD_ADAPT = 100.0
MAX_VISION = 1        # можно менять в меню: 1, 2, 3, 4, 5
CRIS_PERIOD = 400
WORLD_WIDTH = 85
WORLD_HEIGHT = 85

MALE_INCOME_BASE = 5.0
FEMALE_INCOME_BASE = 4.0
EXPENDITURE_BASE = 0.80

INIT_CAPITAL_MEAN = 190.0
INIT_CAPITAL_STD = 80.0
INIT_ADAPT_MEAN = 50.0
INIT_ADAPT_STD = 15.0
INIT_TOLERANCE_MEAN = 50.0
INIT_TOLERANCE_STD = 15.0

RESOURCE_BASE = 22.0
DELTA_BOOM = 0.025
DELTA_CRISIS = -0.025

MOVE_PROB = 0.3
CELL_SIZE = 8
INFO_PANEL_WIDTH = 280

# ====================== ЦВЕТА ======================
COLOR_BG = (18, 18, 24)
COLOR_PANEL = (30, 30, 38)
COLOR_PANEL_BORDER = (60, 60, 70)
COLOR_TEXT = (230, 230, 240)
COLOR_TEXT_DIM = (160, 160, 180)

COLOR_BUTTON_PAUSE = (200, 100, 50)
COLOR_BUTTON_PAUSE_HOVER = (220, 120, 70)
COLOR_BUTTON_RESET = (180, 60, 60)
COLOR_BUTTON_RESET_HOVER = (210, 80, 80)
COLOR_BUTTON_STATS = (50, 120, 180)
COLOR_BUTTON_STATS_HOVER = (70, 140, 210)

COLOR_RESOURCE_LOW = (0, 0, 80)
COLOR_RESOURCE_HIGH = (140, 210, 255)
COLOR_FAMILY_BOTH = (80, 255, 80)      # зелёный — оба работают
COLOR_FAMILY_MALE_ONLY = (255, 80, 80) # красный — только муж
COLOR_OUTLINE = (0, 0, 0)

COLOR_MENU_BG = (38, 38, 48)
COLOR_MENU_SELECT = (80, 120, 200)
COLOR_INPUT_BG = (45, 45, 55)
COLOR_START_BUTTON = (40, 160, 80)
COLOR_START_HOVER = (60, 190, 110)


class Woman:
    def __init__(self):
        self.works = False
        self.income = 0.0

    def update(self, family_capital, adaptation, is_crisis):
        if not self.works:
            if is_crisis and family_capital < adaptation * BOARD_RET:
                self.works = True
                self.income = FEMALE_INCOME_BASE
            elif family_capital < BOARD_SOG:
                self.works = True
                self.income = FEMALE_INCOME_BASE
        else:
            if not is_crisis and family_capital > adaptation * BOARD_RET * 5:
                if random.random() < 0.02:
                    self.works = False
                    self.income = 0.0
        return self.income


class Man:
    def __init__(self):
        self.income = MALE_INCOME_BASE


class Family:
    def __init__(self, x, y, fid):
        self.id = fid
        self.x = x
        self.y = y
        self.capital = max(10.0, np.random.normal(INIT_CAPITAL_MEAN, INIT_CAPITAL_STD))
        self.adaptation = max(0.0, np.random.normal(INIT_ADAPT_MEAN, INIT_ADAPT_STD))
        self.tolerance = max(0.0, np.random.normal(INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD))
        self.man = Man()
        self.woman = Woman()
        self.alive = True

    def update(self, cell_resource, is_crisis):
        if not self.alive:
            return
        male_income = self.man.income * cell_resource
        female_income = self.woman.update(self.capital, self.adaptation, is_crisis) * cell_resource
        total_income = male_income + female_income
        spend = EXPENDITURE_BASE * self.capital
        new_capital = self.capital - spend + total_income
        if new_capital <= 0:
            self.alive = False
            return
        self.capital = new_capital
        if is_crisis:
            self.adaptation = min(100.0, self.adaptation + 0.5)
            self.tolerance = max(0.0, self.tolerance - 0.3)
        else:
            self.adaptation = max(0.0, self.adaptation - 0.2)
            self.tolerance = min(100.0, self.tolerance + 0.2)
        if self.capital < BOARD_SOG and self.woman.works:
            if random.random() < 0.1:
                self.alive = False

    def is_both_working(self):
        return self.woman.works

    def get_color(self):
        if self.is_both_working():
            return COLOR_FAMILY_BOTH
        return COLOR_FAMILY_MALE_ONLY


class World:
    def __init__(self, w, h, num_families, max_vision):
        self.w = w
        self.h = h
        self.num_families = num_families
        self.max_vision = max_vision
        self.resource = np.ones((w, h)) * RESOURCE_BASE
        self.resource += np.random.uniform(-8, 8, (w, h))
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.2, RESOURCE_BASE * 2.0)
        all_cells = [(x, y) for x in range(w) for y in range(h)]
        random.shuffle(all_cells)
        self.families = []
        for i in range(min(num_families, len(all_cells))):
            x, y = all_cells[i]
            self.families.append(Family(x, y, i))
        self.time = 0
        self.next_phase_change = CRIS_PERIOD
        self.is_crisis = False
        self.pop_hist = deque(maxlen=2000)
        self.cap_hist = deque(maxlen=2000)
        self.work_hist = deque(maxlen=2000)
        self.step_counter = 0

    def get_avg_resource(self):
        return np.mean(self.resource) if len(self.resource) > 0 else 0

    def get_population(self):
        return len([f for f in self.families if f.alive])

    def get_avg_capital(self):
        alive = [f for f in self.families if f.alive]
        return np.mean([f.capital for f in alive]) if alive else 0

    def get_working_ratio(self):
        alive = [f for f in self.families if f.alive]
        if not alive:
            return 0
        return sum(1 for f in alive if f.is_both_working()) / len(alive)

    def update_resource_local(self):
        # Потребление
        for f in self.families:
            if f.alive:
                self.resource[f.x, f.y] -= 1.5
        # Восстановление
        self.resource += 0.2 * (RESOURCE_BASE - self.resource) / 10.0
        # Диффузия (каждый 3-й шаг для производительности)
        if self.step_counter % 3 == 0:
            diffused = self.resource.copy()
            diffused[1:-1, 1:-1] += 0.1 * ((self.resource[0:-2, 1:-1] + self.resource[2:, 1:-1] +
                                             self.resource[1:-1, 0:-2] + self.resource[1:-1, 2:]) / 4.0 -
                                            self.resource[1:-1, 1:-1])
            self.resource = diffused
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 3.0)

    def apply_global_phase(self):
        if self.is_crisis:
            self.resource *= DELTA_CRISIS + 1
        else:
            self.resource *= DELTA_BOOM + 1
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 5.0)

    def step(self):
        self.step_counter += 1
        self.time += 1
        
        # Смена фазы
        if self.time >= self.next_phase_change:
            self.is_crisis = not self.is_crisis
            self.next_phase_change = self.time + CRIS_PERIOD
            self.apply_global_phase()
        
        # Локальная динамика ресурса
        self.update_resource_local()
        
        # Движение семей (по оригинальной логике)
        for f in self.families:
            if not f.alive:
                continue
            if random.random() < MOVE_PROB:
                # Ищем лучшую клетку в радиусе maxVision
                best_val = self.resource[f.x, f.y]
                best_pos = (f.x, f.y)
                for dx in range(-self.max_vision, self.max_vision + 1):
                    for dy in range(-self.max_vision, self.max_vision + 1):
                        nx, ny = f.x + dx, f.y + dy
                        if 0 <= nx < self.w and 0 <= ny < self.h:
                            # Проверяем, свободна ли клетка
                            occupied = any(f2.x == nx and f2.y == ny and f2.alive and f2 != f for f2 in self.families)
                            if not occupied and self.resource[nx, ny] > best_val:
                                best_val = self.resource[nx, ny]
                                best_pos = (nx, ny)
                # Перемещаемся на 1 клетку в сторону лучшей (градиентный спуск)
                if best_pos != (f.x, f.y):
                    dx = np.sign(best_pos[0] - f.x)
                    dy = np.sign(best_pos[1] - f.y)
                    new_x = f.x + dx
                    new_y = f.y + dy
                    # Проверяем, свободна ли новая клетка
                    occupied = any(f2.x == new_x and f2.y == new_y and f2.alive and f2 != f for f2 in self.families)
                    if 0 <= new_x < self.w and 0 <= new_y < self.h and not occupied:
                        f.x, f.y = new_x, new_y
        
        # Обновление семей
        for f in self.families[:]:
            if f.alive:
                f.update(self.resource[f.x, f.y], self.is_crisis)
            if not f.alive:
                self.families.remove(f)
        
        # Рождаемость
        avg_capital = self.get_avg_capital()
        if not self.is_crisis and avg_capital > 150 and len(self.families) < self.w * self.h:
            if random.random() < 0.01:
                free_cells = [(x, y) for x in range(self.w) for y in range(self.h)
                              if not any(f.x == x and f.y == y for f in self.families)]
                if free_cells:
                    x, y = random.choice(free_cells)
                    new_id = max([f.id for f in self.families] + [0]) + 1
                    self.families.append(Family(x, y, new_id))
        
        # Смертность в кризис
        if self.is_crisis:
            for f in self.families[:]:
                if f.alive and random.random() < 0.01:
                    if f.capital < 50:
                        f.alive = False
                        self.families.remove(f)
        
        self.pop_hist.append(self.get_population())
        self.cap_hist.append(self.get_avg_capital())
        self.work_hist.append(self.get_working_ratio())


class ConfigMenu:
    def __init__(self, screen, font, current_params):
        self.screen = screen
        self.font = font
        self.params = current_params.copy()
        self.param_names = [
            "Количество семей (numFamily)",
            "Граница экономического кризиса для семьи (boardRet)",
            "Кризисная граница толерантности (boardSog)",
            "Кризисная граница адаптивности (boardAdapt)",
            "Максимальный радиус видимости (maxVision)",
            "Периодичность смены кризиса (cris)",
            "Ширина поля (worldXSize)",
            "Высота поля (worldYSize)"
        ]
        self.param_keys = ['numFamily', 'boardRet', 'boardSog', 'boardAdapt', 'maxVision', 'cris', 'worldXSize', 'worldYSize']
        self.param_rects = []
        self.selected_index = None
        self.editing = False
        self.edit_buffer = ""
        self.running = True
        self.result = None

    def draw(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        menu_w = 500
        menu_h = 520
        menu_x = (self.screen.get_width() - menu_w) // 2
        menu_y = (self.screen.get_height() - menu_h) // 2
        pygame.draw.rect(self.screen, COLOR_MENU_BG, (menu_x, menu_y, menu_w, menu_h), border_radius=15)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (menu_x, menu_y, menu_w, menu_h), 3, border_radius=15)
        title = self.font.render("Настройка параметров модели", True, COLOR_TEXT)
        self.screen.blit(title, (menu_x + menu_w//2 - title.get_width()//2, menu_y + 20))
        y = menu_y + 70
        self.param_rects.clear()
        for i, (name, key) in enumerate(zip(self.param_names, self.param_keys)):
            value = self.params[key]
            display_value = f"{value:.1f}" if isinstance(value, float) else str(value)
            color = COLOR_MENU_SELECT if (self.selected_index == i and not self.editing) else COLOR_TEXT
            text = self.font.render(f"{name}: {display_value}", True, color)
            rect = text.get_rect(topleft=(menu_x + 30, y))
            self.param_rects.append(rect)
            self.screen.blit(text, rect)
            y += 35
        if self.editing:
            edit_text = self.font.render(f"Введите новое значение: {self.edit_buffer}_ (ENTER — сохранить, ESC — отмена)", True, COLOR_TEXT)
            edit_rect = edit_text.get_rect(topleft=(menu_x + 30, y))
            pygame.draw.rect(self.screen, COLOR_INPUT_BG, edit_rect.inflate(10, 5), border_radius=5)
            self.screen.blit(edit_text, edit_rect)
        start_rect = pygame.Rect(menu_x + menu_w//2 - 100, menu_y + menu_h - 70, 200, 45)
        mouse_pos = pygame.mouse.get_pos()
        color_start = COLOR_START_HOVER if start_rect.collidepoint(mouse_pos) else COLOR_START_BUTTON
        pygame.draw.rect(self.screen, color_start, start_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_TEXT, start_rect, 2, border_radius=8)
        start_text = self.font.render("ЗАПУСТИТЬ СИМУЛЯЦИЮ", True, COLOR_TEXT)
        start_text_rect = start_text.get_rect(center=start_rect.center)
        self.screen.blit(start_text, start_text_rect)
        self.start_button_rect = start_rect

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.param_rects):
                if rect.collidepoint(event.pos):
                    self.selected_index = i
                    self.editing = True
                    self.edit_buffer = str(self.params[self.param_keys[i]])
                    return
            if hasattr(self, 'start_button_rect') and self.start_button_rect.collidepoint(event.pos):
                self.running = False
                self.result = self.params
                return
            if not self.editing:
                self.selected_index = None
        if event.type == pygame.KEYDOWN and self.editing:
            if event.key == pygame.K_RETURN:
                try:
                    key = self.param_keys[self.selected_index]
                    if key in ['numFamily', 'maxVision', 'cris', 'worldXSize', 'worldYSize']:
                        val = int(self.edit_buffer)
                    else:
                        val = float(self.edit_buffer)
                    self.params[key] = val
                except ValueError:
                    pass
                self.editing = False
                self.selected_index = None
                self.edit_buffer = ""
            elif event.key == pygame.K_ESCAPE:
                self.editing = False
                self.selected_index = None
                self.edit_buffer = ""
            elif event.key == pygame.K_BACKSPACE:
                self.edit_buffer = self.edit_buffer[:-1]
            else:
                char = event.unicode
                if char.isdigit() or char == '.' or char == '-':
                    self.edit_buffer += char

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                self.handle_event(event)
            self.draw()
            pygame.display.flip()
            clock.tick(30)
        return self.result


def show_statistics(world):
    time_data = list(range(len(world.pop_hist)))
    pop_data = list(world.pop_hist)
    capital_data = list(world.cap_hist)
    work_data = list(world.work_hist)
    working_ratio = world.get_working_ratio() if world.get_population() > 0 else 0
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Статистика модели семьи', fontsize=14)
    axes[0, 0].plot(time_data, pop_data, color='#4488ff')
    axes[0, 0].set_title('Изменение количества семей во времени')
    axes[0, 0].set_xlabel('Шаг времени')
    axes[0, 0].set_ylabel('Число семей')
    axes[0, 1].plot(time_data, capital_data, color='#4CAF50')
    axes[0, 1].set_title('Динамика среднего капитала семьи')
    axes[0, 1].set_xlabel('Шаг времени')
    axes[0, 1].set_ylabel('Капитал')
    axes[1, 0].plot(time_data, work_data, color='#FF9800')
    axes[1, 0].set_title('Доля работающих женщин')
    axes[1, 0].set_xlabel('Шаг времени')
    axes[1, 0].set_ylabel('Доля')
    working = int(working_ratio * world.get_population())
    non_working = world.get_population() - working
    bars = axes[1, 1].bar(['Работающие\nженщины', 'Неработающие\nженщины'],
                          [working, non_working],
                          color=['#4CAF50', '#FF9800'])
    axes[1, 1].set_title('Соотношение семей по идентичности женщин (текущее)')
    axes[1, 1].set_ylabel('Количество семей')
    for bar, val in zip(bars, [working, non_working]):
        if val > 0:
            axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                            str(val), ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    plt.show(block=True)


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
        f"boardRet: {BOARD_RET:.0f}",
        f"boardSog: {BOARD_SOG:.0f}",
        f"maxVision: {world.max_vision}",
        f"cris: {CRIS_PERIOD}",
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


class ModernButton:
    def __init__(self, x, y, w, h, text, action, color_idle, color_hover):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.hovered = False
        self.color_idle = color_idle
        self.color_hover = color_hover

    def draw(self, screen, font):
        color = self.color_hover if self.hovered else self.color_idle
        shadow = self.rect.copy()
        shadow.x += 2
        shadow.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 50), shadow, border_radius=10)
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, COLOR_TEXT, self.rect, 2, border_radius=10)
        text_surf = font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()


class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial_val):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.dragging = False

    def draw(self, screen):
        pygame.draw.rect(screen, (70, 70, 85), self.rect, border_radius=6)
        handle_x = self.rect.left + int((self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width)
        handle_rect = pygame.Rect(handle_x - 6, self.rect.centery - 8, 12, 16)
        pygame.draw.rect(screen, (100, 100, 120), handle_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, self.rect, 1, border_radius=6)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_pos(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_pos(event.pos)

    def _set_from_pos(self, pos):
        rel_x = max(0, min(self.rect.width, pos[0] - self.rect.left))
        self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)
        self.value = round(self.value)


def main():
    global NUM_FAMILIES, BOARD_RET, BOARD_SOG, BOARD_ADAPT, MAX_VISION, CRIS_PERIOD, WORLD_WIDTH, WORLD_HEIGHT
    
    pygame.init()
    screen = pygame.display.set_mode((1200, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Модель выживания семьи — компьютерное моделирование")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Segoe UI', 14)

    default_params = {
        'numFamily': NUM_FAMILIES,
        'boardRet': BOARD_RET,
        'boardSog': BOARD_SOG,
        'boardAdapt': BOARD_ADAPT,
        'maxVision': MAX_VISION,
        'cris': CRIS_PERIOD,
        'worldXSize': WORLD_WIDTH,
        'worldYSize': WORLD_HEIGHT
    }

    # Временный мир для фона
    temp_world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
    screen_rect = screen.get_rect()
    def get_offsets_and_panel(screen_rect, w, h):
        panel_rect = pygame.Rect(screen_rect.right - INFO_PANEL_WIDTH, screen_rect.top,
                                 INFO_PANEL_WIDTH, screen_rect.height)
        available_width = screen_rect.width - INFO_PANEL_WIDTH
        available_height = screen_rect.height
        cell_size = max(2, min(available_width // w if w > 0 else 8, available_height // h if h > 0 else 8))
        field_w = w * cell_size
        field_h = h * cell_size
        offset_x = (available_width - field_w) // 2
        offset_y = (available_height - field_h) // 2
        return offset_x, offset_y, panel_rect, cell_size

    offset_x, offset_y, panel_rect, cell_size = get_offsets_and_panel(screen_rect, WORLD_WIDTH, WORLD_HEIGHT)
    screen.fill(COLOR_BG)
    draw_world(screen, temp_world, offset_x, offset_y, cell_size)
    pygame.display.flip()

    menu = ConfigMenu(screen, font, default_params)
    params = menu.run()
    if params:
        NUM_FAMILIES = params['numFamily']
        BOARD_RET = params['boardRet']
        BOARD_SOG = params['boardSog']
        CRIS_PERIOD = params['cris']
        MAX_VISION = params['maxVision']
        WORLD_WIDTH = params['worldXSize']
        WORLD_HEIGHT = params['worldYSize']

    world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)

    paused = False
    speed = 1
    running = True
    slider = Slider(0, 0, INFO_PANEL_WIDTH - 30, 12, 1, 10, speed)

    def toggle_pause():
        nonlocal paused
        paused = not paused

    def reset_with_menu():
        nonlocal world, paused
        global NUM_FAMILIES, BOARD_RET, BOARD_SOG, CRIS_PERIOD, MAX_VISION, WORLD_WIDTH, WORLD_HEIGHT
        current = {
            'numFamily': NUM_FAMILIES,
            'boardRet': BOARD_RET,
            'boardSog': BOARD_SOG,
            'boardAdapt': BOARD_ADAPT,
            'maxVision': MAX_VISION,
            'cris': CRIS_PERIOD,
            'worldXSize': WORLD_WIDTH,
            'worldYSize': WORLD_HEIGHT
        }
        menu = ConfigMenu(screen, font, current)
        new_params = menu.run()
        if new_params:
            NUM_FAMILIES = new_params['numFamily']
            BOARD_RET = new_params['boardRet']
            BOARD_SOG = new_params['boardSog']
            CRIS_PERIOD = new_params['cris']
            MAX_VISION = new_params['maxVision']
            WORLD_WIDTH = new_params['worldXSize']
            WORLD_HEIGHT = new_params['worldYSize']
            world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
            paused = False

    def show_stats():
        nonlocal paused
        was_paused = paused
        if not was_paused:
            paused = True
        show_statistics(world)
        paused = was_paused

    buttons = [
        ModernButton(0, 0, 0, 40, "Пауза / Продолжить", toggle_pause, COLOR_BUTTON_PAUSE, COLOR_BUTTON_PAUSE_HOVER),
        ModernButton(0, 0, 0, 40, "Сброс / Настройка", reset_with_menu, COLOR_BUTTON_RESET, COLOR_BUTTON_RESET_HOVER),
        ModernButton(0, 0, 0, 40, "Показать графики", show_stats, COLOR_BUTTON_STATS, COLOR_BUTTON_STATS_HOVER),
    ]

    while running:
        screen_rect = screen.get_rect()
        offset_x, offset_y, panel_rect, cell_size = get_offsets_and_panel(screen_rect, WORLD_WIDTH, WORLD_HEIGHT)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    toggle_pause()
                elif event.key == pygame.K_UP:
                    speed = min(10, speed + 1)
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - 1)
                elif event.key == pygame.K_r:
                    reset_with_menu()
            slider.handle_event(event)
            for btn in buttons:
                btn.handle_event(event)

        speed = slider.value

        if not paused:
            for _ in range(speed):
                world.step()
                if world.get_population() == 0:
                    paused = True

        screen.fill(COLOR_BG)
        draw_world(screen, world, offset_x, offset_y, cell_size)
        draw_simulation(screen, world, font, speed, paused, buttons, panel_rect, slider)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()