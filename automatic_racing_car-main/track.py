# track.py
"""Track class untuk mendeteksi jalan dan render track"""

import pygame
import os


class Track:
    """
    Jalan = aspal abu-abu (low saturation, mid brightness) ATAU garis biru.
    Sampling 3x3 agar robust ke noise/anti alias.
    """

    def __init__(self, img_path):
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Track image tidak ditemukan: {img_path}")
        # jangan .convert di sini, karena surface display belum dibuat
        self.surface = pygame.image.load(img_path)
        self.width, self.height = self.surface.get_size()
        # parameter deteksi "abu-abu"
        self.gray_tol = 18
        self.gray_minB = 45
        self.gray_maxB = 185

    def _is_road_pixel(self, x, y):
        """Cek apakah pixel (x,y) adalah jalan"""
        r, g, b = self.surface.get_at((x, y))[:3]
        # Garis putih (start line) juga dianggap sebagai jalan
        white_like = (r == 255 and g == 255 and b == 255)
        if white_like:
            return True
        mean = (r + g + b) / 3
        gray_like = (
            abs(r - g) <= self.gray_tol
            and abs(g - b) <= self.gray_tol
            and self.gray_minB <= mean <= self.gray_maxB
        )
        blue_like = b > 150 and r < 140 and g < 175
        return gray_like or blue_like

    def is_road(self, x, y):
        """Cek apakah koordinat (x,y) adalah jalan dengan sampling 3x3"""
        if x < 1 or y < 1 or x >= self.width - 1 or y >= self.height - 1:
            return False
        # majority 3x3
        cnt = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if self._is_road_pixel(x + dx, y + dy):
                    cnt += 1
        return cnt >= 5

    def draw(self, screen):
        """Render track ke screen"""
        # convert sesuai format display hanya saat draw
        screen.blit(self.surface.convert(), (0, 0))
