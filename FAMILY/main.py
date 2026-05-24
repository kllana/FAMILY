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
        'worldYSize': WORLD_HEIGHT
    }

    # Временный мир для фона
    temp_world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
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

    menu = ConfigMenu(screen, font, default_params)
    params = menu.run()
    if params:
        NUM_FAMILIES = params['numFamily']
        BOARD_RET = params['boardRet']
        BOARD_SOG = params['boardSog']
        CRIS_PERIOD = params['cris']
        MAX_VISION = params['maxVision']
        WORLD_WIDTH = params['worldXSize']
        WORLD_HEIGHT = params['worldYSize']

    world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
    world.config = {
        'boardRet': BOARD_RET,
        'boardSog': BOARD_SOG,
        'cris': CRIS_PERIOD
    }

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
        menu = ConfigMenu(screen, font, current)
        new_params = menu.run()
        if new_params:
            NUM_FAMILIES = new_params['numFamily']
            BOARD_RET = new_params['boardRet']
            BOARD_SOG = new_params['boardSog']
            CRIS_PERIOD = new_params['cris']
            MAX_VISION = new_params['maxVision']
            WORLD_WIDTH = new_params['worldXSize']
            WORLD_HEIGHT = new_params['worldYSize']
            world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_FAMILIES, MAX_VISION)
            world.config = {
                'boardRet': BOARD_RET,
                'boardSog': BOARD_SOG,
                'cris': CRIS_PERIOD
            }
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
                    (200, 100, 50), (220, 120, 70)),
        ModernButton(0, 0, 0, 40, "Сброс / Настройка", reset_with_menu, 
                    (180, 60, 60), (210, 80, 80)),
        ModernButton(0, 0, 0, 40, "Показать графики", show_stats, 
                    (50, 120, 180), (70, 140, 210)),
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