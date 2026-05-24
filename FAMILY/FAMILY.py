#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import numpy as np
import random
from collections import deque
import matplotlib.pyplot as plt

# ====================== ПАРАМЕТРЫ МОДЕЛИ ======================
MALE_INCOME_BASE = 5.0
FEMALE_INCOME_BASE = 4.0
EXPENDITURE_BASE = 0.80

INIT_CAPITAL_MEAN = 190.0
INIT_CAPITAL_STD = 80.0

INIT_ADAPT_MEAN = 50.0
INIT_ADAPT_STD = 15.0
INIT_TOLERANCE_MEAN = 50.0
INIT_TOLERANCE_STD = 15.0
A_MAX = 100.0
S_MAX = 100.0

INIT_WORKING_PROB = 0.05
EXPENDITURE_MIN = 0.08
EXPENDITURE_MAX = 0.28

BIRTH_RATE_BASE = 0.012
DEATH_RATE_BASE = 0.015
CRISIS_DEATH_BONUS = 0.05

CRISIS_PERIOD = 200
BOOM_FACTOR = 1.5
CRISIS_FACTOR = 0.45

RESOURCE_BASE = 22.0
RESOURCE_CONSUMPTION = 4.0
RESOURCE_RENEWAL = 0.12
RESOURCE_DIFFUSION = 0.1

MOVE_PROB = 0.3
INFO_PANEL_WIDTH = 280
R_MAX = 350.0
PROB_QUIT_JOB = 0.05

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
COLOR_FAMILY_MALE = (255, 100, 100)
COLOR_FAMILY_BOTH = (100, 255, 100)
COLOR_OUTLINE = (0, 0, 0)

COLOR_MENU_BG = (38, 38, 48)
COLOR_MENU_SELECT = (80, 120, 200)
COLOR_INPUT_BG = (45, 45, 55)
COLOR_START_BUTTON = (40, 160, 80)
COLOR_START_HOVER = (60, 190, 110)


class Family:
    __slots__ = ('id', 'x', 'y', 'capital', 'adaptation', 'tolerance',
                 'woman_works', 'male_income', 'female_income',
                 'expenditure_rate', 'alive', 'config')
    def __init__(self, x, y, fid, config):
        self.id = fid
        self.x = x
        self.y = y
        self.capital = max(30.0, np.random.normal(INIT_CAPITAL_MEAN, INIT_CAPITAL_STD))
        self.adaptation = np.clip(np.random.normal(INIT_ADAPT_MEAN, INIT_ADAPT_STD), 20, A_MAX)
        self.tolerance = np.clip(np.random.normal(INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD), 20, S_MAX)
        self.woman_works = 1 if random.random() < INIT_WORKING_PROB else 0
        self.male_income = MALE_INCOME_BASE
        self.female_income = FEMALE_INCOME_BASE if self.woman_works else 0.0
        self.expenditure_rate = EXPENDITURE_BASE
        self.alive = True
        self.config = config

    def update(self, cell_resource, is_crisis):
        if not self.alive:
            return
        income = (self.male_income + self.female_income) * cell_resource
        spend = self.expenditure_rate * self.capital
        self.capital = self.capital - spend + income
        if self.capital <= 0:
            self.alive = False
            return
        an = self.adaptation / A_MAX
        sn = self.tolerance / S_MAX
        if self.capital < self.config['boardRet']:
            if self.woman_works == 0:
                self.woman_works = 1
                self.female_income = FEMALE_INCOME_BASE
                self.adaptation = min(A_MAX, self.adaptation + 2)
        elif self.capital < sn * an * self.config['boardRet']:
            self.expenditure_rate = max(EXPENDITURE_MIN, self.expenditure_rate * 0.97)
        elif self.capital > sn * an * R_MAX:
            if self.woman_works == 1 and random.random() < PROB_QUIT_JOB:
                self.woman_works = 0
                self.female_income = 0.0
            self.expenditure_rate = min(EXPENDITURE_MAX, self.expenditure_rate * 1.02)
        if self.capital < self.config['boardSog']:
            if random.random() < 0.12:
                self.alive = False
                return
        self.capital = min(self.capital, R_MAX * 2)
        if self.capital < self.config['boardRet']:
            self.adaptation = min(A_MAX, self.adaptation + 0.3)
            self.tolerance = max(20.0, self.tolerance - 0.15)
        else:
            self.adaptation = max(20.0, self.adaptation - 0.1)
            self.tolerance = min(S_MAX, self.tolerance + 0.05)

    def get_color(self):
        if not self.alive:
            return (60, 60, 70)
        return COLOR_FAMILY_BOTH if self.woman_works else COLOR_FAMILY_MALE


