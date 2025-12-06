# car.py
"""Car class untuk mobil balap dengan sensor dan fisika"""

import pygame
import math
from utils import clamp


class Car:
    """Base class untuk mobil balap dengan sensor dan fisika"""

    def __init__(self, pos, color, track, name="Car", sensor_color=(0, 255, 0), sensor_len=320):
        self.track = track
        self.name = name
        self.pos = pygame.Vector2(pos)
        self.heading = -math.pi / 2
        self.vel = 0.0

        # fisika ringan
        self.max_speed = 900
        self.accel = 2100
        self.brake_accel = 3400
        self.drag = 0.986

        # sensor (ditambah untuk deteksi lebih baik)
        self.sensor_angles = [-90, -70, -40, -20, 0, 20, 40, 70, 90]
        self.sensor_len = sensor_len
        self.sensor_color = sensor_color

        # sprite
        self.image = self._make_sprite(color)

        # lap counter
        self.lap_count = 0
        self.last_x = pos[0]  # untuk deteksi melewati garis start

        # radius tabrakan sederhana (berguna untuk cone collision)
        self.hit_radius = 12
        
        # Cooldowns untuk tabrakan (dalam detik)
        self.cone_hit_cooldown = 0.0
        self.car_hit_cooldown = 0.0
        self.finished = False # Flag untuk menandai mobil sudah finish atau belum

    def _make_sprite(self, color):
        """Membuat sprite mobil dengan warna tertentu"""
        w, h = 20, 32  # Dikecilkan menjadi setengah ukuran
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, color, (4, 1, 12, 30))
        pygame.draw.rect(s, (20, 20, 20), (2, 5, 2, 22))
        pygame.draw.rect(s, (20, 20, 20), (16, 5, 2, 22))
        pygame.draw.polygon(s, (245, 245, 245), [(10, 0), (13, 6), (7, 6)])
        return s

    def _point_hits_cone(self, px, py, cones):
        """True jika point (px,py) berada dalam radius cone mana pun."""
        if not cones:
            return False

        # cones bisa list Cone object yang punya .pos (Vector2) dan .radius
        for c in cones:
            dx = c.pos.x - px
            dy = c.pos.y - py
            if dx * dx + dy * dy <= (c.radius * c.radius):
                return True
        return False

    def _point_hits_car(self, px, py, other_car):
        """True jika point (px,py) berada dalam radius mobil lain."""
        if not other_car:
            return False
        
        dx = other_car.pos.x - px
        dy = other_car.pos.y - py
        # Gunakan radius tabrakan gabungan untuk deteksi lebih aman
        total_radius = self.hit_radius + other_car.hit_radius
        if dx * dx + dy * dy <= (total_radius * total_radius):
            return True
        return False

    def _cast_ray(self, ang, maxlen, cones=None, other_car=None):
        """Cast ray sensor untuk mendeteksi jarak ke tepi jalan, cone, atau mobil lain"""
        x, y = self.pos
        step = 3

        for d in range(0, int(maxlen), step):
            px = int(x + math.cos(ang) * d)
            py = int(y + math.sin(ang) * d)

            # 1) tepi jalan
            if not self.track.is_road(px, py):
                return d

            # 2) cone sebagai obstacle
            if self._point_hits_cone(px, py, cones):
                return d
            
            # 3) mobil lain sebagai obstacle
            if self._point_hits_car(px, py, other_car):
                return d

        return maxlen

    def read_sensors(self, cones=None, other_car=None):
        """Membaca semua sensor dan mengembalikan dict sensor values"""
        dists = []
        for deg in self.sensor_angles:
            ang = self.heading + math.radians(deg)
            d = self._cast_ray(ang, self.sensor_len, cones=cones, other_car=other_car)
            dists.append(d)

        # Sensor jarak jauh tambahan
        long_front_dist = self._cast_ray(self.heading, self.sensor_len * 1.5, cones=cones, other_car=other_car)

        # Dengan 9 sensor: [-90, -70, -40, -20, 0, 20, 40, 70, 90]
        far_left = dists[0]
        left = min(dists[1], dists[2])
        lmid = dists[3]
        front = dists[4]
        rmid = dists[5]
        right = min(dists[6], dists[7])
        far_right = dists[8]
        bias = right - left

        return {
            "far_left": far_left,
            "left": left,
            "lmid": lmid,
            "front": front,
            "front_long": long_front_dist,  # Menambahkan sensor jarak jauh
            "rmid": rmid,
            "right": right,
            "far_right": far_right,
            "bias": bias,
            "speed": self.vel,
        }

    def update(self, dt, steer, throttle, brake):
        """Update posisi dan kecepatan mobil berdasarkan input kontrol"""
        # Update cooldowns
        if self.cone_hit_cooldown > 0:
            self.cone_hit_cooldown -= dt
        if self.car_hit_cooldown > 0:
            self.car_hit_cooldown -= dt

        # Jangan update jika sudah finish
        if self.finished:
            self.vel *= 0.9 # Perlambat mobil sampai berhenti
            return

        # rotasi
        self.heading += steer * 2.2 * dt

        # update kecepatan
        self.vel += throttle * self.accel * dt
        self.vel -= brake * self.brake_accel * dt
        self.vel *= self.drag
        self.vel = clamp(self.vel, 0, self.max_speed)

        # update posisi
        self.pos.x += math.cos(self.heading) * self.vel * dt
        self.pos.y += math.sin(self.heading) * self.vel * dt

    def collide_wall(self):
        """Cek tabrakan dengan dinding dan recovery"""
        ix, iy = int(self.pos.x), int(self.pos.y)
        hit = not self.track.is_road(ix, iy)
        if hit:
            self.vel *= 0.5
            # dorong masuk ke area 'jalan' terdekat (pencarian kipas kecil)
            best = None
            bestd = 1e9
            for a in range(-90, 91, 15):
                ang = math.radians(a)
                for d in range(18, 80, 6):
                    px = int(self.pos.x + math.cos(self.heading + ang) * d)
                    py = int(self.pos.y + math.sin(self.heading + ang) * d)
                    if self.track.is_road(px, py):
                        if d < bestd:
                            bestd, best = d, (px, py, self.heading + ang)
                        break
            if best:
                self.pos.x, self.pos.y, self.heading = best
        return hit

    def collides_with_car(self, other_car):
        """Cek tabrakan dengan mobil lain"""
        if self.car_hit_cooldown > 0 or other_car.car_hit_cooldown > 0:
            return False # Salah satu mobil masih dalam cooldown
            
        dist_sq = self.pos.distance_squared_to(other_car.pos)
        min_dist = self.hit_radius + other_car.hit_radius
        
        if dist_sq < (min_dist * min_dist):
            # Set cooldown untuk kedua mobil
            self.car_hit_cooldown = 1.5 # Cooldown 1.5 detik
            other_car.car_hit_cooldown = 1.5
            return True
        return False

    def draw(self, screen, debug=False, cones=None):
        """Render mobil dan sensor (jika debug mode)"""
        rot = pygame.transform.rotate(self.image, -math.degrees(self.heading) - 90)
        rect = rot.get_rect(center=(self.pos.x, self.pos.y))
        screen.blit(rot, rect)

        if debug:
            for deg in self.sensor_angles:
                ang = self.heading + math.radians(deg)
                d = self._cast_ray(ang, self.sensor_len, cones=cones)
                end = (self.pos.x + math.cos(ang) * d, self.pos.y + math.sin(ang) * d)
                pygame.draw.line(screen, self.sensor_color, self.pos, end, 2)
