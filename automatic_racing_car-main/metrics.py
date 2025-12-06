# metrics.py
"""Metrics tracking untuk performa mobil"""

import pygame
import csv


class Metrics:
    """Class untuk tracking dan menampilkan metrics performa mobil"""
    
    def __init__(self, label):
        """
        Inisialisasi metrics tracker
        
        Args:
            label (str): Label untuk identifikasi metrics
        """
        self.label = label
        self.t = 0.0  # total waktu
        self.coll = 0  # jumlah collision
        self.corr = 0  # jumlah koreksi steering besar
        self.last_steer = 0.0
        self.font = pygame.font.SysFont(None, 22)
        self.finished = False
        self.finish_time = 0.0

    def update(self, dt, collided, steer):
        """
        Update metrics setiap frame
        
        Args:
            dt (float): delta time
            collided (bool): apakah terjadi collision
            steer (float): nilai steering saat ini
        """
        if not self.finished:
            self.t += dt
        
        if collided:
            self.coll += 1
        if abs(steer - self.last_steer) > 0.35:
            self.corr += 1
        self.last_steer = steer

    def draw(self, screen, pos):
        """
        Render metrics ke screen
        
        Args:
            screen: pygame screen
            pos (tuple): posisi (x, y) untuk render
        """
        txt = f"{self.label}: t={self.t:5.1f}s  collisions={self.coll}  corrections={self.corr}"
        img = self.font.render(txt, True, (255, 255, 255))
        screen.blit(img, pos)

    def save_csv(self, path, laps=0):
        """
        Simpan metrics ke file CSV
        
        Args:
            path (str): path file output CSV
            laps (int): jumlah lap yang diselesaikan
        """
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time_s", "collisions", "corrections", "laps", "label"])
            w.writerow([round(self.t, 2), self.coll, self.corr, laps, self.label])
