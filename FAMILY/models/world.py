import numpy as np
import random
from collections import deque
from config import (
    RESOURCE_BASE, GLOBAL_BOOM_INCREMENT, GLOBAL_CRISIS_DECREMENT,
    MOVE_PROB, CRIS_PERIOD,
    BOARD_RET, BOARD_SOG,
    BIRTH_BASE_PROB, BIRTH_BOOM_MULTIPLIER, BIRTH_MIN_CAPITAL,
    BIRTH_MAX_FAMILIES, INIT_CAPITAL_MEAN, INIT_CAPITAL_STD,
    INIT_ADAPT_MEAN, INIT_ADAPT_STD, INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD,
    LOCAL_VARIATION_AMPLITUDE, CONSUMPTION_RATE, RENEWAL_RATE, DIFFUSION_RATE,
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
        self.config = {
            'boardRet': BOARD_RET,
            'boardSog': BOARD_SOG,
            'cris': CRIS_PERIOD
        }

        self.base_resource = RESOURCE_BASE
        self.resource_variation = np.random.uniform(-LOCAL_VARIATION_AMPLITUDE, LOCAL_VARIATION_AMPLITUDE, (w, h))
        self.resource = self.base_resource + self.resource_variation
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.2, RESOURCE_BASE * 2.0)

        all_cells = [(x, y) for x in range(w) for y in range(h)]
        random.shuffle(all_cells)

        self.families = []
        for i in range(min(num_families, len(all_cells))):
            x, y = all_cells[i]
            new_family = Family(x, y, i)
            new_family.capital = max(30.0, np.random.normal(INIT_CAPITAL_MEAN, INIT_CAPITAL_STD))
            new_family.adaptation = max(0.0, np.random.normal(INIT_ADAPT_MEAN, INIT_ADAPT_STD))
            new_family.tolerance = max(0.0, np.random.normal(INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD))
            self.families.append(new_family)

        self.time = 0
        self.next_phase_change = CRIS_PERIOD
        self.is_crisis = False
        self.pop_hist = deque(maxlen=2000)
        self.cap_hist = deque(maxlen=2000)
        self.work_hist = deque(maxlen=2000)
        self.step_counter = 0

    def get_avg_resource(self):
        """Актуальное среднее значение ресурса"""
        return np.mean(self.resource) if len(self.resource) > 0 else 0

    def get_population(self):
        """Актуальное количество семей"""
        return len([f for f in self.families if f.alive])

    def get_avg_capital(self):
        """Актуальный средний капитал"""
        alive = [f for f in self.families if f.alive]
        return np.mean([f.capital for f in alive]) if alive else 0

    def get_working_ratio(self):
        """Актуальное соотношение работающих"""
        alive = [f for f in self.families if f.alive]
        if not alive:
            return 0
        return sum(1 for f in alive if f.is_both_working()) / len(alive)

    def update_resource_local(self):
        """Обновление ресурсов с учетом потребления и диффузии"""
        alive_mask = np.zeros((self.w, self.h), dtype=bool)
        for f in self.families:
            if f.alive:
                alive_mask[f.x, f.y] = True
        
        self.resource_variation[alive_mask] -= CONSUMPTION_RATE
        self.resource_variation = np.maximum(-RESOURCE_BASE * 0.8, self.resource_variation)

        if RENEWAL_RATE > 0:
            self.resource_variation *= (1 - RENEWAL_RATE)

        if DIFFUSION_RATE > 0 and self.step_counter % 5 == 0:
            variation_copy = self.resource_variation.copy()
            variation_copy[1:-1, 1:-1] += DIFFUSION_RATE * (
                (self.resource_variation[0:-2, 1:-1] + self.resource_variation[2:, 1:-1] +
                 self.resource_variation[1:-1, 0:-2] + self.resource_variation[1:-1, 2:]) / 4.0 -
                self.resource_variation[1:-1, 1:-1]
            )
            self.resource_variation = variation_copy

        self.resource = self.base_resource + self.resource_variation
        self.resource = np.clip(self.resource, RESOURCE_BASE * 0.1, RESOURCE_BASE * 5.0)

    def apply_global_phase(self):
        """Применение глобальной фазы (бум/кризис)"""
        if self.is_crisis:
            self.base_resource += GLOBAL_CRISIS_DECREMENT
        else:
            self.base_resource += GLOBAL_BOOM_INCREMENT

        self.base_resource = max(RESOURCE_BASE * 0.1, min(RESOURCE_BASE * 5.0, self.base_resource))

    def move_families(self):
        """Перемещение семей в поисках лучших ресурсов"""
        w, h = self.w, self.h
        res = self.resource
        
        for f in self.families:
            if not f.alive:
                continue
            
            an = f.adaptation / 100
            crisis_threshold = an * BOARD_RET
            
            if f.capital < crisis_threshold:
                if random.random() < MOVE_PROB:
                    best_val = res[f.x, f.y]
                    best_pos = (f.x, f.y)
                   
                    for dx in range(-self.max_vision, self.max_vision + 1):
                        for dy in range(-self.max_vision, self.max_vision + 1):
                            nx, ny = f.x + dx, f.y + dy
                            if 0 <= nx < w and 0 <= ny < h:
                                occupied = False
                                for f2 in self.families:
                                    if f2.alive and f2 != f and f2.x == nx and f2.y == ny:
                                        occupied = True
                                        break
                                if not occupied and res[nx, ny] > best_val:
                                    best_val = res[nx, ny]
                                    best_pos = (nx, ny)
                    
                    if best_pos != (f.x, f.y):
                        dx = np.sign(best_pos[0] - f.x)
                        dy = np.sign(best_pos[1] - f.y)
                        new_x = f.x + dx
                        new_y = f.y + dy
                        
                        occupied = False
                        for f2 in self.families:
                            if f2.alive and f2 != f and f2.x == new_x and f2.y == new_y:
                                occupied = True
                                break
                        
                        if 0 <= new_x < w and 0 <= new_y < h and not occupied:
                            f.x, f.y = new_x, new_y

    def update_families(self):
        """Обновление состояния всех семей"""
        for f in self.families:
            if f.alive:
                f.update(self.resource[f.x, f.y], self.is_crisis)

    def birth_new_family(self):
        """Попытка создать новую семью"""
        if len(self.families) >= BIRTH_MAX_FAMILIES:
            return
        
        avg_capital = self.get_avg_capital()
        birth_prob = BIRTH_BASE_PROB
        
        if not self.is_crisis:
            birth_prob *= BIRTH_BOOM_MULTIPLIER
            if avg_capital > BIRTH_MIN_CAPITAL:
                birth_prob *= 1.5
        
        if random.random() >= birth_prob:
            return
        
        occupied = {(f.x, f.y) for f in self.families if f.alive}
        free_cells = [(x, y) for x in range(self.w) for y in range(self.h) 
                     if (x, y) not in occupied]
        
        if not free_cells:
            return
        
        x, y = random.choice(free_cells)
        new_id = max([f.id for f in self.families] + [0]) + 1
        new_family = Family(x, y, new_id)
        
        new_family.capital = max(30.0, np.random.normal(INIT_CAPITAL_MEAN, INIT_CAPITAL_STD))
        new_family.adaptation = max(0.0, np.random.normal(INIT_ADAPT_MEAN, INIT_ADAPT_STD))
        new_family.tolerance = max(0.0, np.random.normal(INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD))
        new_family.woman.works = False
        new_family.woman.income = 0.0
        
        self.families.append(new_family)

    def apply_crisis_mortality(self):
        """Применение повышенной смертности во время кризиса"""
        if not self.is_crisis:
            return
        
        to_remove = []
        for f in self.families:
            if f.alive and random.random() < 0.003 and f.capital < 30:
                to_remove.append(f)
        
        for f in to_remove:
            if f in self.families:
                self.families.remove(f)

    def step(self):
        """Основной шаг симуляции"""
        self.step_counter += 1
        self.time += 1
        
        self.apply_global_phase()
        
        if self.time >= self.next_phase_change:
            self.is_crisis = not self.is_crisis
            self.next_phase_change = self.time + CRIS_PERIOD
        
        self.update_resource_local()
        
        self.move_families()
        
        self.update_families()
        
        self.families = [f for f in self.families if f.alive]
        
        self.birth_new_family()
        
        self.apply_crisis_mortality()
        
        self.pop_hist.append(self.get_population())
        self.cap_hist.append(self.get_avg_capital())
        self.work_hist.append(self.get_working_ratio())
    
    def get_statistics(self):
        """Получение текущей статистики"""
        return {
            'time': self.time,
            'population': self.get_population(),
            'avg_capital': self.get_avg_capital(),
            'working_ratio': self.get_working_ratio(),
            'avg_resource': self.get_avg_resource(),
            'is_crisis': self.is_crisis,
            'base_resource': self.base_resource
        }
    
    def reset(self):
        """Сброс мира до начального состояния (для отладки)"""
        self.__init__(self.w, self.h, self.num_families, self.max_vision)