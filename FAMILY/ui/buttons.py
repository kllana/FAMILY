# ui/buttons.py
import pygame
from colors import COLOR_TEXT, COLOR_PANEL_BORDER

class ModernButton:
    def __init__(self, x, y, w, h, text, action, color_idle, color_hover):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.hovered = False
        self.color_idle = color_idle
        self.color_hover = color_hover

    def draw(self, screen, font):
        color = self.color_hover if self.hovered else self.color_idle
        shadow = self.rect.copy()
        shadow.x += 2
        shadow.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 50), shadow, border_radius=10)
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, COLOR_TEXT, self.rect, 2, border_radius=10)
        text_surf = font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()


class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial_val):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.dragging = False

    def draw(self, screen):
        pygame.draw.rect(screen, (70, 70, 85), self.rect, border_radius=6)
        handle_x = self.rect.left + int((self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width)
        handle_rect = pygame.Rect(handle_x - 6, self.rect.centery - 8, 12, 16)
        pygame.draw.rect(screen, (100, 100, 120), handle_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, self.rect, 1, border_radius=6)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_pos(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_pos(event.pos)

    def _set_from_pos(self, pos):
        rel_x = max(0, min(self.rect.width, pos[0] - self.rect.left))
        self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)
        self.value = round(self.value)
