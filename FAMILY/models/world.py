import numpy as np
import random
from collections import deque
from config import (
    RESOURCE_BASE, DELTA_BOOM, DELTA_CRISIS, MOVE_PROB, CRIS_PERIOD
)
from .family import Family


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
                self.resource[f.x, f.y] -= 0.5

        # Восстановление
        self.resource += 0.2 * (RESOURCE_BASE - self.resource) / 10.0

        # Диффузия (каждый шаг, векторизовано)
        diffused = self.resource.copy()
        diffused[1:-1, 1:-1] += 0.1 * (
            (self.resource[0:-2, 1:-1] + self.resource[2:, 1:-1] +
             self.resource[1:-1, 0:-2] + self.resource[1:-1, 2:]) / 4.0 -
            self.resource[1:-1, 1:-1]
        )
        self.resource = diffused
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 3.0)

    def apply_global_phase(self):
        if self.is_crisis:
            self.resource *= DELTA_CRISIS + 1
        else:
            self.resource *= DELTA_BOOM + 1
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 5.0)

    def step(self):
        self.time += 1

        if self.time >= self.next_phase_change:
            self.is_crisis = not self.is_crisis
            self.next_phase_change = self.time + CRIS_PERIOD
            self.apply_global_phase()

        self.update_resource_local()

        # Движение семей
        for f in self.families:
            if not f.alive:
                continue
            if random.random() < MOVE_PROB:
                best_val = self.resource[f.x, f.y]
                best_pos = (f.x, f.y)
                for dx in range(-self.max_vision, self.max_vision + 1):
                    for dy in range(-self.max_vision, self.max_vision + 1):
                        nx, ny = f.x + dx, f.y + dy
                        if 0 <= nx < self.w and 0 <= ny < self.h:
                            occupied = any(f2.x == nx and f2.y == ny and f2.alive and f2 != f for f2 in self.families)
                            if not occupied and self.resource[nx, ny] > best_val:
                                best_val = self.resource[nx, ny]
                                best_pos = (nx, ny)
                if best_pos != (f.x, f.y):
                    dx = np.sign(best_pos[0] - f.x)
                    dy = np.sign(best_pos[1] - f.y)
                    new_x = f.x + dx
                    new_y = f.y + dy
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