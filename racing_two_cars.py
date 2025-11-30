# racing_two_cars.py — RED = Rule-Based, BLUE = Fuzzy
# Pastikan ada: assets/track_nascar.png (dari script pembuat track)

import pygame
import math
import time

# Import modular components
from track import Track
from car import Car
from rule_controller import RuleController
from fuzzy_controller import FuzzyController
from metrics import Metrics

# Konstanta
TRACK_IMAGE = "assets/track_nascar.png"   # bisa diganti ke "assets/track.png" kalau mau
FPS = 60
SENSOR_LEN = 320




# ---------- Main ----------
def main():
    """Main game loop untuk racing AI"""
    pygame.init()
    track = Track(TRACK_IMAGE)
    screen = pygame.display.set_mode(track.surface.get_size())
    pygame.display.set_caption("Top-Down Racing AI — RED=Rule, BLUE=Fuzzy")
    clock = pygame.time.Clock()

    # default spawn (bisa digeser pakai placement mode)
    car_rule = Car((260, 110), (220, 40, 40), track, "RED (Rule)", (255, 80, 80), SENSOR_LEN)
    car_fuzzy = Car((300, 110), (40, 130, 235), track, "BLUE (Fuzzy)", (80, 180, 255), SENSOR_LEN)
    ctrl_rule = RuleController()
    ctrl_fuzzy = FuzzyController(SENSOR_LEN)
    met_rule = Metrics("RED (Rule)")
    met_fuzzy = Metrics("BLUE (Fuzzy)")

    def reset_game():
        """Reset game dengan posisi mobil saat ini"""
        nonlocal car_rule, car_fuzzy, ctrl_rule, ctrl_fuzzy, met_rule, met_fuzzy
        car_rule = Car(
            (car_rule.pos.x, car_rule.pos.y),
            (220, 40, 40),
            track,
            "RED (Rule)",
            (255, 80, 80),
            SENSOR_LEN
        )
        car_fuzzy = Car(
            (car_fuzzy.pos.x, car_fuzzy.pos.y),
            (40, 130, 235),
            track,
            "BLUE (Fuzzy)",
            (80, 180, 255),
            SENSOR_LEN
        )
        ctrl_rule = RuleController()
        ctrl_fuzzy = FuzzyController(SENSOR_LEN)
        met_rule = Metrics("RED (Rule)")
        met_fuzzy = Metrics("BLUE (Fuzzy)")

    # placement mode (P)
    placing = False
    place_target = "rule"  # atau "fuzzy"
    rot_speed = math.radians(120)  # derajat/detik

    debug = True
    running = True
    
    while running:
        dt = clock.tick(FPS) / 1000.0

        # Event handling
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_d:
                    debug = not debug
                elif e.key == pygame.K_r:
                    reset_game()
                elif e.key == pygame.K_p:
                    placing = not placing
                elif placing and e.key == pygame.K_1:
                    place_target = "rule"
                elif placing and e.key == pygame.K_2:
                    place_target = "fuzzy"
                elif placing and e.key == pygame.K_RETURN:
                    placing = False
            elif placing and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # cegah spawn di rumput
                if not track.is_road(mx, my):
                    continue
                if place_target == "rule":
                    car_rule.pos.update(mx, my)
                else:
                    car_fuzzy.pos.update(mx, my)

        # rotasi saat placement
        keys = pygame.key.get_pressed()
        if placing:
            dtheta = 0.0
            if keys[pygame.K_a]:
                dtheta -= rot_speed * dt
            if keys[pygame.K_d]:
                dtheta += rot_speed * dt
            target = car_rule if place_target == "rule" else car_fuzzy
            target.heading += dtheta

        # update saat tidak placing
        if not placing:
            # Rule-based car
            s = car_rule.read_sensors()
            st, th, br = ctrl_rule.act(s)
            car_rule.update(dt, st, th, br)
            hit = car_rule.collide_wall()
            met_rule.update(dt, hit, st)

            # Fuzzy logic car
            s = car_fuzzy.read_sensors()
            st, th, br = ctrl_fuzzy.act(s)
            car_fuzzy.update(dt, st, th, br)
            hit = car_fuzzy.collide_wall()
            met_fuzzy.update(dt, hit, st)

        # Render
        track.draw(screen)
        car_rule.draw(screen, debug=debug)
        car_fuzzy.draw(screen, debug=debug)
        met_rule.draw(screen, (20, 20))
        met_fuzzy.draw(screen, (20, 44))

        # Placement mode UI
        if placing:
            help_txt = "[PLACEMENT] Click=move | A/D=rotate | 1=RED 2=BLUE | Enter=OK"
            tip = f"target: {'RED' if place_target=='rule' else 'BLUE'}"
            font = pygame.font.SysFont(None, 24)
            screen.blit(font.render(help_txt, True, (255, 255, 0)), (20, track.height - 48))
            screen.blit(font.render(tip, True, (255, 255, 0)), (20, track.height - 24))

        pygame.display.flip()

    # Simpan metrics ke CSV
    ts = int(time.time())
    met_rule.save_csv(f"run_rule_{ts}.csv")
    met_fuzzy.save_csv(f"run_fuzzy_{ts}.csv")
    pygame.quit()


if __name__ == "__main__":
    main()
