# racing_two_cars.py — RED=Rule, BLUE=Fuzzy
# Pastikan ada: assets/track.png

import pygame, math, csv, time, os

TRACK_IMAGE = "assets/track.png"
FPS = 60
SENSOR_LEN = 320

# ---------- util ----------
def clamp(x, a, b): return a if x < a else b if x > b else x
def lerp(a,b,t): return a+(b-a)*t

# ---------- Track ----------
class Track:
    """
    Jalan = aspal abu-abu (low saturation, mid brightness) ATAU garis biru.
    Sampling 3x3 agar robust ke noise/anti alias.
    """
    def __init__(self, img_path):
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Track image tidak ditemukan: {img_path}")
        self.surface = pygame.image.load(img_path)  # jangan .convert di sini
        self.width, self.height = self.surface.get_size()
        self.gray_tol  = 18
        self.gray_minB = 45
        self.gray_maxB = 185

    def _is_road_pixel(self, x, y):
        r,g,b = self.surface.get_at((x,y))[:3]
        mean = (r+g+b)/3
        gray_like = (abs(r-g) <= self.gray_tol and
                     abs(g-b) <= self.gray_tol and
                     self.gray_minB <= mean <= self.gray_maxB)
        blue_like = (b > 150 and r < 140 and g < 175)
        return gray_like or blue_like

    def is_road(self, x, y):
        if x < 1 or y < 1 or x >= self.width-1 or y >= self.height-1:
            return False
        # majority 3x3
        cnt = 0
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if self._is_road_pixel(x+dx, y+dy):
                    cnt += 1
        return cnt >= 5

    def draw(self, screen):
        # convert sesuai format display hanya saat draw
        screen.blit(self.surface.convert(), (0,0))

# ---------- Car ----------
class Car:
    def __init__(self, pos, color, track, name="Car", sensor_color=(0,255,0)):
        self.track = track
        self.name = name
        self.pos = pygame.Vector2(pos)
        self.heading = -math.pi/2
        self.vel = 0.0
        # fisika ringan
        self.max_speed   = 900
        self.accel       = 2100
        self.brake_accel = 3400
        self.drag        = 0.986
        # sensor
        self.sensor_angles = [-70,-40,-20,0,20,40,70]
        self.sensor_len = SENSOR_LEN
        self.sensor_color = sensor_color
        # sprite
        self.image = self._make_sprite(color)

    def _make_sprite(self, color):
        w,h = 40,64
        s = pygame.Surface((w,h), pygame.SRCALPHA)
        pygame.draw.rect(s, color, (8,2,24,60))
        pygame.draw.rect(s, (20,20,20), (4,10,4,44))
        pygame.draw.rect(s, (20,20,20), (32,10,4,44))
        pygame.draw.polygon(s, (245,245,245), [(20,0),(26,12),(14,12)])
        return s

    def _cast_ray(self, ang, maxlen):
        x,y = self.pos
        step = 3
        for d in range(0, int(maxlen), step):
            px = int(x + math.cos(ang)*d)
            py = int(y + math.sin(ang)*d)
            if not self.track.is_road(px, py):
                return d
        return maxlen

    def read_sensors(self):
        dists=[]
        for deg in self.sensor_angles:
            ang = self.heading + math.radians(deg)
            d = self._cast_ray(ang, self.sensor_len)
            dists.append(d)
        left  = min(dists[0], dists[1])
        lmid  = dists[2]
        front = dists[3]
        rmid  = dists[4]
        right = min(dists[5], dists[6])
        bias  = right - left
        return {"left":left,"lmid":lmid,"front":front,"rmid":rmid,"right":right,
                "bias":bias,"speed":self.vel}

    def update(self, dt, steer, throttle, brake):
        self.heading += steer * 2.2 * dt
        self.vel += throttle * self.accel * dt
        self.vel -= brake * self.brake_accel * dt
        self.vel *= self.drag
        self.vel = clamp(self.vel, 0, self.max_speed)
        self.pos.x += math.cos(self.heading)*self.vel*dt
        self.pos.y += math.sin(self.heading)*self.vel*dt

    def collide_wall(self):
        ix,iy = int(self.pos.x), int(self.pos.y)
        hit = not self.track.is_road(ix,iy)
        if hit:
            self.vel *= 0.5
            # dorong masuk ke area 'jalan' terdekat (pencarian kipas kecil)
            best = None; bestd = 1e9
            for a in range(-90,91,15):
                ang = math.radians(a)
                for d in range(18,80,6):
                    px = int(self.pos.x + math.cos(self.heading+ang)*d)
                    py = int(self.pos.y + math.sin(self.heading+ang)*d)
                    if self.track.is_road(px,py):
                        if d < bestd: bestd, best = d, (px,py, self.heading+ang)
                        break
            if best:
                self.pos.x, self.pos.y, self.heading = best
        return hit

    def draw(self, screen, debug=False):
        rot = pygame.transform.rotate(self.image, -math.degrees(self.heading)-90)
        rect = rot.get_rect(center=(self.pos.x, self.pos.y))
        screen.blit(rot, rect)
        if debug:
            for deg in self.sensor_angles:
                ang = self.heading + math.radians(deg)
                d = self._cast_ray(ang, self.sensor_len)
                end = (self.pos.x + math.cos(ang)*d, self.pos.y + math.sin(ang)*d)
                pygame.draw.line(screen, self.sensor_color, self.pos, end, 2)

