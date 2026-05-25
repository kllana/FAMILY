# models/world.py
import numpy as np
import random
from collections import deque
from config import (
    RESOURCE_BASE, GLOBAL_BOOM_INCREMENT, GLOBAL_CRISIS_DECREMENT,
    MOVE_PROB, CRIS_PERIOD,
    BOARD_RET, BIRTH_BASE_PROB, BIRTH_BOOM_MULTIPLIER, BIRTH_MIN_CAPITAL,
    BIRTH_MAX_FAMILIES, INIT_CAPITAL_MEAN, INIT_CAPITAL_STD,
    INIT_ADAPT_MEAN, INIT_ADAPT_STD, INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD,
    LOCAL_VARIATION_AMPLITUDE,   # <-- добавьте это
    CONSUMPTION_RATE, RENEWAL_RATE, DIFFUSION_RATE,
    EXPENDITURE_MIN, EXPENDITURE_MAX,
    STEPS_BEFORE_REDUCE_EXPENSES, STEPS_BEFORE_WOMAN_WORK
)
from .family import Family


class World:
    def __init__(self, w, h, num_families, max_vision):
        self.w = w
        self.h = h
        self.num_families = num_families
        self.max_vision = max_vision
    
        self.base_resource = RESOURCE_BASE
        # Увеличиваем амплитуду локальных вариаций
        self.resource_variation = np.random.uniform(-LOCAL_VARIATION_AMPLITUDE, LOCAL_VARIATION_AMPLITUDE, (w, h))
        self.resource = self.base_resource + self.resource_variation
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.2, RESOURCE_BASE * 2.0)
        
        # Создаём список всех клеток
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
        # Потребление (уменьшаем локальную вариацию)
        for f in self.families:
            if f.alive:
                self.resource_variation[f.x, f.y] -= CONSUMPTION_RATE
                # Ограничиваем минимальное значение
                self.resource_variation[f.x, f.y] = max(-RESOURCE_BASE * 0.8, self.resource_variation[f.x, f.y])
    
        # Восстановление вариации отключено (RENEWAL_RATE = 0)
        if RENEWAL_RATE > 0:
            self.resource_variation *= (1 - RENEWAL_RATE)
    
        # Диффузия отключена (DIFFUSION_RATE = 0)
        if DIFFUSION_RATE > 0 and self.step_counter % 5 == 0:
            diffused = self.resource_variation.copy()
            diffused[1:-1, 1:-1] += DIFFUSION_RATE * (
                (self.resource_variation[0:-2, 1:-1] + self.resource_variation[2:, 1:-1] +
                 self.resource_variation[1:-1, 0:-2] + self.resource_variation[1:-1, 2:]) / 4.0 -
                self.resource_variation[1:-1, 1:-1]
            )
            self.resource_variation = diffused
    
        # Пересчитываем итоговый ресурс
        self.resource = self.base_resource + self.resource_variation
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 5.0)

    def apply_global_phase(self):
        # Меняем только базовый уровень
        if self.is_crisis:
            self.base_resource += GLOBAL_CRISIS_DECREMENT
        else:
            self.base_resource += GLOBAL_BOOM_INCREMENT
        
        # Ограничиваем базовый уровень
        self.base_resource = max(RESOURCE_BASE * 0.1, min(RESOURCE_BASE * 5.0, self.base_resource))
        
        # Пересчитываем ресурс клеток
        self.resource = self.base_resource + self.resource_variation
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 5.0)

    def step(self):
        self.step_counter += 1
        self.time += 1
        
        # Глобальное изменение ресурса
        self.apply_global_phase()
        
        # Смена фазы
        if self.time >= self.next_phase_change:
            self.is_crisis = not self.is_crisis
            self.next_phase_change = self.time + CRIS_PERIOD
            print(f"Фаза изменена на {'КРИЗИС' if self.is_crisis else 'ПОДЪЁМ'}")
        
        # Локальная динамика
        self.update_resource_local()
        
        # ===== СТРАТЕГИЯ 1: ДВИЖЕНИЕ (только при низком капитале) =====
        for f in self.families:
            if not f.alive:
                continue
            an = f.adaptation / 100
            crisis_threshold = an * BOARD_RET
            if f.capital < crisis_threshold:
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
        
        # ===== СТРАТЕГИИ 2-5: ОБНОВЛЕНИЕ СЕМЕЙ =====
        for f in self.families[:]:
            if f.alive:
                f.update(self.resource[f.x, f.y], self.is_crisis)
            if not f.alive:
                self.families.remove(f)
        
        # ===== РОЖДАЕМОСТЬ =====
        avg_capital = self.get_avg_capital()
        if len(self.families) < BIRTH_MAX_FAMILIES:
            birth_prob = BIRTH_BASE_PROB
            if not self.is_crisis:
                birth_prob *= BIRTH_BOOM_MULTIPLIER
                if avg_capital > BIRTH_MIN_CAPITAL:
                    birth_prob *= 1.5
            
            if random.random() < birth_prob:
                free_cells = [(x, y) for x in range(self.w) for y in range(self.h)
                              if not any(f.x == x and f.y == y for f in self.families)]
                if free_cells:
                    x, y = random.choice(free_cells)
                    new_id = max([f.id for f in self.families] + [0]) + 1
                    new_family = Family(x, y, new_id)
                    new_family.capital = max(30.0, np.random.normal(INIT_CAPITAL_MEAN, INIT_CAPITAL_STD))
                    new_family.adaptation = max(0.0, np.random.normal(INIT_ADAPT_MEAN, INIT_ADAPT_STD))
                    new_family.tolerance = max(0.0, np.random.normal(INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD))
                    # Новая семья — женщина не работает (как в книге)
                    new_family.woman.works = False
                    new_family.woman.income = 0.0
                    self.families.append(new_family)
        
        # ===== СМЕРТНОСТЬ В КРИЗИС =====
        if self.is_crisis:
            for f in self.families[:]:
                if f.alive and random.random() < 0.005:   # 0.5% (было 1%)
                    if f.capital < 30:                     # порог 30 (было 50)
                        f.alive = False
                        self.families.remove(f)
        
        # ===== СБОР СТАТИСТИКИ =====
        self.pop_hist.append(self.get_population())
        self.cap_hist.append(self.get_avg_capital())
        self.work_hist.append(self.get_working_ratio())