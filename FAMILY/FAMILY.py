#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import numpy as np
import random
from collections import deque

# ====================== ФИКСИРОВАННЫЕ ПАРАМЕТРЫ (не меняются в меню) ======================
# Доходы и расходы (средние)
MALE_INCOME_BASE = 5.0
FEMALE_INCOME_BASE = 4.0
EXPENDITURE_BASE = 0.18

# Начальный капитал
INIT_CAPITAL_MEAN = 400.0
INIT_CAPITAL_STD = 100.0

# Адаптивность и толерантность
INIT_ADAPT_MEAN = 50.0
INIT_ADAPT_STD = 15.0
INIT_TOLERANCE_MEAN = 50.0
INIT_TOLERANCE_STD = 15.0
A_MAX = 100.0
S_MAX = 100.0

INIT_WORKING_PROB = 0.3

# Границы расходов
EXPENDITURE_MIN = 0.08
EXPENDITURE_MAX = 0.28

# Демография
BIRTH_RATE_BASE = 0.012
DEATH_RATE_BASE = 0.015
CRISIS_DEATH_BONUS = 0.05

# Локальная динамика ресурса
RESOURCE_BASE = 22.0
RESOURCE_CONSUMPTION = 2.2
RESOURCE_RENEWAL = 0.35
RESOURCE_DIFFUSION = 0.1

# Глобальные циклы
BOOM_FACTOR = 1.4
CRISIS_FACTOR = 0.4

# Движение
MOVE_PROB = 0.3
CELL_SIZE = 18
INFO_PANEL_WIDTH = 280
R_MAX = 1000.0

# Цвета
COLOR_RESOURCE_LOW = (0, 60, 0)
COLOR_RESOURCE_HIGH = (80, 180, 80)
COLOR_FAMILY_MALE = (220, 50, 50)
COLOR_FAMILY_BOTH = (50, 220, 50)
COLOR_OUTLINE = (0, 0, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_PANEL = (30, 30, 40)
COLOR_MENU_BG = (20, 20, 30)
COLOR_MENU_SELECT = (100, 100, 200)
COLOR_INPUT_BG = (50, 50, 70)


class Family:
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

    def update(self, resource, global_phase):
        if not self.alive:
            return

        income = (self.male_income + self.female_income) * resource
        spend = self.expenditure_rate * self.capital
        self.capital = self.capital - spend + income

        if self.capital <= 0:
            self.alive = False
            return

        an = self.adaptation / A_MAX
        sn = self.tolerance / S_MAX

        if self.capital < an * self.config['r_bar']:
            if self.woman_works == 0:
                self.woman_works = 1
                self.female_income = FEMALE_INCOME_BASE
                self.adaptation = min(A_MAX, self.adaptation + 2)

        elif self.capital < sn * an * self.config['r_bar']:
            self.expenditure_rate = max(EXPENDITURE_MIN, self.expenditure_rate * 0.97)

        elif self.capital > sn * an * R_MAX:
            if self.woman_works == 1 and random.random() < 0.02:
                self.woman_works = 0
                self.female_income = 0.0
            self.expenditure_rate = min(EXPENDITURE_MAX, self.expenditure_rate * 1.02)

        if self.capital < self.config['r_hat']:
            if random.random() < 0.12:
                self.alive = False
                return

        self.capital = min(self.capital, R_MAX * 2)

        if self.capital < self.config['r_bar']:
            self.adaptation = min(A_MAX, self.adaptation + 0.3)
            self.tolerance = max(20.0, self.tolerance - 0.15)
        else:
            self.adaptation = max(20.0, self.adaptation - 0.1)
            self.tolerance = min(S_MAX, self.tolerance + 0.05)

    def get_color(self):
        if not self.alive:
            return (80, 80, 80)
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
        self.next_phase_change = self.config['crisis_period']
        self.global_phase = 'BOOM'
        self.pop_hist = deque(maxlen=2000)
        self.cap_hist = deque(maxlen=2000)
        self.work_hist = deque(maxlen=2000)

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
        free_cells = [(x, y) for x in range(self.w) for y in range(self.h)
                      if self.is_cell_free(x, y, None)]
        if free_cells:
            return random.choice(free_cells)
        return None

    def update_resource_local(self):
        consumption = np.zeros((self.w, self.h))
        for f in self.families:
            if f.alive:
                consumption[f.x, f.y] += RESOURCE_CONSUMPTION
        self.resource -= consumption
        self.resource += RESOURCE_RENEWAL * (RESOURCE_BASE - self.resource) / 10.0

        diffused = self.resource.copy()
        for i in range(1, self.w-1):
            for j in range(1, self.h-1):
                neighbors = [self.resource[i-1, j], self.resource[i+1, j],
                             self.resource[i, j-1], self.resource[i, j+1]]
                avg = np.mean(neighbors)
                diffused[i, j] += RESOURCE_DIFFUSION * (avg - self.resource[i, j])
        self.resource = diffused
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 4.0)

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
            self.next_phase_change = self.time + self.config['crisis_period']
            self.apply_global_phase()

        self.update_resource_local()

        # Движение
        for f in self.families:
            if not f.alive:
                continue
            if random.random() < MOVE_PROB:
                dx, dy = self.get_best_neighbor(f.x, f.y, self.config['max_vision'], f)
                if dx != 0 or dy != 0:
                    f.x += dx
                    f.y += dy

        # Обновление семей
        for f in self.families[:]:
            if f.alive:
                f.update(self.resource[f.x, f.y], self.global_phase)
            if not f.alive:
                self.families.remove(f)

        # Рождаемость
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

        # Смертность
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
        else:
            avg_cap = 0
            work_ratio = 0

        self.pop_hist.append(pop)
        self.cap_hist.append(avg_cap)
        self.work_hist.append(work_ratio)

    def get_pop(self):
        return len(self.families)


