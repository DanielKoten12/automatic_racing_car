# racing_two_cars.py — RED = Rule-Based, BLUE = Fuzzy
# Update sesuai request:
# - Cone pakai assets/cone.png
# - Cone hanya berubah posisi antar race (setelah finish)
# - Jika restart sebelum finish, cone tetap
# - Total cone = 10

import pygame
import math
import time

from track import Track
from car import Car
from rule_controller import RuleController
from fuzzy_controller import FuzzyController
from metrics import Metrics
from cones import ConeManager


# ================== KONSTANTA ==================
TRACK_IMAGE = "assets/track_nascar.png"  # gunakan versi TANPA cone statis
FPS = 60
SENSOR_LEN = 320

START_LINE_X = 490
FINISH_LAPS = 5

MAX_SPEED = 900

CONE_COUNT = 10
CONE_RADIUS = 10
CONE_KEEPOUT = 60


def main():
    pygame.init()

    track = Track(TRACK_IMAGE)
    screen = pygame.display.set_mode(track.surface.get_size())
    pygame.display.set_caption("Top-Down Racing AI — RED=Rule, BLUE=Fuzzy")
    clock = pygame.time.Clock()

    # Fonts
    font_small = pygame.font.SysFont(None, 22)
    font_ui = pygame.font.SysFont(None, 24)
    font_big = pygame.font.SysFont(None, 48)
    font_med = pygame.font.SysFont(None, 32)

    # ===== init cones sekali =====
    cones = ConeManager(
        track,
        n=CONE_COUNT,
        radius=CONE_RADIUS,
        keepout=CONE_KEEPOUT,
        image_path="assets/cone.png"
    )

    def build_cars_and_system():
        """Reset mobil + controller + metrics, tapi cones ikut dari luar."""
        car_rule = Car((520, 110), (220, 40, 40), track, "RED (Rule)", (255, 80, 80), SENSOR_LEN)
        car_fuzzy = Car((520, 140), (40, 130, 235), track, "BLUE (Fuzzy)", (80, 180, 255), SENSOR_LEN)

        # start menghadap kanan
        car_rule.heading = 0
        car_fuzzy.heading = 0

        car_rule.max_speed = MAX_SPEED
        car_fuzzy.max_speed = MAX_SPEED

        ctrl_rule = RuleController(MAX_SPEED)
        ctrl_fuzzy = FuzzyController(SENSOR_LEN, MAX_SPEED)

        met_rule = Metrics("RED (Rule)")
        met_fuzzy = Metrics("BLUE (Fuzzy)")

        return car_rule, car_fuzzy, ctrl_rule, ctrl_fuzzy, met_rule, met_fuzzy

    car_rule, car_fuzzy, ctrl_rule, ctrl_fuzzy, met_rule, met_fuzzy = build_cars_and_system()

    # placement mode
    placing = False
    place_target = "rule"  # "rule" | "fuzzy"
    rot_speed = math.radians(120)

    debug = True
    running = True
    race_finished = False

    while running:
        dt = clock.tick(FPS) / 1000.0

        # ================== EVENT ==================
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False

                elif e.key == pygame.K_d:
                    debug = not debug

                elif e.key == pygame.K_p:
                    placing = not placing

                elif e.key == pygame.K_1 and placing:
                    place_target = "rule"

                elif e.key == pygame.K_2 and placing:
                    place_target = "fuzzy"

                elif e.key == pygame.K_RETURN and placing:
                    placing = False

                elif e.key == pygame.K_r:
                    # RULE UTAMA:
                    # - kalau race sudah finish -> cones diacak ulang
                    # - kalau belum finish -> cones tetap
                    if race_finished:
                        cones.shuffle(cars=[car_rule, car_fuzzy])

                    car_rule, car_fuzzy, ctrl_rule, ctrl_fuzzy, met_rule, met_fuzzy = build_cars_and_system()
                    race_finished = False
                    placing = False

            elif placing and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                if not track.is_road(mx, my):
                    continue

                if place_target == "rule":
                    car_rule.pos.update(mx, my)
                else:
                    car_fuzzy.pos.update(mx, my)

        # ================== ROTASI PLACEMENT ==================
        keys = pygame.key.get_pressed()
        if placing:
            dtheta = 0.0
            if keys[pygame.K_a]:
                dtheta -= rot_speed * dt
            if keys[pygame.K_d]:
                dtheta += rot_speed * dt

            target = car_rule if place_target == "rule" else car_fuzzy
            target.heading += dtheta

        # ================== UPDATE GAME ==================
        if not placing and not race_finished:
            # ---------- RED ----------
            s = car_rule.read_sensors(cones=cones.cones)
            st, th, br = ctrl_rule.act(s)
            car_rule.update(dt, st, th, br)

            hit_wall = car_rule.collide_wall()
            hit_cone = cones.collide_car(car_rule)
            hit = hit_wall or hit_cone
            if hit_cone:
                car_rule.vel *= 0.3

            met_rule.update(dt, hit, st)

            if car_rule.last_x < START_LINE_X and car_rule.pos.x >= START_LINE_X:
                if met_rule.t > 3.0 and car_rule.lap_count < FINISH_LAPS:
                    car_rule.lap_count += 1
            car_rule.last_x = car_rule.pos.x

            # ---------- BLUE ----------
            s = car_fuzzy.read_sensors(cones=cones.cones)
            st, th, br = ctrl_fuzzy.act(s)
            car_fuzzy.update(dt, st, th, br)

            hit_wall = car_fuzzy.collide_wall()
            hit_cone = cones.collide_car(car_fuzzy)
            hit = hit_wall or hit_cone
            if hit_cone:
                car_fuzzy.vel *= 0.3

            met_fuzzy.update(dt, hit, st)

            if car_fuzzy.last_x < START_LINE_X and car_fuzzy.pos.x >= START_LINE_X:
                if met_fuzzy.t > 3.0 and car_fuzzy.lap_count < FINISH_LAPS:
                    car_fuzzy.lap_count += 1
            car_fuzzy.last_x = car_fuzzy.pos.x

            if car_rule.lap_count >= FINISH_LAPS and car_fuzzy.lap_count >= FINISH_LAPS:
                race_finished = True

        # ================== RENDER ==================
        track.draw(screen)
        cones.draw(screen)

        car_rule.draw(screen, debug=debug, cones=cones.cones)
        car_fuzzy.draw(screen, debug=debug, cones=cones.cones)

        txt_rule = f"RED: Lap {car_rule.lap_count}/{FINISH_LAPS} | Time: {met_rule.t:.1f}s | Crashes: {met_rule.coll}"
        txt_fuzzy = f"BLUE: Lap {car_fuzzy.lap_count}/{FINISH_LAPS} | Time: {met_fuzzy.t:.1f}s | Crashes: {met_fuzzy.coll}"
        screen.blit(font_small.render(txt_rule, True, (255, 100, 100)), (20, 20))
        screen.blit(font_small.render(txt_fuzzy, True, (100, 180, 255)), (20, 44))

        if placing:
            help_txt = "[PLACEMENT] Click=move | A/D=rotate | 1=RED 2=BLUE | Enter=OK"
            tip = f"target: {'RED' if place_target=='rule' else 'BLUE'}"
            screen.blit(font_ui.render(help_txt, True, (255, 255, 0)), (20, track.height - 48))
            screen.blit(font_ui.render(tip, True, (255, 255, 0)), (20, track.height - 24))

        if race_finished:
            result_bg = pygame.Surface((600, 300))
            result_bg.set_alpha(220)
            result_bg.fill((20, 20, 20))
            screen.blit(result_bg, (track.width // 2 - 300, track.height // 2 - 150))

            title = font_big.render("RACE FINISHED!", True, (255, 255, 0))
            screen.blit(title, (track.width // 2 - title.get_width() // 2, track.height // 2 - 120))

            y_offset = track.height // 2 - 60

            red_title = font_med.render("RED (Rule-Based):", True, (255, 100, 100))
            screen.blit(red_title, (track.width // 2 - 250, y_offset))
            red_time = font_med.render(f"Time: {met_rule.t:.2f}s", True, (255, 255, 255))
            screen.blit(red_time, (track.width // 2 - 250, y_offset + 30))
            red_crash = font_med.render(f"Crashes: {met_rule.coll}", True, (255, 255, 255))
            screen.blit(red_crash, (track.width // 2 - 250, y_offset + 60))

            blue_title = font_med.render("BLUE (Fuzzy Logic):", True, (100, 180, 255))
            screen.blit(blue_title, (track.width // 2 - 250, y_offset + 110))
            blue_time = font_med.render(f"Time: {met_fuzzy.t:.2f}s", True, (255, 255, 255))
            screen.blit(blue_time, (track.width // 2 - 250, y_offset + 140))
            blue_crash = font_med.render(f"Crashes: {met_fuzzy.coll}", True, (255, 255, 255))
            screen.blit(blue_crash, (track.width // 2 - 250, y_offset + 170))

            inst = font_small.render("Press R to start next race", True, (255, 255, 0))
            screen.blit(inst, (track.width // 2 - inst.get_width() // 2, track.height // 2 + 110))

        pygame.display.flip()

    # ================== SIMPAN METRICS ==================
    ts = int(time.time())
    met_rule.save_csv(f"run_rule_{ts}.csv", car_rule.lap_count)
    met_fuzzy.save_csv(f"run_fuzzy_{ts}.csv", car_fuzzy.lap_count)

    print("\n" + "=" * 50)
    print("RACE RESULTS")
    print("=" * 50)
    print("RED (Rule-Based):")
    print(f"  - Laps: {car_rule.lap_count}")
    print(f"  - Time: {met_rule.t:.2f}s")
    print(f"  - Crashes: {met_rule.coll}")
    print("\nBLUE (Fuzzy Logic):")
    print(f"  - Laps: {car_fuzzy.lap_count}")
    print(f"  - Time: {met_fuzzy.t:.2f}s")
    print(f"  - Crashes: {met_fuzzy.coll}")
    print("=" * 50)

    pygame.quit()


if __name__ == "__main__":
    main()
