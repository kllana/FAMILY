# main.py
import pygame
from config import (
    NUM_FAMILIES, BOARD_RET, BOARD_SOG, BOARD_ADAPT, MAX_VISION,
    CRIS_PERIOD, WORLD_WIDTH, WORLD_HEIGHT, CELL_SIZE, INFO_PANEL_WIDTH
)
from colors import COLOR_BG
from models import World
from ui import ConfigMenu, ModernButton, Slider, draw_world, draw_simulation
from statistics import show_statistics


def capture_background(screen):
    return screen.copy()


def show_family_info(family, is_crisis):
    info_width, info_height = 300, 230
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
            if ev.type == pygame.KEYDOWN or ev.type == pygame.MOUSEBUTTONDOWN:
                waiting = False
            elif ev.type == pygame.QUIT:
                pygame.quit()
                exit()

    screen.blit(background, (0, 0))
    pygame.display.flip()


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
        'worldYSize': WORLD_HEIGHT,
        'maleIncomeBase': 5.0, 'femaleIncomeBase': 4.0, 'expenditureBase': 0.80,
        'initCapitalMean': 190.0, 'initCapitalStd': 80.0,
        'initAdaptMean': 50.0, 'initAdaptStd': 15.0,
        'initToleranceMean': 50.0, 'initToleranceStd': 15.0,
        'resourceBase': 22.0, 'globalBoomIncrement': 0.15, 'globalCrisisDecrement': -0.20,
        'localVariationAmplitude': 12.0, 'consumptionRate': 0.5, 'renewalRate': 0.005, 'diffusionRate': 0.03,
        'moveProb': 0.5, 'birthBaseProb': 0.003, 'birthBoomMultiplier': 4.0,
        'birthMinCapital': 150.0, 'birthMaxFamilies': 200,
        'expenditureMin': 0.10, 'expenditureMax': 0.35,
        'stepsBeforeReduceExpenses': 10, 'stepsBeforeWomanWork': 5
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
        CRIS_PERIOD = int(params.get('cris', CRIS_PERIOD))
        MAX_VISION = int(params.get('maxVision', MAX_VISION))
        WORLD_WIDTH = int(params.get('worldXSize', WORLD_WIDTH))
        WORLD_HEIGHT = int(params.get('worldYSize', WORLD_HEIGHT))

    world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
    world.config = {'boardRet': BOARD_RET, 'boardSog': BOARD_SOG, 'cris': CRIS_PERIOD}

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
        bg = capture_background(screen)
        menu = ConfigMenu(screen, font, current, bg)
        new_params = menu.run()
        if new_params:
            NUM_FAMILIES = int(new_params.get('numFamily', NUM_FAMILIES))
            BOARD_RET = float(new_params.get('boardRet', BOARD_RET))
            BOARD_SOG = float(new_params.get('boardSog', BOARD_SOG))
            CRIS_PERIOD = int(new_params.get('cris', CRIS_PERIOD))
            MAX_VISION = int(new_params.get('maxVision', MAX_VISION))
            WORLD_WIDTH = int(new_params.get('worldXSize', WORLD_WIDTH))
            WORLD_HEIGHT = int(new_params.get('worldYSize', WORLD_HEIGHT))
            world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
            world.config = {'boardRet': BOARD_RET, 'boardSog': BOARD_SOG, 'cris': CRIS_PERIOD}
            paused = False

    def show_stats():
        nonlocal paused
        was_paused = paused
        if not was_paused:
            paused = True
        show_statistics(world)
        paused = was_paused

    # Кнопки с подсказками
    buttons = [
        ModernButton(0, 0, 0, 40, "Пауза / Продолжить", toggle_pause,
                    (200, 100, 50), (220, 120, 70), "Остановить или продолжить симуляцию"),
        ModernButton(0, 0, 0, 40, "Сброс / Настройка", reset_with_menu,
                    (180, 60, 60), (210, 80, 80), "Сбросить симуляцию и открыть настройки"),
        ModernButton(0, 0, 0, 40, "Показать графики", show_stats,
                    (50, 120, 180), (70, 140, 210), "Открыть окно с графиками статистики"),
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