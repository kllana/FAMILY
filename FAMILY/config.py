# config.py
# Размеры окна
CELL_SIZE = 8
INFO_PANEL_WIDTH = 280

# Параметры модели
NUM_FAMILIES = 50
BOARD_RET = 180.0
BOARD_SOG = 30.0
BOARD_ADAPT = 100.0
MAX_VISION = 2
CRIS_PERIOD = 400
WORLD_WIDTH = 85
WORLD_HEIGHT = 85

# Доходы и расходы
MALE_INCOME_BASE = 5.0
FEMALE_INCOME_BASE = 4.0
EXPENDITURE_BASE = 0.80

# Начальный капитал и адаптивность
INIT_CAPITAL_MEAN = 190.0
INIT_CAPITAL_STD = 80.0
INIT_ADAPT_MEAN = 50.0
INIT_ADAPT_STD = 15.0
INIT_TOLERANCE_MEAN = 50.0
INIT_TOLERANCE_STD = 15.0

# Ресурс и циклы (аддитивные)
RESOURCE_BASE = 22.0
GLOBAL_BOOM_INCREMENT = 0.15
GLOBAL_CRISIS_DECREMENT = -0.20

# Локальная вариация (умеренная)
LOCAL_VARIATION_AMPLITUDE = 12.0      # была 40, теперь 12
CONSUMPTION_RATE = 0.5                # вернули к умеренному
RENEWAL_RATE = 0.005                  # очень медленное восстановление (было 0)
DIFFUSION_RATE = 0.03                 # слабая диффузия (было 0)

# Движение
MOVE_PROB = 0.5

# Рождаемость
BIRTH_BASE_PROB = 0.003
BIRTH_BOOM_MULTIPLIER = 4.0
BIRTH_MIN_CAPITAL = 150.0
BIRTH_MAX_FAMILIES = 200

# Границы расходов
EXPENDITURE_MIN = 0.10
EXPENDITURE_MAX = 0.35

# Шаги для счётчиков
STEPS_BEFORE_REDUCE_EXPENSES = 10
STEPS_BEFORE_WOMAN_WORK = 5