# models/family.py
import random
import numpy as np
from config import (
    BOARD_RET, BOARD_SOG, MALE_INCOME_BASE, FEMALE_INCOME_BASE,
    EXPENDITURE_BASE, INIT_CAPITAL_MEAN, INIT_CAPITAL_STD,
    INIT_ADAPT_MEAN, INIT_ADAPT_STD, INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD,
    EXPENDITURE_MIN, EXPENDITURE_MAX
)


class Woman:
    def __init__(self):
        self.works = False
        self.income = 0.0

    def update(self, family_capital, adaptation):
        if not self.works:
            an = adaptation / 100
            if family_capital < an * BOARD_RET:
                self.works = True
                self.income = FEMALE_INCOME_BASE
            elif family_capital < BOARD_SOG:
                self.works = True
                self.income = FEMALE_INCOME_BASE
        else:
            an = adaptation / 100
            if  family_capital > an * BOARD_RET * 5:
                if random.random() < 0.25:
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
        self.expenditure_rate = EXPENDITURE_BASE
        self.alive = True
        # Счётчики для последовательного применения стратегий
        self.steps_low_capital = 0      # сколько шагов капитал ниже порога
        self.steps_reduced_expenses = 0 # сколько шагов после снижения расходов

    def update(self, cell_resource, is_crisis):
        if not self.alive:
            return

        # Предварительный расчёт нового капитала (до применения стратегий)
        male_income = self.man.income * cell_resource
        female_income = self.woman.income * cell_resource
        total_income = male_income + female_income
        spend = self.expenditure_rate * self.capital
        new_capital = self.capital - spend + total_income

        if new_capital <= 0:
            self.alive = False
            return

        an = self.adaptation / 100
        sn = self.tolerance / 100
        
        # Порог кризиса
        crisis_threshold = an * BOARD_RET
        
        # Обновляем счётчик шагов с низким капиталом
        if new_capital < crisis_threshold:
            self.steps_low_capital += 1
        else:
            self.steps_low_capital = 0
            self.steps_reduced_expenses = 0

        # ===== СТРАТЕГИЯ 1: ДВИЖЕНИЕ (в world.step, не здесь) =====
        
        # ===== СТРАТЕГИЯ 2: СНИЖЕНИЕ РАСХОДОВ (после 10 шагов низкого капитала) =====
        if self.steps_low_capital > 10:
            if self.expenditure_rate > EXPENDITURE_MIN:
                self.expenditure_rate = max(EXPENDITURE_MIN, self.expenditure_rate * 0.97)
                self.steps_reduced_expenses += 1
        
        # ===== СТРАТЕГИЯ 3: ВЫХОД ЖЕНЩИНЫ НА РАБОТУ (после снижения расходов) =====
        # Если после снижения расходов прошло ещё 5 шагов, а капитал всё ещё низкий
        if self.steps_reduced_expenses > 5:
            if not self.woman.works:
                if is_crisis and new_capital < crisis_threshold:
                    self.woman.works = True
                    self.woman.income = FEMALE_INCOME_BASE
                elif new_capital < BOARD_SOG:
                    self.woman.works = True
                    self.woman.income = FEMALE_INCOME_BASE

        # ===== СТРАТЕГИЯ 4: УВОЛЬНЕНИЕ ЖЕНЩИНЫ =====
        else:
            if not is_crisis and new_capital > an * BOARD_RET * 5:
                if random.random() < 0.02:
                    self.woman.works = False
                    self.woman.income = 0.0
                    self.steps_low_capital = 0
                    self.steps_reduced_expenses = 0

        # ===== СТРАТЕГИЯ 5: УВЕЛИЧЕНИЕ РАСХОДОВ (при высоком капитале) =====
        if new_capital > sn * an * BOARD_RET * 5:
            if self.expenditure_rate < EXPENDITURE_MAX:
                self.expenditure_rate = min(EXPENDITURE_MAX, self.expenditure_rate * 1.02)

        # Применяем новый капитал
        self.capital = new_capital

        # Динамика адаптивности и толерантности
        if is_crisis:
            self.adaptation = min(100.0, self.adaptation + 0.5)
            self.tolerance = max(0.0, self.tolerance - 0.3)
        else:
            self.adaptation = max(0.0, self.adaptation - 0.2)
            self.tolerance = min(100.0, self.tolerance + 0.2)

        # Распад семьи при остром кризисе
        if self.capital < BOARD_SOG and self.woman.works:
            if random.random() < 0.1:
                self.alive = False

    def is_both_working(self):
        return self.woman.works

    def get_color(self):
        from colors import COLOR_FAMILY_BOTH, COLOR_FAMILY_MALE_ONLY
        if self.is_both_working():
            return COLOR_FAMILY_BOTH
        return COLOR_FAMILY_MALE_ONLY