# ---------- Controllers ----------
class RuleController:
    def act(self, s):
        # steer proporsional terhadap 'bias', dibatasi
        k_steer = 0.006
        steer = clamp(k_steer * s["bias"], -0.7, 0.7)

        # kecepatan target dari jarak depan & sisi
        front = s["front"]; side = min(s["lmid"], s["rmid"])
        # throttle lebih rendah kalau ruang depan/samping sempit
        t_front = clamp((front-60)/220, 0.0, 1.0)    # 0 saat <60px, 1 saat >=280px
        t_side  = clamp((side-60)/220,  0.0, 1.0)
        throttle = 0.35 + 0.65*min(t_front, t_side)

        brake = 0.0
        if front < 70:          # emergency
            brake, throttle = 1.0, 0.0
        elif front < 110:
            brake = 0.4*(110-front)/40

        return steer, throttle, brake

def tri(x, a, b, c):
    if x<=a or x>=c: return 0.0
    return (x-a)/(b-a) if x<b else (c-x)/(c-b)

class FuzzyController:
    def act(self, s):
        # normalisasi
        F = clamp(s["front"]/SENSOR_LEN, 0.0, 1.0)
        B = clamp((s["right"]-s["left"])/SENSOR_LEN, -1.0, 1.0)
        V = clamp(s["speed"]/900.0, 0.0, 1.0)

        near = tri(F,0.0,0.0,0.38); mid = tri(F,0.20,0.50,0.80); far = tri(F,0.60,1.0,1.0)
        left = tri(B,-1.0,-0.6,-0.1); center = tri(B,-0.25,0.0,0.25); right = tri(B,0.1,0.6,1.0)
        slow = tri(V,0.0,0.2,0.45); med = tri(V,0.35,0.55,0.75); fast = tri(V,0.65,0.9,1.0)

        rules = []
        # emergency brake
        rules.append(("brakeH","steerC","gasL", near))
        # keep center
        rules.append(("brake0","steerR","gasM", left))
        rules.append(("brake0","steerL","gasM", right))
        # go fast if clear & centered & not already fast
        rules.append(("brake0","steerC","gasH", min(far, center, 1.0-fast)))
        # moderate when mid clearance or already fast
        rules.append(("brakeL","steerC","gasM", max(mid*center, fast*center)))

        steer_map = {"L":-0.70,"SL":-0.35,"C":0.0,"SR":0.35,"R":0.70}
        gas_map   = {"H":0.95,"M":0.65,"L":0.40}
        brake_map = {"0":0.0,"L":0.3,"H":1.0}

        num_s=den_s=0.0; num_t=den_t=0.0; brake=0.0
        for bl, st, gs, w in rules:
            if w<=0: continue
            # steer
            if   st=="steerL":  num_s += steer_map["SL"]*w; den_s += w
            elif st=="steerR":  num_s += steer_map["SR"]*w; den_s += w
            else:               num_s += steer_map["C"] *w; den_s += w
            # throttle
            num_t += gas_map[gs[-1]]*w   # gasH/M/L -> ambil H/M/L
            den_t += w
            # brake (max)
            brake = max(brake, brake_map[bl[-1]]*w) # brakeH/L/0

        steer = (num_s/den_s) if den_s>0 else 0.0
        throttle = (num_t/den_t) if den_t>0 else 0.6
        return steer, throttle, clamp(brake,0,1)

# ---------- Metrics ----------
class Metrics:
    def __init__(self, label):
        self.label = label
        self.t=0.0; self.coll=0; self.corr=0; self.last_steer=0.0
        self.font = pygame.font.SysFont(None, 22)
    def update(self, dt, collided, steer):
        self.t += dt
        if collided: self.coll += 1
        if abs(steer - self.last_steer) > 0.35: self.corr += 1
        self.last_steer = steer
    def draw(self, screen, pos):
        txt = f"{self.label}: t={self.t:5.1f}s  collisions={self.coll}  corrections={self.corr}"
        screen.blit(self.font.render(txt, True, (255,255,255)), pos)
    def save_csv(self, path):
        with open(path,"w",newline="") as f:
            w=csv.writer(f); w.writerow(["time_s","collisions","corrections","label"])
            w.writerow([round(self.t,2), self.coll, self.corr, self.label])

