import pygame
import sys
from config import (
    NUM_FAMILIES, BOARD_RET, BOARD_SOG, BOARD_ADAPT, MAX_VISION,
    CRIS_PERIOD, WORLD_WIDTH, WORLD_HEIGHT, CELL_SIZE, INFO_PANEL_WIDTH, INFO_PANEL_SCROLL_SPEED,
    MALE_INCOME_BASE, FEMALE_INCOME_BASE, EXPENDITURE_BASE,
    INIT_CAPITAL_MEAN, INIT_CAPITAL_STD, INIT_ADAPT_MEAN, INIT_ADAPT_STD,
    INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD,
    RESOURCE_BASE, GLOBAL_BOOM_INCREMENT, GLOBAL_CRISIS_DECREMENT,
    LOCAL_VARIATION_AMPLITUDE, CONSUMPTION_RATE, RENEWAL_RATE, DIFFUSION_RATE,
    MOVE_PROB, BIRTH_BASE_PROB, BIRTH_BOOM_MULTIPLIER, BIRTH_MIN_CAPITAL,
    BIRTH_MAX_FAMILIES, EXPENDITURE_MIN, EXPENDITURE_MAX,
    STEPS_BEFORE_REDUCE_EXPENSES, STEPS_BEFORE_WOMAN_WORK
)
from colors import COLOR_BG
from models import World
from ui import ConfigMenu, ModernButton, Slider, draw_world, draw_simulation
from statistics import show_statistics


def safe_quit():
    """Безопасное завершение программы"""
    pygame.quit()
    sys.exit(0)


def capture_background(screen):
    return screen.copy()


def show_family_info(family, is_crisis):
    info_width, info_height = 330, 260
    info_surface = pygame.Surface((info_width, info_height))
    info_surface.fill((30, 30, 40))
    pygame.draw.rect(info_surface, (60, 60, 70), info_surface.get_rect(), 3)
    pygame.draw.rect(info_surface, (80, 80, 100), info_surface.get_rect(), 1)

    font = pygame.font.SysFont('Segoe UI', 14)

    state_code = family.get_state(is_crisis)
    state_names = {
        1: "ПОИСК РЕСУРСА",
        2: "СНИЖЕНИЕ РАСХОДОВ",
        3: "СТАБИЛЬНОСТЬ",
        4: "БОГАТСТВО",
        5: "ГРАНЬ РАСПАДА"
    }
    state_colors = {
        1: (255, 200, 100),
        2: (255, 150, 100),
        3: (100, 200, 100),
        4: (100, 150, 255),
        5: (200, 100, 100)
    }
    state_text = state_names.get(state_code, "НЕИЗВЕСТНО")
    state_color = state_colors.get(state_code, (220, 220, 230))

    lines = [
        (f"СЕМЬЯ #{family.id}", (220, 220, 230)),
        (f"Капитал: {family.capital:.1f}", (220, 220, 230)),
        (f"Адаптивность: {family.adaptation:.1f}", (220, 220, 230)),
        (f"Толерантность: {family.tolerance:.1f}", (220, 220, 230)),
        (f"Женщина работает: {'ДА' if family.woman.works else 'НЕТ'}", (220, 220, 230)),
        (f"Коэффициент расхода: {family.expenditure_rate:.2f}", (220, 220, 230)),
        (f"СОСТОЯНИЕ:", (180, 180, 200)),
        (state_text, state_color),
    ]

    for i, (text, color) in enumerate(lines):
        surf = font.render(text, True, color)
        info_surface.blit(surf, (15, 15 + i * 25))

    screen = pygame.display.get_surface()
    screen_rect = screen.get_rect()
    info_rect = info_surface.get_rect(center=screen_rect.center)

    background = screen.copy()
    screen.blit(info_surface, info_rect)
    pygame.display.flip()

    waiting = True
    while waiting:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                safe_quit()
            if ev.type == pygame.KEYDOWN or ev.type == pygame.MOUSEBUTTONDOWN:
                waiting = False

    screen.blit(background, (0, 0))
    pygame.display.flip()