class World:
    def __init__(self, w, h, num_families, config):
        self.w = w
        self.h = h
        self.num_families = num_families
        self.config = config.copy()

        self.resource = np.ones((w, h)) * RESOURCE_BASE
        self.resource += np.random.uniform(-8, 8, (w, h))
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.2, RESOURCE_BASE * 2.0)

        all_cells = [(x, y) for x in range(w) for y in range(h)]
        random.shuffle(all_cells)
        self.families = []
        for i in range(min(num_families, len(all_cells))):
            x, y = all_cells[i]
            self.families.append(Family(x, y, i, self.config))

        self.time = 0
        self.next_phase_change = CRISIS_PERIOD
        self.global_phase = 'BOOM'
        self.pop_hist = deque(maxlen=2000)
        self.cap_hist = deque(maxlen=2000)
        self.work_hist = deque(maxlen=2000)
        self.expenditure_hist = deque(maxlen=2000)

    def is_cell_free(self, x, y, exclude=None):
        for f in self.families:
            if f.alive and f != exclude and f.x == x and f.y == y:
                return False
        return True

    def get_best_neighbor(self, fx, fy, radius, exclude):
        current_val = self.resource[fx, fy]
        best_dx, best_dy = 0, 0
        best_val = current_val
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = fx + dx, fy + dy
                if 0 <= nx < self.w and 0 <= ny < self.h:
                    if abs(dx) + abs(dy) == 1:
                        if self.is_cell_free(nx, ny, exclude):
                            if self.resource[nx, ny] > best_val:
                                best_val = self.resource[nx, ny]
                                best_dx, best_dy = dx, dy
        return best_dx, best_dy

    def find_free_cell(self):
        free_cells = [(x, y) for x in range(self.w) for y in range(self.h) if self.is_cell_free(x, y, None)]
        return random.choice(free_cells) if free_cells else None

    def update_resource_local(self):
        consumption = np.zeros((self.w, self.h))
        for f in self.families:
            if f.alive:
                consumption[f.x, f.y] += RESOURCE_CONSUMPTION
        self.resource -= consumption
        self.resource += RESOURCE_RENEWAL * (RESOURCE_BASE - self.resource) / 10.0
        diffused = self.resource.copy()
        diffused[1:-1, 1:-1] += RESOURCE_DIFFUSION * (
            (self.resource[0:-2, 1:-1] + self.resource[2:, 1:-1] +
             self.resource[1:-1, 0:-2] + self.resource[1:-1, 2:]) / 4.0 -
            self.resource[1:-1, 1:-1]
        )
        self.resource = diffused
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 3.0)

    def apply_global_phase(self):
        if self.global_phase == 'BOOM':
            self.resource *= BOOM_FACTOR
        else:
            self.resource *= CRISIS_FACTOR
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 5.0)

    def step(self):
        self.time += 1
        if self.time >= self.next_phase_change:
            self.global_phase = 'CRISIS' if self.global_phase == 'BOOM' else 'BOOM'
            self.next_phase_change = self.time + self.config['cris']
            self.apply_global_phase()
        self.update_resource_local()
        for f in self.families:
            if not f.alive:
                continue
            if random.random() < MOVE_PROB:
                dx, dy = self.get_best_neighbor(f.x, f.y, self.config['maxVision'], f)
                if dx != 0 or dy != 0:
                    f.x += dx
                    f.y += dy
        is_crisis = (self.global_phase == 'CRISIS')
        for f in self.families[:]:
            if f.alive:
                f.update(self.resource[f.x, f.y], is_crisis)
            if not f.alive:
                self.families.remove(f)
        avg_capital = np.mean([f.capital for f in self.families]) if self.families else 0
        birth_chance = BIRTH_RATE_BASE
        if self.global_phase == 'BOOM' and avg_capital > 250:
            birth_chance = BIRTH_RATE_BASE * 2
        elif self.global_phase == 'CRISIS':
            birth_chance = BIRTH_RATE_BASE * 0.3
        if random.random() < birth_chance:
            free = self.find_free_cell()
            if free:
                new_id = max([f.id for f in self.families] + [0]) + 1
                self.families.append(Family(free[0], free[1], new_id, self.config))
        death_rate = DEATH_RATE_BASE + (CRISIS_DEATH_BONUS if self.global_phase == 'CRISIS' else 0)
        for f in self.families[:]:
            if f.alive and random.random() < death_rate * 0.1:
                if f.capital < 150:
                    f.alive = False
                    self.families.remove(f)
        pop = len(self.families)
        if pop > 0:
            avg_cap = np.mean([f.capital for f in self.families])
            work_ratio = sum(1 for f in self.families if f.woman_works) / pop
            avg_expenditure = np.mean([f.expenditure_rate for f in self.families])
        else:
            avg_cap = 0
            work_ratio = 0
            avg_expenditure = 0
        self.pop_hist.append(pop)
        self.cap_hist.append(avg_cap)
        self.work_hist.append(work_ratio)
        self.expenditure_hist.append(avg_expenditure)

    def get_pop(self):
        return len(self.families)


