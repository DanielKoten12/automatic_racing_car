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
START_LINE_X = 490  # Posisi x garis start (putih)
FINISH_LAPS = 5  # Jumlah lap untuk menyelesaikan balapan




# ---------- Main ----------
def main():
    """Main game loop untuk racing AI"""
    pygame.init()
    track = Track(TRACK_IMAGE)
    screen = pygame.display.set_mode(track.surface.get_size())
    pygame.display.set_caption("Top-Down Racing AI — RED=Rule, BLUE=Fuzzy")
    clock = pygame.time.Clock()

    # Posisi start di sebelah kanan garis start, menghadap ke kanan (heading = 0)
    MAX_SPEED = 900  # Kecepatan maksimal yang sama untuk kedua mobil
    car_rule = Car((520, 110), (220, 40, 40), track, "RED (Rule)", (255, 80, 80), SENSOR_LEN)
    car_fuzzy = Car((520, 140), (40, 130, 235), track, "BLUE (Fuzzy)", (80, 180, 255), SENSOR_LEN)
    # Set heading menghadak ke kanan dan kecepatan maksimal yang sama
    car_rule.heading = 0
    car_fuzzy.heading = 0
    car_rule.max_speed = MAX_SPEED
    car_fuzzy.max_speed = MAX_SPEED
    ctrl_rule = RuleController(MAX_SPEED)
    ctrl_fuzzy = FuzzyController(SENSOR_LEN, MAX_SPEED)
    met_rule = Metrics("RED (Rule)")
    met_fuzzy = Metrics("BLUE (Fuzzy)")

    def reset_game():
        """Reset game dengan posisi mobil saat ini"""
        nonlocal car_rule, car_fuzzy, ctrl_rule, ctrl_fuzzy, met_rule, met_fuzzy, race_finished
        car_rule = Car(
            (520, 110),
            (220, 40, 40),
            track,
            "RED (Rule)",
            (255, 80, 80),
            SENSOR_LEN
        )
        car_fuzzy = Car(
            (520, 140),
            (40, 130, 235),
            track,
            "BLUE (Fuzzy)",
            (80, 180, 255),
            SENSOR_LEN
        )
        car_rule.heading = 0
        car_fuzzy.heading = 0
        car_rule.max_speed = MAX_SPEED
        car_fuzzy.max_speed = MAX_SPEED
        ctrl_rule = RuleController(MAX_SPEED)
        ctrl_fuzzy = FuzzyController(SENSOR_LEN, MAX_SPEED)
        met_rule = Metrics("RED (Rule)")
        met_fuzzy = Metrics("BLUE (Fuzzy)")
        race_finished = False

    # placement mode (P)
    placing = False
    place_target = "rule"  # atau "fuzzy"
    rot_speed = math.radians(120)  # derajat/detik

    debug = True
    running = True
    race_finished = False
    
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

        # update saat tidak placing dan balapan belum selesai
        if not placing and not race_finished:
            # Rule-based car
            s = car_rule.read_sensors()
            st, th, br = ctrl_rule.act(s)
            car_rule.update(dt, st, th, br)
            hit = car_rule.collide_wall()
            met_rule.update(dt, hit, st)
            
            # Deteksi melewati garis start untuk car_rule (dari kiri ke kanan)
            if car_rule.last_x < START_LINE_X and car_rule.pos.x >= START_LINE_X:
                # Hitung lap hanya jika sudah menjauh dari start (minimal sudah keliling)
                if met_rule.t > 3.0 and car_rule.lap_count < FINISH_LAPS:  # Jangan lewati FINISH_LAPS
                    car_rule.lap_count += 1
            car_rule.last_x = car_rule.pos.x

            # Fuzzy logic car
            s = car_fuzzy.read_sensors()
            st, th, br = ctrl_fuzzy.act(s)
            car_fuzzy.update(dt, st, th, br)
            hit = car_fuzzy.collide_wall()
            met_fuzzy.update(dt, hit, st)
            
            # Deteksi melewati garis start untuk car_fuzzy (dari kiri ke kanan)
            if car_fuzzy.last_x < START_LINE_X and car_fuzzy.pos.x >= START_LINE_X:
                # Hitung lap hanya jika sudah menjauh dari start (minimal sudah keliling)
                if met_fuzzy.t > 3.0 and car_fuzzy.lap_count < FINISH_LAPS:  # Jangan lewati FINISH_LAPS
                    car_fuzzy.lap_count += 1
            car_fuzzy.last_x = car_fuzzy.pos.x
            
            # Cek apakah balapan selesai (langsung setelah kedua mobil finish lap terakhir)
            if car_rule.lap_count >= FINISH_LAPS and car_fuzzy.lap_count >= FINISH_LAPS:
                race_finished = True

        # Render
        track.draw(screen)
        car_rule.draw(screen, debug=debug)
        car_fuzzy.draw(screen, debug=debug)
        
        # Tampilkan metrics dengan lap count
        font = pygame.font.SysFont(None, 22)
        txt_rule = f"RED: Lap {car_rule.lap_count}/{FINISH_LAPS} | Time: {met_rule.t:.1f}s | Crashes: {met_rule.coll}"
        txt_fuzzy = f"BLUE: Lap {car_fuzzy.lap_count}/{FINISH_LAPS} | Time: {met_fuzzy.t:.1f}s | Crashes: {met_fuzzy.coll}"
        screen.blit(font.render(txt_rule, True, (255, 100, 100)), (20, 20))
        screen.blit(font.render(txt_fuzzy, True, (100, 180, 255)), (20, 44))

        # Placement mode UI
        if placing:
            help_txt = "[PLACEMENT] Click=move | A/D=rotate | 1=RED 2=BLUE | Enter=OK"
            tip = f"target: {'RED' if place_target=='rule' else 'BLUE'}"
            font = pygame.font.SysFont(None, 24)
            screen.blit(font.render(help_txt, True, (255, 255, 0)), (20, track.height - 48))
            screen.blit(font.render(tip, True, (255, 255, 0)), (20, track.height - 24))
        
        # Race finished UI
        if race_finished:
            font_big = pygame.font.SysFont(None, 48)
            font_med = pygame.font.SysFont(None, 32)
            
            # Background gelap untuk hasil
            result_bg = pygame.Surface((600, 300))
            result_bg.set_alpha(220)
            result_bg.fill((20, 20, 20))
            screen.blit(result_bg, (track.width // 2 - 300, track.height // 2 - 150))
            
            # Judul
            title = font_big.render("RACE FINISHED!", True, (255, 255, 0))
            screen.blit(title, (track.width // 2 - title.get_width() // 2, track.height // 2 - 120))
            
            # Hasil RED
            y_offset = track.height // 2 - 60
            red_title = font_med.render("RED (Rule-Based):", True, (255, 100, 100))
            screen.blit(red_title, (track.width // 2 - 250, y_offset))
            red_time = font_med.render(f"Time: {met_rule.t:.2f}s", True, (255, 255, 255))
            screen.blit(red_time, (track.width // 2 - 250, y_offset + 30))
            red_crash = font_med.render(f"Crashes: {met_rule.coll}", True, (255, 255, 255))
            screen.blit(red_crash, (track.width // 2 - 250, y_offset + 60))
            
            # Hasil BLUE
            blue_title = font_med.render("BLUE (Fuzzy Logic):", True, (100, 180, 255))
            screen.blit(blue_title, (track.width // 2 - 250, y_offset + 110))
            blue_time = font_med.render(f"Time: {met_fuzzy.t:.2f}s", True, (255, 255, 255))
            screen.blit(blue_time, (track.width // 2 - 250, y_offset + 140))
            blue_crash = font_med.render(f"Crashes: {met_fuzzy.coll}", True, (255, 255, 255))
            screen.blit(blue_crash, (track.width // 2 - 250, y_offset + 170))
            
            # Instruksi
            inst = font.render("Press R to restart or ESC to quit", True, (255, 255, 0))
            screen.blit(inst, (track.width // 2 - inst.get_width() // 2, track.height // 2 + 110))

        pygame.display.flip()

    # Simpan metrics ke CSV
    ts = int(time.time())
    met_rule.save_csv(f"run_rule_{ts}.csv", car_rule.lap_count)
    met_fuzzy.save_csv(f"run_fuzzy_{ts}.csv", car_fuzzy.lap_count)
    
    # Tampilkan hasil akhir di console
    print("\n" + "="*50)
    print("RACE RESULTS")
    print("="*50)
    print(f"RED (Rule-Based):")
    print(f"  - Laps: {car_rule.lap_count}")
    print(f"  - Time: {met_rule.t:.2f}s")
    print(f"  - Crashes: {met_rule.coll}")
    print(f"\nBLUE (Fuzzy Logic):")
    print(f"  - Laps: {car_fuzzy.lap_count}")
    print(f"  - Time: {met_fuzzy.t:.2f}s")
    print(f"  - Crashes: {met_fuzzy.coll}")
    print("="*50)
    
    pygame.quit()


if __name__ == "__main__":
    main()
