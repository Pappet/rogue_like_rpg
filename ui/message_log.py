import pygame
import re
from typing import List, Tuple, Optional
from config import LogCategory, LOG_COLORS

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 150, 255)
YELLOW = (255, 255, 50)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GREY = (128, 128, 128)

COLOR_MAP = {
    "white": WHITE,
    "red": RED,
    "green": GREEN,
    "blue": BLUE,
    "yellow": YELLOW,
    "orange": ORANGE,
    "purple": PURPLE,
    "grey": GREY
}

def parse_rich_text(text: str, default_color: Tuple[int, int, int] = WHITE) -> List[Tuple[str, Tuple[int, int, int]]]:
    """
    Parses text with [color=name]tags[/color] into a list of (text, color) tuples.
    """
    results = []
    # Pattern to find tags
    pattern = r'(\[color=[a-zA-Z]+\].*?\[/color\])'
    parts = re.split(pattern, text)
    
    for part in parts:
        if not part:
            continue
            
        tag_match = re.match(r'\[color=([a-zA-Z]+)\](.*?)\[/color\]', part)
        if tag_match:
            color_name = tag_match.group(1).lower()
            inner_text = tag_match.group(2)
            color = COLOR_MAP.get(color_name, default_color)
            results.append((inner_text, color))
        else:
            results.append((part, default_color))
            
    return results

class MessageLog:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font, max_messages: int = 100):
        self.rect = rect
        self.font = font
        self.max_messages = max_messages
        self.messages = []
        self.line_height = self.font.get_linesize()

    def add_message(self, text: str, color: str = None, category: Optional[LogCategory] = None):
        default_color = WHITE
        if category and category in LOG_COLORS:
            default_color = LOG_COLORS[category]
        
        if color:
            text = f"[color={color}]{text}[/color]"
        
        parsed_message = parse_rich_text(text, default_color)
        self.messages.append(parsed_message)
        
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def draw(self, surface: pygame.Surface):
        # Draw background
        pygame.draw.rect(surface, (15, 15, 15), self.rect)
        pygame.draw.line(surface, (100, 100, 100), (self.rect.x, self.rect.y), (self.rect.right, self.rect.y), 2)
        
        # Draw messages from bottom to top
        x_start = self.rect.x + 10
        y_bottom = self.rect.bottom - 5
        
        for i, message in enumerate(reversed(self.messages)):
            y_pos = y_bottom - (i + 1) * self.line_height
            if y_pos < self.rect.top + 5:
                break
                
            current_x = x_start
            for text_chunk, color in message:
                surf = self.font.render(text_chunk, True, color)
                surface.blit(surf, (current_x, y_pos))
                current_x += surf.get_width()
