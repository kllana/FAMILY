# ui/menu.py
import pygame
from colors import (
    COLOR_MENU_BG, COLOR_PANEL_BORDER, COLOR_TEXT, COLOR_MENU_SELECT,
    COLOR_INPUT_BG, COLOR_START_BUTTON, COLOR_START_HOVER
)

class ConfigMenu:
    def __init__(self, screen, font, current_params, background_surface=None):
        self.screen = screen
        self.font = font
        self.params = current_params.copy()
        self.background_surface = background_surface
        self.param_names = [
            "Количество семей (numFamily)",
            "Граница экономического кризиса для семьи (boardRet)",
            "Кризисная граница толерантности (boardSog)",
            "Кризисная граница адаптивности (boardAdapt)",
            "Максимальный радиус видимости (maxVision)",
            "Периодичность смены кризиса (cris)",
            "Ширина поля (worldXSize)",
            "Высота поля (worldYSize)"
        ]
        self.param_keys = ['numFamily', 'boardRet', 'boardSog', 'boardAdapt', 'maxVision', 'cris', 'worldXSize', 'worldYSize']
        self.param_rects = []
        self.selected_index = None
        self.editing = False
        self.edit_buffer = ""
        self.running = True
        self.result = None

    def draw_background(self):
        if self.background_surface is not None:
            # Рисуем сохранённый фон
            self.screen.blit(self.background_surface, (0, 0))
            # Затемняем его
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))   # полупрозрачный чёрный
            self.screen.blit(overlay, (0, 0))
        else:
            # fallback — просто тёмный фон
            self.screen.fill(COLOR_MENU_BG)

    def draw(self):
        self.draw_background()
        menu_w = 500
        menu_h = 520
        menu_x = (self.screen.get_width() - menu_w) // 2
        menu_y = (self.screen.get_height() - menu_h) // 2
        pygame.draw.rect(self.screen, COLOR_MENU_BG, (menu_x, menu_y, menu_w, menu_h), border_radius=15)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (menu_x, menu_y, menu_w, menu_h), 3, border_radius=15)
        title = self.font.render("Настройка параметров модели", True, COLOR_TEXT)
        self.screen.blit(title, (menu_x + menu_w//2 - title.get_width()//2, menu_y + 20))
        y = menu_y + 70
        self.param_rects.clear()
        for i, (name, key) in enumerate(zip(self.param_names, self.param_keys)):
            value = self.params[key]
            display_value = f"{value:.1f}" if isinstance(value, float) else str(value)
            color = COLOR_MENU_SELECT if (self.selected_index == i and not self.editing) else COLOR_TEXT
            text = self.font.render(f"{name}: {display_value}", True, color)
            rect = text.get_rect(topleft=(menu_x + 30, y))
            self.param_rects.append(rect)
            self.screen.blit(text, rect)
            y += 35
        if self.editing:
            edit_text = self.font.render(f"Введите новое значение: {self.edit_buffer}_ (ENTER — сохранить, ESC — отмена)", True, COLOR_TEXT)
            edit_rect = edit_text.get_rect(topleft=(menu_x + 30, y))
            pygame.draw.rect(self.screen, COLOR_INPUT_BG, edit_rect.inflate(10, 5), border_radius=5)
            self.screen.blit(edit_text, edit_rect)
        start_rect = pygame.Rect(menu_x + menu_w//2 - 100, menu_y + menu_h - 70, 200, 45)
        mouse_pos = pygame.mouse.get_pos()
        color_start = COLOR_START_HOVER if start_rect.collidepoint(mouse_pos) else COLOR_START_BUTTON
        pygame.draw.rect(self.screen, color_start, start_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_TEXT, start_rect, 2, border_radius=8)
        start_text = self.font.render("ЗАПУСТИТЬ СИМУЛЯЦИЮ", True, COLOR_TEXT)
        start_text_rect = start_text.get_rect(center=start_rect.center)
        self.screen.blit(start_text, start_text_rect)
        self.start_button_rect = start_rect

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.param_rects):
                if rect.collidepoint(event.pos):
                    self.selected_index = i
                    self.editing = True
                    self.edit_buffer = str(self.params[self.param_keys[i]])
                    return
            if hasattr(self, 'start_button_rect') and self.start_button_rect.collidepoint(event.pos):
                self.running = False
                self.result = self.params
                return
            if not self.editing:
                self.selected_index = None
        if event.type == pygame.KEYDOWN and self.editing:
            if event.key == pygame.K_RETURN:
                try:
                    key = self.param_keys[self.selected_index]
                    if key in ['numFamily', 'maxVision', 'cris', 'worldXSize', 'worldYSize']:
                        val = int(self.edit_buffer)
                    else:
                        val = float(self.edit_buffer)
                    self.params[key] = val
                except ValueError:
                    pass
                self.editing = False
                self.selected_index = None
                self.edit_buffer = ""
            elif event.key == pygame.K_ESCAPE:
                self.editing = False
                self.selected_index = None
                self.edit_buffer = ""
            elif event.key == pygame.K_BACKSPACE:
                self.edit_buffer = self.edit_buffer[:-1]
            else:
                char = event.unicode
                if char.isdigit() or char == '.' or char == '-':
                    self.edit_buffer += char

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
        return self.result