# ====================== МЕНЮ С КЛАВИАТУРНЫМ ВВОДОМ ======================
class ConfigMenu:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.params = {
            'num_families': 40,
            'r_bar': 180.0,
            'r_hat': 60.0,
            'max_vision': 4,
            'crisis_period': 200,
            'world_width': 40,
            'world_height': 30
        }
        self.param_names = [
            "Number of families (int)",
            "Crisis threshold R_BAR (float)",
            "Acute crisis R_HAT (float)",
            "Max vision radius (int)",
            "Crisis period steps (int)",
            "World width (int)",
            "World height (int)"
        ]
        self.param_keys = ['num_families', 'r_bar', 'r_hat', 'max_vision', 'crisis_period', 'world_width', 'world_height']
        self.selected_index = 0
        self.editing = False
        self.edit_buffer = ""
        self.running = True

    def draw(self):
        self.screen.fill((0, 0, 0))
        title = self.font.render("CONFIGURATION MENU - Press ENTER to edit, ESC to cancel, S to START", True, COLOR_TEXT)
        self.screen.blit(title, (50, 20))

        y = 80
        for i, (name, key) in enumerate(zip(self.param_names, self.param_keys)):
            value = self.params[key]
            if isinstance(value, float):
                display_value = f"{value:.1f}"
            else:
                display_value = str(value)
            if self.selected_index == i and not self.editing:
                color = COLOR_MENU_SELECT
                prefix = "> "
            else:
                color = COLOR_TEXT
                prefix = "  "
            text = self.font.render(f"{prefix}{name}: {display_value}", True, color)
            self.screen.blit(text, (50, y))
            y += 35

        if self.editing:
            edit_text = self.font.render(f"Enter new value: {self.edit_buffer}_", True, COLOR_TEXT)
            pygame.draw.rect(self.screen, COLOR_INPUT_BG, (50, y, 400, 30))
            self.screen.blit(edit_text, (55, y+5))

        start_text = self.font.render("Press S to START simulation", True, COLOR_TEXT)
        self.screen.blit(start_text, (50, y + 60))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.editing:
                if event.key == pygame.K_RETURN:
                    try:
                        key = self.param_keys[self.selected_index]
                        if key in ['num_families', 'max_vision', 'crisis_period', 'world_width', 'world_height']:
                            val = int(self.edit_buffer)
                        else:
                            val = float(self.edit_buffer)
                        self.params[key] = val
                    except ValueError:
                        pass
                    self.editing = False
                    self.edit_buffer = ""
                elif event.key == pygame.K_ESCAPE:
                    self.editing = False
                    self.edit_buffer = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.edit_buffer = self.edit_buffer[:-1]
                else:
                    char = event.unicode
                    if char.isdigit() or char == '.' or char == '-':
                        self.edit_buffer += char
            else:
                if event.key == pygame.K_UP:
                    self.selected_index = (self.selected_index - 1) % len(self.param_keys)
                elif event.key == pygame.K_DOWN:
                    self.selected_index = (self.selected_index + 1) % len(self.param_keys)
                elif event.key == pygame.K_RETURN:
                    self.editing = True
                    self.edit_buffer = str(self.params[self.param_keys[self.selected_index]])
                elif event.key == pygame.K_s or event.key == pygame.K_S:
                    self.running = False

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
        return self.params


# ====================== ОТРИСОВКА СИМУЛЯЦИИ ======================
def draw_simulation(screen, world, font, speed, paused):
    panel = pygame.Rect(WINDOW_WIDTH, 0, INFO_PANEL_WIDTH, SCREEN_HEIGHT)
    pygame.draw.rect(screen, COLOR_PANEL, panel)
    y = 10
    avg_res = np.mean(world.resource) if len(world.resource) > 0 else 0

    lines = [
        f"TIME: {world.time}",
        f"POPULATION: {world.get_pop()}",
        f"PHASE: {world.global_phase}",
        f"AVG RESOURCE: {avg_res:.1f}",
        f"AVG CAPITAL: {world.cap_hist[-1] if world.cap_hist else 0:.0f}",
        f"WORKING WOMEN: {int(world.work_hist[-1]*100) if world.work_hist else 0}%",
        "",
        f"FIELD: {world.w}×{world.h}",
        f"FAMILIES: {world.num_families}",
        f"R_BAR: {world.config['r_bar']:.0f}",
        f"R_HAT: {world.config['r_hat']:.0f}",
        f"VISION: {world.config['max_vision']}",
        f"CRISIS PERIOD: {world.config['crisis_period']}",
        "",
        f"SPEED: {speed}x",
        "",
        "SPACE - pause",
        "UP/DOWN - speed",
        "R - reset (config)",
        "ESC - quit"
    ]
    for line in lines:
        surf = font.render(line, True, COLOR_TEXT)
        screen.blit(surf, (WINDOW_WIDTH + 10, y))
        y += 24

    # График популяции
    if len(world.pop_hist) > 5:
        gx, gy = WINDOW_WIDTH + 10, y + 10
        gw, gh = INFO_PANEL_WIDTH - 20, 100
        pygame.draw.rect(screen, (20, 20, 30), (gx, gy, gw, gh))
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
            pygame.draw.lines(screen, (100, 200, 255), False, points, 2)


