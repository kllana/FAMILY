#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import numpy as np
import random
from collections import deque

# ====================== ПАРАМЕТРЫ ======================
WORLD_WIDTH = 40
WORLD_HEIGHT = 30
CELL_SIZE = 18
WINDOW_WIDTH = WORLD_WIDTH * CELL_SIZE
WINDOW_HEIGHT = WORLD_HEIGHT * CELL_SIZE
INFO_PANEL_WIDTH = 280
SCREEN_WIDTH = WINDOW_WIDTH + INFO_PANEL_WIDTH
SCREEN_HEIGHT = WINDOW_HEIGHT

NUM_FAMILIES = 40

# Доходы и расходы (трудная жизнь)
MALE_INCOME_BASE = 6
FEMALE_INCOME_BASE = 5
EXPENDITURE_BASE = 0.1

INIT_CAPITAL_MEAN = 300.0
INIT_CAPITAL_STD = 80.0

INIT_ADAPT_MEAN = 50.0
INIT_ADAPT_STD = 15.0
INIT_TOLERANCE_MEAN = 50.0
INIT_TOLERANCE_STD = 15.0
A_MAX = 100.0
S_MAX = 100.0

INIT_WORKING_PROB = 0.3

R_BAR = 150.0
R_HAT = 40.0
R_MAX = 800.0
EXPENDITURE_MIN = 0.10
EXPENDITURE_MAX = 0.35

BIRTH_RATE_BASE = 0.02
DEATH_RATE_BASE = 0.01
CRISIS_DEATH_BONUS = 0.03

# Локальная динамика ресурса
RESOURCE_BASE = 15.0
RESOURCE_CONSUMPTION = 3.0
RESOURCE_RENEWAL = 0.2
RESOURCE_DIFFUSION = 0.1

# Глобальные циклы
CRISIS_PERIOD = 200
BOOM_FACTOR = 1.3
CRISIS_FACTOR = 0.3

# ДВИЖЕНИЕ (исправлено: теперь пошаговое, а не телепортация)
MAX_VISION = 4           # радиус, в котором семья ищет лучшую клетку
MOVE_PROB = 0.3          # вероятность попытаться переместиться (было 0.7)

# Цвета
COLOR_RESOURCE_LOW = (0, 60, 0)
COLOR_RESOURCE_HIGH = (80, 180, 80)
COLOR_FAMILY_MALE = (220, 50, 50)
COLOR_FAMILY_BOTH = (50, 220, 50)
COLOR_OUTLINE = (0, 0, 0)
COLOR_TEXT = (255, 255, 255)


class Family:
    def __init__(self, x, y, fid):
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

        if self.capital < an * R_BAR:
            if self.woman_works == 0:
                self.woman_works = 1
                self.female_income = FEMALE_INCOME_BASE
                self.adaptation = min(A_MAX, self.adaptation + 2)

        elif self.capital < sn * an * R_BAR:
            self.expenditure_rate = max(EXPENDITURE_MIN, self.expenditure_rate * 0.97)

        elif self.capital > sn * an * R_MAX:
            if self.woman_works == 1 and random.random() < 0.02:
                self.woman_works = 0
                self.female_income = 0.0
            self.expenditure_rate = min(EXPENDITURE_MAX, self.expenditure_rate * 1.02)

        if self.capital < R_HAT:
            if random.random() < 0.15:
                self.alive = False
                return

        self.capital = min(self.capital, R_MAX * 2)

        if self.capital < R_BAR:
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
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.resource = np.ones((w, h)) * RESOURCE_BASE
        self.resource += np.random.uniform(-8, 8, (w, h))
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.2, RESOURCE_BASE * 2.0)

        all_cells = [(x, y) for x in range(w) for y in range(h)]
        random.shuffle(all_cells)
        self.families = []
        for i in range(min(NUM_FAMILIES, len(all_cells))):
            x, y = all_cells[i]
            self.families.append(Family(x, y, i))

        self.time = 0
        self.next_phase_change = CRISIS_PERIOD
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
        """Находит лучшую СОСЕДНЮЮ клетку (на расстоянии 1) в пределах радиуса видимости.
           Возвращает направление (dx, dy) или (0,0) если оставаться на месте."""
        current_val = self.resource[fx, fy]
        best_dx, best_dy = 0, 0
        best_val = current_val

        # Смотрим все клетки в радиусе видимости, но перемещаемся только на 1 клетку
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = fx + dx, fy + dy
                if 0 <= nx < self.w and 0 <= ny < self.h:
                    if abs(dx) + abs(dy) == 1:  # ТОЛЬКО СОСЕДНИЕ КЛЕТКИ (4 направления)
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

        # Смена глобальной фазы
        if self.time >= self.next_phase_change:
            self.global_phase = 'CRISIS' if self.global_phase == 'BOOM' else 'BOOM'
            self.next_phase_change = self.time + CRISIS_PERIOD
            self.apply_global_phase()

        # Локальная динамика ресурса
        self.update_resource_local()

        # Движение семей (ПОШАГОВОЕ: только на соседнюю клетку)
        for f in self.families:
            if not f.alive:
                continue
            if random.random() < MOVE_PROB:
                dx, dy = self.get_best_neighbor(f.x, f.y, MAX_VISION, f)
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
        if self.global_phase == 'BOOM' and avg_capital > 200:
            birth_chance = BIRTH_RATE_BASE * 2
        elif self.global_phase == 'CRISIS':
            birth_chance = BIRTH_RATE_BASE * 0.3

        if random.random() < birth_chance:
            free = self.find_free_cell()
            if free:
                new_id = max([f.id for f in self.families] + [0]) + 1
                self.families.append(Family(free[0], free[1], new_id))

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


def draw(screen, world, font, paused, speed):
    # Фон ресурса
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

    # Семьи
    for f in world.families:
        rect = (f.x*CELL_SIZE, f.y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, f.get_color(), rect)
        pygame.draw.rect(screen, COLOR_OUTLINE, rect, 2)
        if f.capital > 500:
            center = (f.x*CELL_SIZE + CELL_SIZE//2, f.y*CELL_SIZE + CELL_SIZE//2)
            pygame.draw.circle(screen, (255, 255, 200), center, 3)

    # Инфопанель
    panel = pygame.Rect(WINDOW_WIDTH, 0, INFO_PANEL_WIDTH, SCREEN_HEIGHT)
    pygame.draw.rect(screen, (30, 30, 40), panel)
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
        f"SPEED: {speed}x",
        "",
        "SPACE - pause", "UP/DOWN - speed",
        "R - reset", "ESC - quit"
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


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Family: Slow Migration")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 14)

    world = World(WORLD_WIDTH, WORLD_HEIGHT)
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
                    world = World(WORLD_WIDTH, WORLD_HEIGHT)
                    paused = False

        if not paused:
            for _ in range(speed):
                world.step()
                if world.get_pop() == 0 and world.time > 100:
                    paused = True

        draw(screen, world, font, paused, speed)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()