# ---------- Main ----------
def main():
    pygame.init()
    track = Track(TRACK_IMAGE)
    screen = pygame.display.set_mode(track.surface.get_size())
    pygame.display.set_caption("Top-Down Racing AI — RED=Rule, BLUE=Fuzzy")
    clock = pygame.time.Clock()

    # default spawn (silakan geser pakai mode place)
    car_rule  = Car((260,110), (220,40,40), track, "RED (Rule)",  (255,80,80))
    car_fuzzy = Car((300,110), (40,130,235), track, "BLUE (Fuzzy)", (80,180,255))
    ctrl_rule, ctrl_fuzzy = RuleController(), FuzzyController()
    met_rule, met_fuzzy = Metrics("RED (Rule)"), Metrics("BLUE (Fuzzy)")

    def reset_game():
        nonlocal car_rule,car_fuzzy,ctrl_rule,ctrl_fuzzy,met_rule,met_fuzzy
        car_rule  = Car((car_rule.pos.x, car_rule.pos.y), (220,40,40), track, "RED (Rule)",  (255,80,80))
        car_fuzzy = Car((car_fuzzy.pos.x, car_fuzzy.pos.y), (40,130,235), track, "BLUE (Fuzzy)", (80,180,255))
        ctrl_rule, ctrl_fuzzy = RuleController(), FuzzyController()
        met_rule, met_fuzzy = Metrics("RED (Rule)"), Metrics("BLUE (Fuzzy)")

    # ------- placement mode (P) --------
    placing = False
    place_target = "rule"   # atau "fuzzy"
    rot_speed = math.radians(120)  # derajat/detik

    debug = True
    running = True
    while running:
        dt = clock.tick(FPS)/1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_d:    debug = not debug
                elif e.key == pygame.K_r:    reset_game()
                elif e.key == pygame.K_p:    placing = not placing
                elif placing and e.key == pygame.K_1: place_target = "rule"
                elif placing and e.key == pygame.K_2: place_target = "fuzzy"
                elif placing and e.key == pygame.K_RETURN: placing = False
            if placing and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx,my = e.pos
                if not track.is_road(mx,my):  # cegah spawn di rumput
                    continue
                if place_target == "rule":
                    car_rule.pos.update(mx,my)
                else:
                    car_fuzzy.pos.update(mx,my)

        # rotasi saat placement
        keys = pygame.key.get_pressed()
        if placing:
            dtheta = 0.0
            if keys[pygame.K_a]: dtheta -= rot_speed*dt
            if keys[pygame.K_d]: dtheta += rot_speed*dt
            target = car_rule if place_target=="rule" else car_fuzzy
            target.heading += dtheta

        # --- UPDATE saat tidak placing ---
        if not placing:
            # Rule
            s = car_rule.read_sensors()
            st,th,br = ctrl_rule.act(s)
            car_rule.update(dt, st, th, br)
            hit = car_rule.collide_wall()
            met_rule.update(dt, hit, st)
            # Fuzzy
            s = car_fuzzy.read_sensors()
            st,th,br = ctrl_fuzzy.act(s)
            car_fuzzy.update(dt, st, th, br)
            hit = car_fuzzy.collide_wall()
            met_fuzzy.update(dt, hit, st)

        # --- RENDER ---
        track.draw(screen)
        car_rule.draw(screen, debug=debug)
        car_fuzzy.draw(screen, debug=debug)
        met_rule.draw(screen, (20,20))
        met_fuzzy.draw(screen, (20,44))

        if placing:
            help_txt = "[PLACEMENT] Click=move | A/D=rotate | 1=RED 2=BLUE | Enter=OK"
            tip = f"target: {'RED' if place_target=='rule' else 'BLUE'}"
            font = pygame.font.SysFont(None, 24)
            screen.blit(font.render(help_txt, True,(255,255,0)), (20, track.height-48))
            screen.blit(font.render(tip, True,(255,255,0)), (20, track.height-24))

        pygame.display.flip()

    ts = int(time.time())
    met_rule.save_csv(f"run_rule_{ts}.csv")
    met_fuzzy.save_csv(f"run_fuzzy_{ts}.csv")
    pygame.quit()

if __name__ == "__main__":
    main()
