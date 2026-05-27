import pygame
import json
import os
import tkinter as tk
from tkinter import filedialog
from colors import (
    COLOR_MENU_BG, COLOR_PANEL_BORDER, COLOR_TEXT, COLOR_MENU_SELECT,
    COLOR_INPUT_BG, COLOR_START_BUTTON, COLOR_START_HOVER,
    COLOR_BUTTON, COLOR_BUTTON_HOVER
)


class ConfigMenu:
    def __init__(self, screen, font, current_params, background_surface=None):
        self.screen = screen
        self.font = font
        self.params = current_params.copy()
        self.background_surface = background_surface
        self.selected_index = None
        self.editing = False
        self.edit_buffer = ""
        self.running = True
        self.result = None
        self.page = 0
        self.scroll_offset = 0
        self.dragging_scroll = False
        self.total_content_height = 0
        self.content_rect = None
        self.editing_key = None
        self.export_button_rect = None
        self.import_button_rect = None

        self.simple_keys = ['numFamily', 'boardRet', 'boardSog', 'boardAdapt', 'maxVision', 'cris', 'worldXSize', 'worldYSize']
        self.simple_names = [
            "Количество семей",
            "Граница экономического кризиса",
            "Кризисная граница толерантности",
            "Кризисная граница адаптивности",
            "Максимальный радиус видимости",
            "Периодичность смены кризиса",
            "Ширина поля",
            "Высота поля"
        ]

        self.advanced_groups = [
            {
                "name": "ДОХОДЫ И РАСХОДЫ",
                "keys": ['maleIncomeBase', 'femaleIncomeBase', 'expenditureBase'],
                "names": ["Доход мужчины", "Доход женщины", "Коэффициент расходов"]
            },
            {
                "name": "НАЧАЛЬНЫЕ ХАРАКТЕРИСТИКИ",
                "keys": ['initCapitalMean', 'initCapitalStd', 'initAdaptMean', 'initAdaptStd', 'initToleranceMean', 'initToleranceStd'],
                "names": ["Средний капитал", "Стд. отклонение капитала", "Средняя адаптивность", "Стд. отклонение адаптивности", "Средняя толерантность", "Стд. отклонение толерантности"]
            },
            {
                "name": "РЕСУРС И ЦИКЛЫ",
                "keys": ['resourceBase', 'globalBoomIncrement', 'globalCrisisDecrement'],
                "names": ["Базовый ресурс", "Прирост в подъём", "Убыль в кризис"]
            },
            {
                "name": "ЛОКАЛЬНАЯ ДИНАМИКА",
                "keys": ['localVariationAmplitude', 'consumptionRate', 'renewalRate', 'diffusionRate'],
                "names": ["Амплитуда вариации", "Скорость потребления", "Скорость восстановления", "Скорость диффузии"]
            },
            {
                "name": "ДВИЖЕНИЕ И РОЖДАЕМОСТЬ",
                "keys": ['moveProb', 'birthBaseProb', 'birthBoomMultiplier', 'birthMinCapital', 'birthMaxFamilies'],
                "names": ["Вероятность движения", "Базовая рождаемость", "Множитель в бум", "Мин. капитал для бонуса", "Макс. семей"]
            },
            {
                "name": "ГРАНИЦЫ И СЧЁТЧИКИ",
                "keys": ['expenditureMin', 'expenditureMax', 'stepsBeforeReduceExpenses', 'stepsBeforeWomanWork'],
                "names": ["Мин. расходы", "Макс. расходы", "Шагов до снижения расходов", "Шагов до выхода женщины"]
            }
        ]

        self.param_rects = []

    def draw_background(self):
        if self.background_surface is not None:
            self.screen.blit(self.background_surface, (0, 0))
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(COLOR_MENU_BG)

    def _update_content_height(self):
        if self.page == 0:
            self.total_content_height = len(self.simple_keys) * 32 + 20
        else:
            height = 20
            for group in self.advanced_groups:
                height += 28 + len(group["keys"]) * 32 + 10
            self.total_content_height = height

    def draw(self):
        self.draw_background()
        menu_w = 650
        menu_h = 620
        menu_x = (self.screen.get_width() - menu_w) // 2
        menu_y = (self.screen.get_height() - menu_h) // 2

        pygame.draw.rect(self.screen, COLOR_MENU_BG, (menu_x, menu_y, menu_w, menu_h), border_radius=15)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (menu_x, menu_y, menu_w, menu_h), 3, border_radius=15)

        btn_w = 120
        btn_h = 30
        btn_simple = pygame.Rect(menu_x + menu_w//2 - btn_w - 10, menu_y + 15, btn_w, btn_h)
        btn_advanced = pygame.Rect(menu_x + menu_w//2 + 10, menu_y + 15, btn_w, btn_h)
        mouse_pos = pygame.mouse.get_pos()

        simple_color = COLOR_START_HOVER if self.page == 0 else COLOR_BUTTON
        pygame.draw.rect(self.screen, simple_color, btn_simple, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_TEXT, btn_simple, 1, border_radius=8)
        simple_text = self.font.render("Базовые", True, COLOR_TEXT)
        self.screen.blit(simple_text, simple_text.get_rect(center=btn_simple.center))

        adv_color = COLOR_START_HOVER if self.page == 1 else COLOR_BUTTON
        pygame.draw.rect(self.screen, adv_color, btn_advanced, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_TEXT, btn_advanced, 1, border_radius=8)
        adv_text = self.font.render("Расширенные", True, COLOR_TEXT)
        self.screen.blit(adv_text, adv_text.get_rect(center=btn_advanced.center))

        self.btn_simple_rect = btn_simple
        self.btn_advanced_rect = btn_advanced

        self.content_rect = pygame.Rect(menu_x + 10, menu_y + 60, menu_w - 20, menu_h - 130)
        self._update_content_height()

        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.content_rect)

        if self.page == 0:
            self._draw_simple_page()
        else:
            self._draw_advanced_page()

        self.screen.set_clip(old_clip)

        if self.total_content_height > self.content_rect.height:
            self._draw_scrollbar()

        export_rect = pygame.Rect(menu_x + 30, menu_y + menu_h - 55, 100, 40)
        color_export = COLOR_BUTTON_HOVER if export_rect.collidepoint(mouse_pos) else COLOR_BUTTON
        pygame.draw.rect(self.screen, color_export, export_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_TEXT, export_rect, 2, border_radius=8)
        export_text = self.font.render("ЭКСПОРТ", True, COLOR_TEXT)
        export_text_rect = export_text.get_rect(center=export_rect.center)
        self.screen.blit(export_text, export_text_rect)
        self.export_button_rect = export_rect

        import_rect = pygame.Rect(menu_x + menu_w - 130, menu_y + menu_h - 55, 100, 40)
        color_import = COLOR_BUTTON_HOVER if import_rect.collidepoint(mouse_pos) else COLOR_BUTTON
        pygame.draw.rect(self.screen, color_import, import_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_TEXT, import_rect, 2, border_radius=8)
        import_text = self.font.render("ИМПОРТ", True, COLOR_TEXT)
        import_text_rect = import_text.get_rect(center=import_rect.center)
        self.screen.blit(import_text, import_text_rect)
        self.import_button_rect = import_rect

        start_rect = pygame.Rect(menu_x + menu_w//2 - 100, menu_y + menu_h - 55, 200, 40)
        color_start = COLOR_START_HOVER if start_rect.collidepoint(mouse_pos) else COLOR_START_BUTTON
        pygame.draw.rect(self.screen, color_start, start_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_TEXT, start_rect, 2, border_radius=8)
        start_text = self.font.render("ЗАПУСТИТЬ СИМУЛЯЦИЮ", True, COLOR_TEXT)
        start_text_rect = start_text.get_rect(center=start_rect.center)
        self.screen.blit(start_text, start_text_rect)
        self.start_button_rect = start_rect

    def _draw_simple_page(self):
        self.param_rects = []
        y = self.content_rect.y + 5 - self.scroll_offset

        for i, (name, key) in enumerate(zip(self.simple_names, self.simple_keys)):
            if y + 28 < self.content_rect.y or y > self.content_rect.bottom:
                y += 32
                continue

            value = self.params.get(key, 0)
            display_value = f"{value:.3f}".rstrip('0').rstrip('.') if isinstance(value, float) else str(value)

            text = self.font.render(f"{name}:", True, COLOR_TEXT)
            text_rect = text.get_rect(topleft=(self.content_rect.x + 15, y))
            self.screen.blit(text, text_rect)

            if self.editing and self.editing_key == key:
                input_rect = pygame.Rect(self.content_rect.x + 250, y, 120, 28)
                pygame.draw.rect(self.screen, COLOR_INPUT_BG, input_rect, border_radius=5)
                pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, input_rect, 2, border_radius=5)
                edit_surf = self.font.render(self.edit_buffer + "_", True, COLOR_TEXT)
                self.screen.blit(edit_surf, (input_rect.x + 5, input_rect.y + 5))
                self.param_rects.append((input_rect, key, y, name))
            else:
                value_surf = self.font.render(display_value, True, COLOR_TEXT)
                value_rect = value_surf.get_rect(topleft=(self.content_rect.x + 250, y))
                self.screen.blit(value_surf, value_rect)
                click_rect = pygame.Rect(self.content_rect.x + 15, y, 350, 28)
                self.param_rects.append((click_rect, key, y, name))

            y += 32

    def _draw_advanced_page(self):
        self.param_rects = []
        y = self.content_rect.y + 5 - self.scroll_offset

        for group in self.advanced_groups:
            if y + 28 >= self.content_rect.y and y <= self.content_rect.bottom:
                header = self.font.render(group["name"], True, (180, 180, 200))
                self.screen.blit(header, (self.content_rect.x + 10, y))
            y += 28

            for name, key in zip(group["names"], group["keys"]):
                if y + 28 >= self.content_rect.y and y <= self.content_rect.bottom:
                    value = self.params.get(key, 0)
                    display_value = f"{value:.3f}".rstrip('0').rstrip('.') if isinstance(value, float) else str(value)

                    text = self.font.render(f"{name}:", True, COLOR_TEXT)
                    text_rect = text.get_rect(topleft=(self.content_rect.x + 15, y))
                    self.screen.blit(text, text_rect)

                    if self.editing and self.editing_key == key:
                        input_rect = pygame.Rect(self.content_rect.x + 250, y, 120, 28)
                        pygame.draw.rect(self.screen, COLOR_INPUT_BG, input_rect, border_radius=5)
                        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, input_rect, 2, border_radius=5)
                        edit_surf = self.font.render(self.edit_buffer + "_", True, COLOR_TEXT)
                        self.screen.blit(edit_surf, (input_rect.x + 5, input_rect.y + 5))
                        self.param_rects.append((input_rect, key, y, name))
                    else:
                        value_surf = self.font.render(display_value, True, COLOR_TEXT)
                        value_rect = value_surf.get_rect(topleft=(self.content_rect.x + 250, y))
                        self.screen.blit(value_surf, value_rect)
                        click_rect = pygame.Rect(self.content_rect.x + 15, y, 350, 28)
                        self.param_rects.append((click_rect, key, y, name))

                y += 32

            y += 10

    def _draw_scrollbar(self):
        scrollbar_rect = pygame.Rect(self.content_rect.right - 12, self.content_rect.y, 8, self.content_rect.height)
        pygame.draw.rect(self.screen, (50, 50, 60), scrollbar_rect, border_radius=4)

        visible_ratio = self.content_rect.height / self.total_content_height
        thumb_height = max(30, int(visible_ratio * self.content_rect.height))
        max_scroll = max(0, self.total_content_height - self.content_rect.height)
        if max_scroll > 0:
            thumb_y = self.content_rect.y + int((self.scroll_offset / max_scroll) * (self.content_rect.height - thumb_height))
            thumb_y = max(self.content_rect.y, min(self.content_rect.bottom - thumb_height, thumb_y))
            thumb_rect = pygame.Rect(self.content_rect.right - 12, thumb_y, 8, thumb_height)
            pygame.draw.rect(self.screen, (100, 100, 120), thumb_rect, border_radius=4)
            self.thumb_rect = thumb_rect
            self.scrollbar_rect = scrollbar_rect
        else:
            self.thumb_rect = None
            self.scrollbar_rect = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(self, 'btn_simple_rect') and self.btn_simple_rect.collidepoint(event.pos):
                self.page = 0
                self.selected_index = None
                self.editing = False
                self.editing_key = None
                self.scroll_offset = 0
                return
            if hasattr(self, 'btn_advanced_rect') and self.btn_advanced_rect.collidepoint(event.pos):
                self.page = 1
                self.selected_index = None
                self.editing = False
                self.editing_key = None
                self.scroll_offset = 0
                self._update_content_height()
                return
            if hasattr(self, 'export_button_rect') and self.export_button_rect and self.export_button_rect.collidepoint(event.pos):
                self._export_settings()
                return
            if hasattr(self, 'import_button_rect') and self.import_button_rect and self.import_button_rect.collidepoint(event.pos):
                self._import_settings()
                return
            if hasattr(self, 'start_button_rect') and self.start_button_rect.collidepoint(event.pos):
                self.running = False
                self.result = self.params
                return

            if self.page == 1 and self.total_content_height > self.content_rect.height:
                if hasattr(self, 'thumb_rect') and self.thumb_rect and self.thumb_rect.collidepoint(event.pos):
                    self.dragging_scroll = True
                    self.drag_start_y = event.pos[1]
                    self.drag_start_offset = self.scroll_offset
                    return
                if hasattr(self, 'scrollbar_rect') and self.scrollbar_rect and self.scrollbar_rect.collidepoint(event.pos):
                    rel_y = event.pos[1] - self.scrollbar_rect.y
                    max_scroll = max(0, self.total_content_height - self.content_rect.height)
                    self.scroll_offset = (rel_y / self.scrollbar_rect.height) * max_scroll
                    self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))
                    return

            for i, (rect, key, y_pos, name) in enumerate(self.param_rects):
                if rect and rect.collidepoint(event.pos):
                    self.selected_index = i
                    self.editing = True
                    self.editing_key = key
                    self.edit_buffer = str(self.params.get(key, 0))
                    return

            self.selected_index = None
            if self.editing:
                self._save_edit()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_scroll = False

        elif event.type == pygame.MOUSEMOTION and self.dragging_scroll:
            delta = event.pos[1] - self.drag_start_y
            max_scroll = max(0, self.total_content_height - self.content_rect.height)
            if max_scroll > 0 and hasattr(self, 'thumb_rect') and self.thumb_rect:
                scroll_range = self.content_rect.height - self.thumb_rect.height
                if scroll_range > 0:
                    self.scroll_offset = self.drag_start_offset + delta * max_scroll / scroll_range
                    self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))

        elif event.type == pygame.MOUSEWHEEL and self.page == 1:
            self.scroll_offset -= event.y * 30
            max_scroll = max(0, self.total_content_height - self.content_rect.height)
            self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))

        elif event.type == pygame.KEYDOWN and self.editing:
            if event.key == pygame.K_RETURN:
                self._save_edit()
            elif event.key == pygame.K_ESCAPE:
                self._cancel_edit()
            elif event.key == pygame.K_BACKSPACE:
                self.edit_buffer = self.edit_buffer[:-1]
            else:
                char = event.unicode
                if char.isdigit() or char == '.' or char == '-':
                    self.edit_buffer += char

    def _save_edit(self):
        if self.editing_key is not None:
            try:
                current_val = self.params.get(self.editing_key, 0)
                if isinstance(current_val, float):
                    val = float(self.edit_buffer)
                else:
                    val = int(self.edit_buffer)
                self.params[self.editing_key] = val
            except ValueError:
                pass
        self.editing = False
        self.editing_key = None
        self.selected_index = None
        self.edit_buffer = ""

    def _cancel_edit(self):
        self.editing = False
        self.editing_key = None
        self.selected_index = None
        self.edit_buffer = ""

    def _export_settings(self):
        """Экспорт настроек в JSON файл"""
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Сохранить настройки как"
        )
        root.destroy()

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.params, f, ensure_ascii=False, indent=4)
                print(f"Настройки сохранены в {file_path}")
            except Exception as e:
                print(f"Ошибка сохранения: {e}")

    def _import_settings(self):
        """Импорт настроек из JSON файла"""
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Выберите файл настроек"
        )
        root.destroy()

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_params = json.load(f)

                for key in self.params.keys():
                    if key in imported_params:
                        self.params[key] = imported_params[key]

                print(f"Настройки загружены из {file_path}")
            except Exception as e:
                print(f"Ошибка загрузки: {e}")

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