def main():
    global NUM_FAMILIES, BOARD_RET, BOARD_SOG, BOARD_ADAPT, MAX_VISION, CRIS_PERIOD, WORLD_WIDTH, WORLD_HEIGHT
    global MALE_INCOME_BASE, FEMALE_INCOME_BASE, EXPENDITURE_BASE
    global INIT_CAPITAL_MEAN, INIT_CAPITAL_STD, INIT_ADAPT_MEAN, INIT_ADAPT_STD
    global INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD
    global RESOURCE_BASE, GLOBAL_BOOM_INCREMENT, GLOBAL_CRISIS_DECREMENT
    global LOCAL_VARIATION_AMPLITUDE, CONSUMPTION_RATE, RENEWAL_RATE, DIFFUSION_RATE
    global MOVE_PROB, BIRTH_BASE_PROB, BIRTH_BOOM_MULTIPLIER, BIRTH_MIN_CAPITAL, BIRTH_MAX_FAMILIES
    global EXPENDITURE_MIN, EXPENDITURE_MAX, STEPS_BEFORE_REDUCE_EXPENSES, STEPS_BEFORE_WOMAN_WORK

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
        'worldYSize': WORLD_HEIGHT,
        'maleIncomeBase': MALE_INCOME_BASE,
        'femaleIncomeBase': FEMALE_INCOME_BASE,
        'expenditureBase': EXPENDITURE_BASE,
        'initCapitalMean': INIT_CAPITAL_MEAN,
        'initCapitalStd': INIT_CAPITAL_STD,
        'initAdaptMean': INIT_ADAPT_MEAN,
        'initAdaptStd': INIT_ADAPT_STD,
        'initToleranceMean': INIT_TOLERANCE_MEAN,
        'initToleranceStd': INIT_TOLERANCE_STD,
        'resourceBase': RESOURCE_BASE,
        'globalBoomIncrement': GLOBAL_BOOM_INCREMENT,
        'globalCrisisDecrement': abs(GLOBAL_CRISIS_DECREMENT),
        'localVariationAmplitude': LOCAL_VARIATION_AMPLITUDE,
        'consumptionRate': CONSUMPTION_RATE,
        'renewalRate': RENEWAL_RATE,
        'diffusionRate': DIFFUSION_RATE,
        'moveProb': MOVE_PROB,
        'birthBaseProb': BIRTH_BASE_PROB,
        'birthBoomMultiplier': BIRTH_BOOM_MULTIPLIER,
        'birthMinCapital': BIRTH_MIN_CAPITAL,
        'birthMaxFamilies': BIRTH_MAX_FAMILIES,
        'expenditureMin': EXPENDITURE_MIN,
        'expenditureMax': EXPENDITURE_MAX,
        'stepsBeforeReduceExpenses': STEPS_BEFORE_REDUCE_EXPENSES,
        'stepsBeforeWomanWork': STEPS_BEFORE_WOMAN_WORK
    }

    temp_world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
    temp_world.config = {'boardRet': BOARD_RET, 'boardSog': BOARD_SOG, 'cris': CRIS_PERIOD}

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

    background = capture_background(screen)
    menu = ConfigMenu(screen, font, default_params, background)
    params = menu.run()
    if params:
        NUM_FAMILIES = int(params.get('numFamily', NUM_FAMILIES))
        BOARD_RET = float(params.get('boardRet', BOARD_RET))
        BOARD_SOG = float(params.get('boardSog', BOARD_SOG))
        BOARD_ADAPT = float(params.get('boardAdapt', BOARD_ADAPT))
        MAX_VISION = int(params.get('maxVision', MAX_VISION))
        CRIS_PERIOD = int(params.get('cris', CRIS_PERIOD))
        WORLD_WIDTH = int(params.get('worldXSize', WORLD_WIDTH))
        WORLD_HEIGHT = int(params.get('worldYSize', WORLD_HEIGHT))
        
        MALE_INCOME_BASE = params.get('maleIncomeBase', MALE_INCOME_BASE)
        FEMALE_INCOME_BASE = params.get('femaleIncomeBase', FEMALE_INCOME_BASE)
        EXPENDITURE_BASE = params.get('expenditureBase', EXPENDITURE_BASE)
        INIT_CAPITAL_MEAN = params.get('initCapitalMean', INIT_CAPITAL_MEAN)
        INIT_CAPITAL_STD = params.get('initCapitalStd', INIT_CAPITAL_STD)
        INIT_ADAPT_MEAN = params.get('initAdaptMean', INIT_ADAPT_MEAN)
        INIT_ADAPT_STD = params.get('initAdaptStd', INIT_ADAPT_STD)
        INIT_TOLERANCE_MEAN = params.get('initToleranceMean', INIT_TOLERANCE_MEAN)
        INIT_TOLERANCE_STD = params.get('initToleranceStd', INIT_TOLERANCE_STD)
        RESOURCE_BASE = params.get('resourceBase', RESOURCE_BASE)
        GLOBAL_BOOM_INCREMENT = params.get('globalBoomIncrement', GLOBAL_BOOM_INCREMENT)
        GLOBAL_CRISIS_DECREMENT = -abs(params.get('globalCrisisDecrement', abs(GLOBAL_CRISIS_DECREMENT)))
        LOCAL_VARIATION_AMPLITUDE = params.get('localVariationAmplitude', LOCAL_VARIATION_AMPLITUDE)
        CONSUMPTION_RATE = params.get('consumptionRate', CONSUMPTION_RATE)
        RENEWAL_RATE = params.get('renewalRate', RENEWAL_RATE)
        DIFFUSION_RATE = params.get('diffusionRate', DIFFUSION_RATE)
        MOVE_PROB = params.get('moveProb', MOVE_PROB)
        BIRTH_BASE_PROB = params.get('birthBaseProb', BIRTH_BASE_PROB)
        BIRTH_BOOM_MULTIPLIER = params.get('birthBoomMultiplier', BIRTH_BOOM_MULTIPLIER)
        BIRTH_MIN_CAPITAL = params.get('birthMinCapital', BIRTH_MIN_CAPITAL)
        BIRTH_MAX_FAMILIES = int(params.get('birthMaxFamilies', BIRTH_MAX_FAMILIES))
        EXPENDITURE_MIN = params.get('expenditureMin', EXPENDITURE_MIN)
        EXPENDITURE_MAX = params.get('expenditureMax', EXPENDITURE_MAX)
        STEPS_BEFORE_REDUCE_EXPENSES = int(params.get('stepsBeforeReduceExpenses', STEPS_BEFORE_REDUCE_EXPENSES))
        STEPS_BEFORE_WOMAN_WORK = int(params.get('stepsBeforeWomanWork', STEPS_BEFORE_WOMAN_WORK))

    world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
    world.config = {'boardRet': BOARD_RET, 'boardSog': BOARD_SOG, 'cris': CRIS_PERIOD}
    world.next_phase_change = CRIS_PERIOD

    paused = False
    speed = 1
    running = True
    slider = Slider(0, 0, INFO_PANEL_WIDTH - 30, 12, 1, 10, speed)
    panel_scroll_y = 0
    panel_dragging_scroll = False
    thumb_rect = None
    scrollbar_rect = None

    def toggle_pause():
        nonlocal paused
        paused = not paused

    def step_once():
        nonlocal paused
        was_paused = paused
        paused = True
        world.step()
        if not was_paused:
            paused = False

    def reset_with_menu():
        nonlocal world, paused
        global NUM_FAMILIES, BOARD_RET, BOARD_SOG, BOARD_ADAPT, MAX_VISION, CRIS_PERIOD, WORLD_WIDTH, WORLD_HEIGHT
        global MALE_INCOME_BASE, FEMALE_INCOME_BASE, EXPENDITURE_BASE
        global INIT_CAPITAL_MEAN, INIT_CAPITAL_STD, INIT_ADAPT_MEAN, INIT_ADAPT_STD
        global INIT_TOLERANCE_MEAN, INIT_TOLERANCE_STD
        global RESOURCE_BASE, GLOBAL_BOOM_INCREMENT, GLOBAL_CRISIS_DECREMENT
        global LOCAL_VARIATION_AMPLITUDE, CONSUMPTION_RATE, RENEWAL_RATE, DIFFUSION_RATE
        global MOVE_PROB, BIRTH_BASE_PROB, BIRTH_BOOM_MULTIPLIER, BIRTH_MIN_CAPITAL, BIRTH_MAX_FAMILIES
        global EXPENDITURE_MIN, EXPENDITURE_MAX, STEPS_BEFORE_REDUCE_EXPENSES, STEPS_BEFORE_WOMAN_WORK
        
        current = {
            'numFamily': NUM_FAMILIES,
            'boardRet': BOARD_RET,
            'boardSog': BOARD_SOG,
            'boardAdapt': BOARD_ADAPT,
            'maxVision': MAX_VISION,
            'cris': CRIS_PERIOD,
            'worldXSize': WORLD_WIDTH,
            'worldYSize': WORLD_HEIGHT,
            'maleIncomeBase': MALE_INCOME_BASE,
            'femaleIncomeBase': FEMALE_INCOME_BASE,
            'expenditureBase': EXPENDITURE_BASE,
            'initCapitalMean': INIT_CAPITAL_MEAN,
            'initCapitalStd': INIT_CAPITAL_STD,
            'initAdaptMean': INIT_ADAPT_MEAN,
            'initAdaptStd': INIT_ADAPT_STD,
            'initToleranceMean': INIT_TOLERANCE_MEAN,
            'initToleranceStd': INIT_TOLERANCE_STD,
            'resourceBase': RESOURCE_BASE,
            'globalBoomIncrement': GLOBAL_BOOM_INCREMENT,
            'globalCrisisDecrement': abs(GLOBAL_CRISIS_DECREMENT),
            'localVariationAmplitude': LOCAL_VARIATION_AMPLITUDE,
            'consumptionRate': CONSUMPTION_RATE,
            'renewalRate': RENEWAL_RATE,
            'diffusionRate': DIFFUSION_RATE,
            'moveProb': MOVE_PROB,
            'birthBaseProb': BIRTH_BASE_PROB,
            'birthBoomMultiplier': BIRTH_BOOM_MULTIPLIER,
            'birthMinCapital': BIRTH_MIN_CAPITAL,
            'birthMaxFamilies': BIRTH_MAX_FAMILIES,
            'expenditureMin': EXPENDITURE_MIN,
            'expenditureMax': EXPENDITURE_MAX,
            'stepsBeforeReduceExpenses': STEPS_BEFORE_REDUCE_EXPENSES,
            'stepsBeforeWomanWork': STEPS_BEFORE_WOMAN_WORK
        }
        
        bg = capture_background(screen)
        menu = ConfigMenu(screen, font, current, bg)
        new_params = menu.run()
        
        if new_params:
            NUM_FAMILIES = int(new_params.get('numFamily', NUM_FAMILIES))
            BOARD_RET = float(new_params.get('boardRet', BOARD_RET))
            BOARD_SOG = float(new_params.get('boardSog', BOARD_SOG))
            BOARD_ADAPT = float(new_params.get('boardAdapt', BOARD_ADAPT))
            MAX_VISION = int(new_params.get('maxVision', MAX_VISION))
            CRIS_PERIOD = int(new_params.get('cris', CRIS_PERIOD))
            WORLD_WIDTH = int(new_params.get('worldXSize', WORLD_WIDTH))
            WORLD_HEIGHT = int(new_params.get('worldYSize', WORLD_HEIGHT))
            
            MALE_INCOME_BASE = new_params.get('maleIncomeBase', MALE_INCOME_BASE)
            FEMALE_INCOME_BASE = new_params.get('femaleIncomeBase', FEMALE_INCOME_BASE)
            EXPENDITURE_BASE = new_params.get('expenditureBase', EXPENDITURE_BASE)
            INIT_CAPITAL_MEAN = new_params.get('initCapitalMean', INIT_CAPITAL_MEAN)
            INIT_CAPITAL_STD = new_params.get('initCapitalStd', INIT_CAPITAL_STD)
            INIT_ADAPT_MEAN = new_params.get('initAdaptMean', INIT_ADAPT_MEAN)
            INIT_ADAPT_STD = new_params.get('initAdaptStd', INIT_ADAPT_STD)
            INIT_TOLERANCE_MEAN = new_params.get('initToleranceMean', INIT_TOLERANCE_MEAN)
            INIT_TOLERANCE_STD = new_params.get('initToleranceStd', INIT_TOLERANCE_STD)
            RESOURCE_BASE = new_params.get('resourceBase', RESOURCE_BASE)
            GLOBAL_BOOM_INCREMENT = new_params.get('globalBoomIncrement', GLOBAL_BOOM_INCREMENT)
            GLOBAL_CRISIS_DECREMENT = -abs(new_params.get('globalCrisisDecrement', abs(GLOBAL_CRISIS_DECREMENT)))
            LOCAL_VARIATION_AMPLITUDE = new_params.get('localVariationAmplitude', LOCAL_VARIATION_AMPLITUDE)
            CONSUMPTION_RATE = new_params.get('consumptionRate', CONSUMPTION_RATE)
            RENEWAL_RATE = new_params.get('renewalRate', RENEWAL_RATE)
            DIFFUSION_RATE = new_params.get('diffusionRate', DIFFUSION_RATE)
            MOVE_PROB = new_params.get('moveProb', MOVE_PROB)
            BIRTH_BASE_PROB = new_params.get('birthBaseProb', BIRTH_BASE_PROB)
            BIRTH_BOOM_MULTIPLIER = new_params.get('birthBoomMultiplier', BIRTH_BOOM_MULTIPLIER)
            BIRTH_MIN_CAPITAL = new_params.get('birthMinCapital', BIRTH_MIN_CAPITAL)
            BIRTH_MAX_FAMILIES = int(new_params.get('birthMaxFamilies', BIRTH_MAX_FAMILIES))
            EXPENDITURE_MIN = new_params.get('expenditureMin', EXPENDITURE_MIN)
            EXPENDITURE_MAX = new_params.get('expenditureMax', EXPENDITURE_MAX)
            STEPS_BEFORE_REDUCE_EXPENSES = int(new_params.get('stepsBeforeReduceExpenses', STEPS_BEFORE_REDUCE_EXPENSES))
            STEPS_BEFORE_WOMAN_WORK = int(new_params.get('stepsBeforeWomanWork', STEPS_BEFORE_WOMAN_WORK))
            
            import config
            config.NUM_FAMILIES = NUM_FAMILIES
            config.BOARD_RET = BOARD_RET
            config.BOARD_SOG = BOARD_SOG
            config.BOARD_ADAPT = BOARD_ADAPT
            config.MAX_VISION = MAX_VISION
            config.CRIS_PERIOD = CRIS_PERIOD
            config.WORLD_WIDTH = WORLD_WIDTH
            config.WORLD_HEIGHT = WORLD_HEIGHT
            config.MALE_INCOME_BASE = MALE_INCOME_BASE
            config.FEMALE_INCOME_BASE = FEMALE_INCOME_BASE
            config.EXPENDITURE_BASE = EXPENDITURE_BASE
            config.INIT_CAPITAL_MEAN = INIT_CAPITAL_MEAN
            config.INIT_CAPITAL_STD = INIT_CAPITAL_STD
            config.INIT_ADAPT_MEAN = INIT_ADAPT_MEAN
            config.INIT_ADAPT_STD = INIT_ADAPT_STD
            config.INIT_TOLERANCE_MEAN = INIT_TOLERANCE_MEAN
            config.INIT_TOLERANCE_STD = INIT_TOLERANCE_STD
            config.RESOURCE_BASE = RESOURCE_BASE
            config.GLOBAL_BOOM_INCREMENT = GLOBAL_BOOM_INCREMENT
            config.GLOBAL_CRISIS_DECREMENT = GLOBAL_CRISIS_DECREMENT
            config.LOCAL_VARIATION_AMPLITUDE = LOCAL_VARIATION_AMPLITUDE
            config.CONSUMPTION_RATE = CONSUMPTION_RATE
            config.RENEWAL_RATE = RENEWAL_RATE
            config.DIFFUSION_RATE = DIFFUSION_RATE
            config.MOVE_PROB = MOVE_PROB
            config.BIRTH_BASE_PROB = BIRTH_BASE_PROB
            config.BIRTH_BOOM_MULTIPLIER = BIRTH_BOOM_MULTIPLIER
            config.BIRTH_MIN_CAPITAL = BIRTH_MIN_CAPITAL
            config.BIRTH_MAX_FAMILIES = BIRTH_MAX_FAMILIES
            config.EXPENDITURE_MIN = EXPENDITURE_MIN
            config.EXPENDITURE_MAX = EXPENDITURE_MAX
            config.STEPS_BEFORE_REDUCE_EXPENSES = STEPS_BEFORE_REDUCE_EXPENSES
            config.STEPS_BEFORE_WOMAN_WORK = STEPS_BEFORE_WOMAN_WORK
            
            world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
            world.config = {'boardRet': BOARD_RET, 'boardSog': BOARD_SOG, 'cris': CRIS_PERIOD}
            world.next_phase_change = CRIS_PERIOD
            paused = False

    def show_stats():
        nonlocal paused
        was_paused = paused
        if not was_paused:
            paused = True
        show_statistics(world)
        paused = was_paused

    buttons = [
        ModernButton(0, 0, 0, 40, "Пауза / Продолжить", toggle_pause,
                    (200, 100, 50), (220, 120, 70), "Остановить или продолжить симуляцию"),
        ModernButton(0, 0, 0, 40, "Сброс / Настройка", reset_with_menu,
                    (180, 60, 60), (210, 80, 80), "Сбросить симуляцию и открыть настройки"),
        ModernButton(0, 0, 0, 40, "Один шаг", step_once,
                    (100, 100, 100), (130, 130, 130), "Выполнить один шаг симуляции"),
        ModernButton(0, 0, 0, 40, "Вывести графики", show_stats,
                    (50, 120, 180), (70, 140, 210), "Открыть окно с графиками за всю историю (можно сохранить в PNG)"),
    ]

    while running:
        screen_rect = screen.get_rect()
        offset_x, offset_y, panel_rect, cell_size = get_offsets_and_panel(screen_rect, WORLD_WIDTH, WORLD_HEIGHT)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    break
                elif event.key == pygame.K_SPACE:
                    toggle_pause()
                elif event.key == pygame.K_UP:
                    speed = min(10, speed + 1)
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - 1)
                elif event.key == pygame.K_r:
                    reset_with_menu()
                elif event.key == pygame.K_s:
                    step_once()
            
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                clicked_on_button = False
                for btn in buttons:
                    if btn.rect.collidepoint(mouse_pos):
                        clicked_on_button = True
                        break
                if not clicked_on_button and mouse_pos[0] < panel_rect.left:
                    cell_x = (mouse_pos[0] - offset_x) // cell_size
                    cell_y = (mouse_pos[1] - offset_y) // cell_size
                    if 0 <= cell_x < world.w and 0 <= cell_y < world.h:
                        for f in world.families:
                            if f.alive and f.x == cell_x and f.y == cell_y:
                                show_family_info(f, world.is_crisis)
                                break
                
                # Проверка на скроллбар
                if thumb_rect and thumb_rect.collidepoint(event.pos):
                    panel_dragging_scroll = True
                    panel_drag_start_y = event.pos[1]
                    panel_drag_start_scroll = panel_scroll_y
            
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                panel_dragging_scroll = False
            
            elif event.type == pygame.MOUSEMOTION and panel_dragging_scroll:
                delta = event.pos[1] - panel_drag_start_y
                max_scroll = max(0, 1200 - panel_rect.height)
                if thumb_rect:
                    scroll_range = panel_rect.height - thumb_rect.height
                    if scroll_range > 0:
                        panel_scroll_y = panel_drag_start_scroll + delta * max_scroll / scroll_range
                        panel_scroll_y = max(0, min(max_scroll, panel_scroll_y))
            
            elif event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                if panel_rect.collidepoint(mouse_pos):
                    panel_scroll_y -= event.y * INFO_PANEL_SCROLL_SPEED
                    max_scroll = max(0, 1200 - panel_rect.height)
                    panel_scroll_y = max(0, min(max_scroll, panel_scroll_y))
            
            slider.handle_event(event)
            for btn in buttons:
                btn.handle_event(event)
        
        if not running:
            break

        speed = slider.value

        if not paused:
            for _ in range(speed):
                world.step()
                if world.get_population() == 0:
                    paused = True

        screen.fill(COLOR_BG)
        draw_world(screen, world, offset_x, offset_y, cell_size)
        thumb_rect, scrollbar_rect = draw_simulation(screen, world, font, speed, paused, buttons, panel_rect, slider, panel_scroll_y)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()