class ConfigMenu:
    def __init__(self, screen, font, current_params, background_surface=None):
        self.screen = screen
        self.font = font
        self.params = current_params.copy()
        self.background_surface = background_surface  # сохранённый фон под меню
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

    def draw_background(self):
        """Рисует затемнённый фон (полупрозрачный слой поверх сохранённого фона)"""
        if self.background_surface is not None:
            # Копируем сохранённый фон
            self.screen.blit(self.background_surface, (0, 0))
            # Затемняем его (чёрный слой с прозрачностью)
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))  # 160 = полупрозрачный, не полностью чёрный
            self.screen.blit(overlay, (0, 0))
        else:
            # Если фона нет, просто заливаем цветом панели
            self.screen.fill(COLOR_PANEL)

    def draw(self):
        self.draw_background()
        
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

    def update_background(self, new_background):
        """Обновляет фон при изменении размера окна"""
        self.background_surface = new_background

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
    expenditure_data = list(world.expenditure_hist)
    if world.families:
        working = sum(1 for f in world.families if f.woman_works)
        non_working = len(world.families) - working
        categories = ['Работающие\nженщины', 'Неработающие\nженщины']
        values = [working, non_working]
    else:
        categories = ['Нет семей']
        values = [0]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Статистика модели семьи', fontsize=14)
    axes[0,0].plot(time_data, pop_data, color='#4488ff')
    axes[0,0].set_title('Изменение количества семей во времени')
    axes[0,0].set_xlabel('Шаг времени')
    axes[0,0].set_ylabel('Число семей')
    axes[0,0].grid(True, alpha=0.3)
    axes[0,1].plot(time_data, capital_data, color='#4CAF50')
    axes[0,1].set_title('Динамика среднего капитала семьи')
    axes[0,1].set_xlabel('Шаг времени')
    axes[0,1].set_ylabel('Капитал')
    axes[0,1].grid(True, alpha=0.3)
    axes[1,0].plot(time_data, expenditure_data, color='#f44336')
    axes[1,0].set_title('Изменение коэффициента расхода капитала')
    axes[1,0].set_xlabel('Шаг времени')
    axes[1,0].set_ylabel('Коэффициент расхода (γ)')
    axes[1,0].grid(True, alpha=0.3)
    bars = axes[1,1].bar(categories, values, color=['#4CAF50','#FF9800'])
    axes[1,1].set_title('Соотношение семей по идентичности женщин (текущее)')
    axes[1,1].set_ylabel('Количество семей')
    axes[1,1].set_ylim(0, max(values)*1.2 if values else 1)
    for bar,val in zip(bars,values):
        if val>0:
            axes[1,1].text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5, str(val), ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    plt.show(block=True)


