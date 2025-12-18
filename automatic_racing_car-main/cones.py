# cones.py
import random
import pygame

class Cone:
    def __init__(self, pos, radius=10):
        self.pos = pygame.Vector2(pos)
        self.radius = radius


class ConeManager:
    def __init__(
        self,
        track,
        n=10,
        radius=10,
        keepout=60,
        max_tries=2000,
        image_path="assets/cone.png"
    ):
        self.track = track
        self.n = n
        self.radius = radius
        self.keepout = keepout
        self.max_tries = max_tries

        self.width = getattr(track, "width", track.surface.get_width())
        self.height = getattr(track, "height", track.surface.get_height())

        # Load image cone sekali
        self.cone_img = None
        try:
            img = pygame.image.load(image_path).convert_alpha()
            size = int(self.radius * 2)
            self.cone_img = pygame.transform.smoothscale(img, (size, size))
        except:
            self.cone_img = None

        self.cones = [
            Cone(self._random_road_pos([]), radius=self.radius)
            for _ in range(self.n)
        ]

    def _random_road_pos(self, cars):
        for _ in range(self.max_tries):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)

            if not self.track.is_road(x, y):
                continue

            ok = True
            for car in cars:
                if car.pos.distance_to((x, y)) < self.keepout:
                    ok = False
                    break

            if ok:
                return (x, y)

        return (self.width // 2, self.height // 2)

    def shuffle(self, cars=None):
        """Pindahkan semua cone ke posisi acak baru (dipakai antar-race)."""
        cars = cars or []
        for c in self.cones:
            c.pos.update(self._random_road_pos(cars))

    def draw(self, screen):
        if self.cone_img:
            for c in self.cones:
                rect = self.cone_img.get_rect(center=(int(c.pos.x), int(c.pos.y)))
                screen.blit(self.cone_img, rect)
        else:
            for c in self.cones:
                pygame.draw.circle(screen, (255, 120, 0), (int(c.pos.x), int(c.pos.y)), c.radius)

    def collide_car(self, car):
        car_r = getattr(car, "hit_radius", 12)
        for c in self.cones:
            # Kurangi area deteksi lebih banyak untuk mengurangi false positive
            collision_threshold = (car_r + c.radius) * 0.70  # 70% dari radius total
            if car.pos.distance_to(c.pos) <= collision_threshold:
                return True
        return False