def draw_world(screen, world):
    for x in range(world.w):
        for y in range(world.h):
            val = world.resource[x, y]
            t = (val - RESOURCE_BASE * 0.2) / (RESOURCE_BASE * 4.0)
            t = max(0, min(1, t))
            color = (
                int(COLOR_RESOURCE_LOW[0] + t * (COLOR_RESOURCE_HIGH[0] - COLOR_RESOURCE_LOW[0])),
                int(COLOR_RESOURCE_LOW[1] + t * (COLOR_RESOURCE_HIGH[1] - COLOR_RESOURCE_LOW[1])),
                int(COLOR_RESOURCE_LOW[2] + t * (COLOR_RESOURCE_HIGH[2] - COLOR_RESOURCE_LOW[2]))
            )
            pygame.draw.rect(screen, color, (x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE))

    for f in world.families:
        rect = (f.x*CELL_SIZE, f.y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, f.get_color(), rect)
        pygame.draw.rect(screen, COLOR_OUTLINE, rect, 2)
        if f.capital > 600:
            center = (f.x*CELL_SIZE + CELL_SIZE//2, f.y*CELL_SIZE + CELL_SIZE//2)
            pygame.draw.circle(screen, (255, 255, 200), center, 3)


# ====================== ГЛАВНАЯ ФУНКЦИЯ ======================
def main():
    pygame.init()
    global WINDOW_WIDTH, WINDOW_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT

    # Временные размеры
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    SCREEN_WIDTH = WINDOW_WIDTH + INFO_PANEL_WIDTH
    SCREEN_HEIGHT = WINDOW_HEIGHT

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Family Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 14)

    # При первом запуске показать меню
    menu = ConfigMenu(screen, font)
    params = menu.run()

    # Применить параметры
    WORLD_WIDTH = params['world_width']
    WORLD_HEIGHT = params['world_height']
    WINDOW_WIDTH = WORLD_WIDTH * CELL_SIZE
    WINDOW_HEIGHT = WORLD_HEIGHT * CELL_SIZE
    SCREEN_WIDTH = WINDOW_WIDTH + INFO_PANEL_WIDTH
    SCREEN_HEIGHT = WINDOW_HEIGHT
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)

    # Создать мир
    config = {
        'r_bar': params['r_bar'],
        'r_hat': params['r_hat'],
        'max_vision': params['max_vision'],
        'crisis_period': params['crisis_period']
    }
    world = World(WORLD_WIDTH, WORLD_HEIGHT, params['num_families'], config)

    paused = False
    speed = 1
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    speed = min(10, speed + 1)
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - 1)
                elif event.key == pygame.K_r:
                    # Показать меню с текущими параметрами
                    menu.params = {
                        'num_families': world.num_families,
                        'r_bar': world.config['r_bar'],
                        'r_hat': world.config['r_hat'],
                        'max_vision': world.config['max_vision'],
                        'crisis_period': world.config['crisis_period'],
                        'world_width': world.w,
                        'world_height': world.h
                    }
                    menu.running = True
                    menu.selected_index = 0
                    menu.editing = False
                    new_params = menu.run()
                    if new_params:
                        WORLD_WIDTH = new_params['world_width']
                        WORLD_HEIGHT = new_params['world_height']
                        WINDOW_WIDTH = WORLD_WIDTH * CELL_SIZE
                        WINDOW_HEIGHT = WORLD_HEIGHT * CELL_SIZE
                        SCREEN_WIDTH = WINDOW_WIDTH + INFO_PANEL_WIDTH
                        SCREEN_HEIGHT = WINDOW_HEIGHT
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                        config = {
                            'r_bar': new_params['r_bar'],
                            'r_hat': new_params['r_hat'],
                            'max_vision': new_params['max_vision'],
                            'crisis_period': new_params['crisis_period']
                        }
                        world = World(WORLD_WIDTH, WORLD_HEIGHT, new_params['num_families'], config)
                        paused = False

        if not paused:
            for _ in range(speed):
                world.step()
                if world.get_pop() == 0 and world.time > 100:
                    paused = True

        draw_world(screen, world)
        draw_simulation(screen, world, font, speed, paused)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()