def draw_world(screen, world, offset_x, offset_y, cell_size):
    for x in range(world.w):
        for y in range(world.h):
            val = world.resource[x, y]
            t = (val-5)/75
            t = max(0,min(1,t))
            color = (int(COLOR_RESOURCE_LOW[0]+t*(COLOR_RESOURCE_HIGH[0]-COLOR_RESOURCE_LOW[0])),
                     int(COLOR_RESOURCE_LOW[1]+t*(COLOR_RESOURCE_HIGH[1]-COLOR_RESOURCE_LOW[1])),
                     int(COLOR_RESOURCE_LOW[2]+t*(COLOR_RESOURCE_HIGH[2]-COLOR_RESOURCE_LOW[2])))
            rect = pygame.Rect(offset_x + x*cell_size, offset_y + y*cell_size, cell_size, cell_size)
            pygame.draw.rect(screen, color, rect)
    for f in world.families:
        rect = pygame.Rect(offset_x + f.x*cell_size, offset_y + f.y*cell_size, cell_size, cell_size)
        pygame.draw.rect(screen, f.get_color(), rect)
        pygame.draw.rect(screen, COLOR_OUTLINE, rect, 2)
        if f.capital > 600:
            center = (rect.centerx, rect.centery)
            pygame.draw.circle(screen, (255,255,200), center, max(2,cell_size//4))


def draw_simulation(screen, world, font, speed, paused, buttons, panel_rect, slider):
    pygame.draw.rect(screen, COLOR_PANEL, panel_rect)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, panel_rect, 2)
    y = panel_rect.top + 15
    avg_res = np.mean(world.resource) if len(world.resource)>0 else 0
    stats = [
        ("ВРЕМЯ", world.time),
        ("ЧИСЛЕННОСТЬ СЕМЕЙ", world.get_pop()),
        ("ФАЗА", "ПОДЪЁМ" if world.global_phase=='BOOM' else "КРИЗИС"),
        ("СРЕДНИЙ РЕСУРС", f"{avg_res:.1f}"),
        ("СРЕДНИЙ КАПИТАЛ", f"{world.cap_hist[-1] if world.cap_hist else 0:.1f}"),
        ("РАБОТАЮЩИЕ ЖЕНЩИНЫ", f"{int(world.work_hist[-1]*100) if world.work_hist else 0}%"),
    ]
    for label, val in stats:
        color = COLOR_TEXT if label!="ФАЗА" else (COLOR_BUTTON_STATS if val=="ПОДЪЁМ" else COLOR_BUTTON_RESET)
        left = font.render(label, True, COLOR_TEXT_DIM)
        right = font.render(str(val), True, color)
        screen.blit(left, (panel_rect.left+15, y))
        screen.blit(right, (panel_rect.right - right.get_width() - 15, y))
        y += 24
    y += 5
    param_title = font.render("ПАРАМЕТРЫ МОДЕЛИ", True, COLOR_TEXT_DIM)
    screen.blit(param_title, (panel_rect.left+15, y))
    y += 20
    for p in [f"ПОЛЕ: {world.w}×{world.h}", f"СЕМЕЙ: {world.num_families}",
              f"boardRet: {world.config['boardRet']:.1f}", f"boardSog: {world.config['boardSog']:.1f}",
              f"maxVision: {world.config['maxVision']}", f"cris: {world.config['cris']}"]:
        txt = font.render(p, True, COLOR_TEXT)
        screen.blit(txt, (panel_rect.left+25, y))
        y += 20
    y += 10
    speed_label = font.render(f"СКОРОСТЬ: {speed}x", True, COLOR_TEXT_DIM)
    screen.blit(speed_label, (panel_rect.left+15, y))
    slider.rect.x = panel_rect.left+15
    slider.rect.y = y+22
    slider.draw(screen)
    y += 50
    button_y = y+10
    for btn in buttons:
        btn.rect.x = panel_rect.left+15
        btn.rect.y = button_y
        btn.rect.width = panel_rect.width-30
        btn.draw(screen, font)
        button_y += 50
    if len(world.pop_hist) > 1:
        gx = panel_rect.left+15
        gy = button_y+10
        gw = panel_rect.width-30
        gh = 80
        pygame.draw.rect(screen, COLOR_BG, (gx, gy, gw, gh), border_radius=8)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, (gx, gy, gw, gh), 2, border_radius=8)
        max_pop = max(world.pop_hist) if world.pop_hist else 1
        if max_pop == 0:
            max_pop = 1
        points = []
        step = max(1, len(world.pop_hist)//100)
        for i,p in enumerate(world.pop_hist):
            if i%step==0:
                px = gx + int(i*gw/len(world.pop_hist))
                py = gy + gh - int(p/max_pop*gh)
                points.append((px,py))
        if len(points)>1:
            pygame.draw.lines(screen, (100,180,255), False, points, 2)


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
        pygame.draw.rect(screen, (0,0,0,50), shadow, border_radius=10)
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
        pygame.draw.rect(screen, (70,70,85), self.rect, border_radius=6)
        handle_x = self.rect.left + int((self.value - self.min_val)/(self.max_val-self.min_val)*self.rect.width)
        handle_rect = pygame.Rect(handle_x-6, self.rect.centery-8, 12, 16)
        pygame.draw.rect(screen, (100,100,120), handle_rect, border_radius=4)
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
        rel_x = max(0, min(self.rect.width, pos[0]-self.rect.left))
        self.value = self.min_val + (rel_x/self.rect.width)*(self.max_val-self.min_val)
        self.value = round(self.value)


def capture_background(screen):
    """Сохраняет текущее содержимое экрана как поверхность для фона"""
    return screen.copy()


def main():
    pygame.init()
    screen = pygame.display.set_mode((1200,800), pygame.RESIZABLE)
    pygame.display.set_caption("Модель выживания семьи — компьютерное моделирование")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Segoe UI', 14)

    # Начальные параметры по умолчанию (для временного фона)
    default_params = {
        'numFamily': 50,
        'boardRet': 180.0,
        'boardSog': 60.0,
        'boardAdapt': 100.0,
        'maxVision': 1,
        'cris': 400,
        'worldXSize': 85,
        'worldYSize': 85
    }

    INFO_PANEL_WIDTH = 280
    def get_offsets_and_panel(screen_rect, w, h):
        panel_rect = pygame.Rect(screen_rect.right - INFO_PANEL_WIDTH, screen_rect.top,
                                 INFO_PANEL_WIDTH, screen_rect.height)
        available_width = screen_rect.width - INFO_PANEL_WIDTH
        available_height = screen_rect.height
        cell_size = max(2, min(available_width//w if w>0 else 8, available_height//h if h>0 else 8))
        field_w = w * cell_size
        field_h = h * cell_size
        offset_x = (available_width - field_w)//2
        offset_y = (available_height - field_h)//2
        return offset_x, offset_y, panel_rect, cell_size

    # Создаём временный мир для фона
    temp_config = {
        'boardRet': default_params['boardRet'],
        'boardSog': default_params['boardSog'],
        'maxVision': default_params['maxVision'],
        'cris': default_params['cris']
    }
    temp_world = World(default_params['worldXSize'], default_params['worldYSize'], 
                       default_params['numFamily'], temp_config)
    
    # Рисуем временный фон
    screen_rect = screen.get_rect()
    offset_x, offset_y, panel_rect, cell_size = get_offsets_and_panel(screen_rect, 
                                                                       default_params['worldXSize'], 
                                                                       default_params['worldYSize'])
    screen.fill(COLOR_BG)
    draw_world(screen, temp_world, offset_x, offset_y, cell_size)
    draw_simulation(screen, temp_world, font, 1, False, [], panel_rect, Slider(0,0,10,10,1,10,1))
    pygame.display.flip()
    
    # Сохраняем фон и показываем меню
    background = capture_background(screen)
    menu = ConfigMenu(screen, font, default_params, background)
    params = menu.run()
    if params is None:
        params = default_params

    # Создаём настоящий мир с выбранными параметрами
    WORLD_WIDTH = params['worldXSize']
    WORLD_HEIGHT = params['worldYSize']

    config = {
        'boardRet': params['boardRet'],
        'boardSog': params['boardSog'],
        'maxVision': params['maxVision'],
        'cris': params['cris']
    }
    world = World(WORLD_WIDTH, WORLD_HEIGHT, params['numFamily'], config)

    paused = False
    speed = 1
    running = True
    slider = Slider(0,0, INFO_PANEL_WIDTH-30,12, 1,10, speed)

    def toggle_pause():
        nonlocal paused
        paused = not paused

    def reset_with_menu():
        nonlocal world, screen, paused, WORLD_WIDTH, WORLD_HEIGHT
        # Сохраняем текущий экран как фон для меню
        background = capture_background(screen)
        current = {
            'numFamily': world.num_families,
            'boardRet': world.config['boardRet'],
            'boardSog': world.config['boardSog'],
            'boardAdapt': 100.0,
            'maxVision': world.config['maxVision'],
            'cris': world.config['cris'],
            'worldXSize': world.w,
            'worldYSize': world.h
        }
        menu = ConfigMenu(screen, font, current, background)
        new_params = menu.run()
        if new_params:
            WORLD_WIDTH = new_params['worldXSize']
            WORLD_HEIGHT = new_params['worldYSize']
            config = {
                'boardRet': new_params['boardRet'],
                'boardSog': new_params['boardSog'],
                'maxVision': new_params['maxVision'],
                'cris': new_params['cris']
            }
            world = World(WORLD_WIDTH, WORLD_HEIGHT, new_params['numFamily'], config)
            paused = False

    def show_stats():
        nonlocal paused
        was_paused = paused
        if not was_paused:
            paused = True
        show_statistics(world)
        paused = was_paused

    buttons = [
        ModernButton(0,0,0,40, "Пауза / Продолжить", toggle_pause, COLOR_BUTTON_PAUSE, COLOR_BUTTON_PAUSE_HOVER),
        ModernButton(0,0,0,40, "Сброс / Настройка", reset_with_menu, COLOR_BUTTON_RESET, COLOR_BUTTON_RESET_HOVER),
        ModernButton(0,0,0,40, "Показать графики", show_stats, COLOR_BUTTON_STATS, COLOR_BUTTON_STATS_HOVER),
    ]

    # Флаг для обработки ресайза во время работы меню (но у нас меню уже закрыто)
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
                    speed = min(10, speed+1)
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed-1)
                elif event.key == pygame.K_r:
                    reset_with_menu()
            slider.handle_event(event)
            for btn in buttons:
                btn.handle_event(event)

        speed = slider.value

        if not paused:
            for _ in range(speed):
                world.step()
                if world.get_pop() == 0 and world.time > 100:
                    paused = True

        screen.fill(COLOR_BG)
        draw_world(screen, world, offset_x, offset_y, cell_size)
        draw_simulation(screen, world, font, speed, paused, buttons, panel_rect, slider)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()