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
CONE_RADIUS = 8  # Diperkecil dari 10 agar tidak terlalu sering crash
CONE_KEEPOUT = 40  # Diperkecil dari 60 agar deteksi tabrakan lebih akurat


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
    
    # ===== RACE HISTORY TRACKING =====
    race_history = []  # List untuk menyimpan hasil setiap race
    race_number = 0

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
                    # Simpan hasil race saat ini jika race sudah selesai
                    if race_finished:
                        race_number += 1
                        race_history.append({
                            "race": race_number,
                            "red_time": met_rule.finish_time,
                            "red_laps": car_rule.lap_count,
                            "red_crashes": met_rule.coll,
                            "blue_time": met_fuzzy.finish_time,
                            "blue_laps": car_fuzzy.lap_count,
                            "blue_crashes": met_fuzzy.coll
                        })
                        # Acak cone untuk race baru
                        cones.shuffle(cars=[car_rule, car_fuzzy])

                    car_rule, car_fuzzy, ctrl_rule, ctrl_fuzzy, met_rule, met_fuzzy = build_cars_and_system()
                    race_finished = False
                    placing = False

                elif e.key == pygame.K_t:
                    # Tombol T: Restart dan SELALU mengacak cone (bahkan di tengah race)
                    if race_finished:
                        race_number += 1
                        race_history.append({
                            "race": race_number,
                            "red_time": met_rule.finish_time,
                            "red_laps": car_rule.lap_count,
                            "red_crashes": met_rule.coll,
                            "blue_time": met_fuzzy.finish_time,
                            "blue_laps": car_fuzzy.lap_count,
                            "blue_crashes": met_fuzzy.coll
                        })
                    
                    # Selalu acak cone dengan tombol T
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
        if not placing:
            # Cek jika kedua mobil sudah finish, hentikan semua update
            if car_rule.finished and car_fuzzy.finished and not race_finished:
                race_finished = True

            # ---------- RED (Rule-Based) ----------
            if not car_rule.finished:
                s = car_rule.read_sensors(cones=cones.cones, other_car=car_fuzzy)
                st, th, br = ctrl_rule.act(s)
                car_rule.update(dt, st, th, br)

                hit_wall = car_rule.collide_wall()
                
                # Logika tabrakan cone dengan cooldown
                hit_cone = False
                if car_rule.cone_hit_cooldown <= 0:
                    if cones.collide_car(car_rule):
                        hit_cone = True
                        car_rule.vel *= 0.4  # Hanya kurangi kecepatan
                        car_rule.cone_hit_cooldown = 1.0 # Cooldown 1 detik
                
                met_rule.update(dt, hit_wall or hit_cone, st)

                # Cek finish lap
                if car_rule.last_x < START_LINE_X and car_rule.pos.x >= START_LINE_X:
                    if met_rule.t > 3.0:
                        car_rule.lap_count += 1
                        if car_rule.lap_count >= FINISH_LAPS:
                            car_rule.finished = True
                            met_rule.finish_time = met_rule.t # Catat waktu finish
                car_rule.last_x = car_rule.pos.x

            # ---------- BLUE (Fuzzy) ----------
            if not car_fuzzy.finished:
                s = car_fuzzy.read_sensors(cones=cones.cones, other_car=car_rule)
                st, th, br = ctrl_fuzzy.act(s)
                car_fuzzy.update(dt, st, th, br)

                hit_wall = car_fuzzy.collide_wall()

                # Logika tabrakan cone dengan cooldown
                hit_cone = False
                if car_fuzzy.cone_hit_cooldown <= 0:
                    if cones.collide_car(car_fuzzy):
                        hit_cone = True
                        car_fuzzy.vel *= 0.4 # Hanya kurangi kecepatan
                        car_fuzzy.cone_hit_cooldown = 1.0 # Cooldown 1 detik

                met_fuzzy.update(dt, hit_wall or hit_cone, st)

                # Cek finish lap
                if car_fuzzy.last_x < START_LINE_X and car_fuzzy.pos.x >= START_LINE_X:
                    if met_fuzzy.t > 3.0:
                        car_fuzzy.lap_count += 1
                        if car_fuzzy.lap_count >= FINISH_LAPS:
                            car_fuzzy.finished = True
                            met_fuzzy.finish_time = met_fuzzy.t # Catat waktu finish
                car_fuzzy.last_x = car_fuzzy.pos.x

            # ---------- Tabrakan Antar Mobil ----------
            if not race_finished and car_rule.collides_with_car(car_fuzzy):
                # Update metrics untuk kedua mobil
                met_rule.update(dt, True, 0)
                met_fuzzy.update(dt, True, 0)
                
                # Beri efek pelan pada kedua mobil
                car_rule.vel *= 0.3
                car_fuzzy.vel *= 0.3

        # RENDER
        track.draw(screen)
        cones.draw(screen)

        car_rule.draw(screen, debug=debug, cones=cones.cones)
        car_fuzzy.draw(screen, debug=debug, cones=cones.cones)

        # Tampilkan waktu finish jika sudah selesai, jika tidak, tampilkan waktu berjalan
        time_rule_str = f"{met_rule.finish_time:.1f}s" if car_rule.finished else f"{met_rule.t:.1f}s"
        time_fuzzy_str = f"{met_fuzzy.finish_time:.1f}s" if car_fuzzy.finished else f"{met_fuzzy.t:.1f}s"

        txt_rule = f"RED: Lap {min(car_rule.lap_count, FINISH_LAPS)}/{FINISH_LAPS} | Time: {time_rule_str} | Crashes: {met_rule.coll}"
        txt_fuzzy = f"BLUE: Lap {min(car_fuzzy.lap_count, FINISH_LAPS)}/{FINISH_LAPS} | Time: {time_fuzzy_str} | Crashes: {met_fuzzy.coll}"
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
            red_time = font_med.render(f"Time: {met_rule.finish_time:.2f}s", True, (255, 255, 255))
            screen.blit(red_time, (track.width // 2 - 250, y_offset + 30))
            red_crash = font_med.render(f"Crashes: {met_rule.coll}", True, (255, 255, 255))
            screen.blit(red_crash, (track.width // 2 - 250, y_offset + 60))

            blue_title = font_med.render("BLUE (Fuzzy Logic):", True, (100, 180, 255))
            screen.blit(blue_title, (track.width // 2 - 250, y_offset + 110))
            blue_time = font_med.render(f"Time: {met_fuzzy.finish_time:.2f}s", True, (255, 255, 255))
            screen.blit(blue_time, (track.width // 2 - 250, y_offset + 140))
            blue_crash = font_med.render(f"Crashes: {met_fuzzy.coll}", True, (255, 255, 255))
            screen.blit(blue_crash, (track.width // 2 - 250, y_offset + 170))

            inst = font_small.render("Press R to start next race", True, (255, 255, 0))
            screen.blit(inst, (track.width // 2 - inst.get_width() // 2, track.height // 2 + 110))

        pygame.display.flip()

    #SIMPAN METRICS
    ts = int(time.time())
    met_rule.save_csv(f"run_rule_{ts}.csv", car_rule.lap_count)
    met_fuzzy.save_csv(f"run_fuzzy_{ts}.csv", car_fuzzy.lap_count)

    # Simpan race terakhir jika belum disimpan
    if race_finished and race_number == len(race_history):
        race_number += 1
        race_history.append({
            "race": race_number,
            "red_time": met_rule.finish_time,
            "red_laps": car_rule.lap_count,
            "red_crashes": met_rule.coll,
            "blue_time": met_fuzzy.finish_time,
            "blue_laps": car_fuzzy.lap_count,
            "blue_crashes": met_fuzzy.coll
        })

    # TABEL EVALUASI
    print("\n" + "=" * 120)
    print(" " * 45 + "RACE EVALUATION RESULTS")
    print("=" * 120)
    
    if race_history:
        # Header tabel
        header = "| Race | " + "RED Car (Rule-Based)" + " " * 10 + "| " + "BLUE Car (Fuzzy Logic)" + " " * 10 + "| Winner     |"
        separator = "-" * 120
        subheader = "|  No. | Time (s) | Laps | Crashes | Time (s) | Laps | Crashes | Winner     |"
        
        print(header)
        print(separator)
        print(subheader)
        print(separator)
        
        # Data setiap race
        for race in race_history:
            # Tentukan pemenang
            if race["red_laps"] > race["blue_laps"]:
                winner = "RED"
            elif race["blue_laps"] > race["red_laps"]:
                winner = "BLUE"
            elif race["red_laps"] == race["blue_laps"] and race["red_laps"] >= FINISH_LAPS:
                # Keduanya finish, bandingkan waktu
                if race["red_time"] < race["blue_time"]:
                    winner = "RED"
                elif race["blue_time"] < race["red_time"]:
                    winner = "BLUE"
                else:
                    winner = "DRAW"
            else:
                winner = "NONE"
            
            row = f"|  {race['race']:2d}  | {race['red_time']:8.2f} | {race['red_laps']:4d} | {race['red_crashes']:7d} | {race['blue_time']:8.2f} | {race['blue_laps']:4d} | {race['blue_crashes']:7d} | {winner:10s} |"
            print(row)
        
        print(separator)
        
        # Summary statistik
        total_races = len(race_history)
        red_wins = sum(1 for r in race_history if (
            r["red_laps"] > r["blue_laps"] or 
            (r["red_laps"] == r["blue_laps"] and r["red_laps"] >= FINISH_LAPS and r["red_time"] < r["blue_time"])
        ))
        blue_wins = sum(1 for r in race_history if (
            r["blue_laps"] > r["red_laps"] or 
            (r["blue_laps"] == r["red_laps"] and r["blue_laps"] >= FINISH_LAPS and r["blue_time"] < r["red_time"])
        ))
        
        avg_red_time = sum(r["red_time"] for r in race_history) / total_races
        avg_blue_time = sum(r["blue_time"] for r in race_history) / total_races
        total_red_crashes = sum(r["red_crashes"] for r in race_history)
        total_blue_crashes = sum(r["blue_crashes"] for r in race_history)
        
        print("\nSUMMARY:")
        print(f"  Total Races: {total_races}")
        print(f"  RED Wins: {red_wins} | BLUE Wins: {blue_wins}")
        print(f"  RED Avg Time: {avg_red_time:.2f}s | BLUE Avg Time: {avg_blue_time:.2f}s")
        print(f"  RED Total Crashes: {total_red_crashes} | BLUE Total Crashes: {total_blue_crashes}")
        print("=" * 120)
    else:
        print("No races completed.")
        print("=" * 120)

    pygame.quit()


if __name__ == "__main__":
    main()
