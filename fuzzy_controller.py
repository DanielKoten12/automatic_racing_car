# fuzzy_controller.py
"""Fuzzy Logic Controller untuk mobil balap"""

from utils import clamp


def tri(x, a, b, c):
    """
    Fungsi membership triangular
    
    Args:
        x: nilai input
        a, b, c: parameter triangular (kiri, tengah, kanan)
    
    Returns:
        float: membership value [0, 1]
    """
    if x <= a or x >= c:
        return 0.0
    return (x - a) / (b - a) if x < b else (c - x) / (c - b)


class FuzzyController:
    """Controller berbasis logika fuzzy untuk mobil balap"""
    
    def __init__(self, sensor_len=320, max_speed=900):
        """
        Inisialisasi parameter fuzzy controller
        
        Args:
            sensor_len: panjang sensor maksimal
            max_speed: kecepatan maksimal mobil
        """
        self.sensor_len = sensor_len
        self.max_speed = max_speed
        self.k_center = 0.3  # konstanta koreksi ke tengah (dikurangi untuk lebih smooth)
        self.k_wall_avoid = 0.5  # konstanta untuk menghindari dinding samping
    
    def act(self, s):
        """
        Menentukan aksi berdasarkan fuzzy logic dengan rules tambahan untuk menghindari tabrakan
        
        Args:
            s (dict): Sensor readings dengan keys:
                - far_left, left, lmid, front, rmid, right, far_right: jarak sensor
                - bias: selisih right - left
                - speed: kecepatan saat ini
        
        Returns:
            tuple: (steer, throttle, brake)
        """
        # normalisasi sensor
        F = clamp(s["front"] / self.sensor_len, 0.0, 1.0)  # jarak depan
        L = clamp(s["left"] / self.sensor_len, 0.0, 1.0)  # jarak kiri
        R = clamp(s["right"] / self.sensor_len, 0.0, 1.0)  # jarak kanan
        FL = clamp(s["far_left"] / self.sensor_len, 0.0, 1.0)  # jarak kiri jauh
        FR = clamp(s["far_right"] / self.sensor_len, 0.0, 1.0)  # jarak kanan jauh
        LM = clamp(s["lmid"] / self.sensor_len, 0.0, 1.0)  # jarak kiri-tengah
        RM = clamp(s["rmid"] / self.sensor_len, 0.0, 1.0)  # jarak kanan-tengah
        B = clamp((s["right"] - s["left"]) / self.sensor_len, -1.0, 1.0)  # bias kiri/kanan
        V = clamp(s["speed"] / self.max_speed, 0.0, 1.0)  # kecepatan relatif
        
        # Deteksi minimum clearance samping
        min_side = min(L, R, LM, RM)

        # membership jarak depan (lebih sensitif)
        very_near = tri(F, 0.0, 0.0, 0.25)
        near = tri(F, 0.15, 0.30, 0.45)
        mid = tri(F, 0.35, 0.55, 0.75)
        far = tri(F, 0.65, 1.0, 1.0)

        # membership posisi kiri/kanan (center lebih sempit untuk kontrol lebih baik)
        far_left_pos = tri(B, -1.0, -0.8, -0.4)
        left_pos = tri(B, -0.7, -0.4, -0.15)
        center = tri(B, -0.25, 0.0, 0.25)
        right_pos = tri(B, 0.15, 0.4, 0.7)
        far_right_pos = tri(B, 0.4, 0.8, 1.0)

        # membership kecepatan (lebih konservatif)
        very_slow = tri(V, 0.0, 0.0, 0.25)
        slow = tri(V, 0.15, 0.35, 0.55)
        med = tri(V, 0.45, 0.65, 0.80)
        fast = tri(V, 0.70, 0.90, 1.0)
        
        # membership jarak samping (untuk wall avoidance)
        side_critical = tri(min_side, 0.0, 0.0, 0.20)
        side_close = tri(min_side, 0.10, 0.25, 0.40)
        side_safe = tri(min_side, 0.30, 1.0, 1.0)

        rules = []

        # === EMERGENCY RULES (prioritas tertinggi) ===
        # 1) Emergency brake: sangat dekat & cepat
        w1 = min(very_near, max(fast, med))
        if w1 > 0:
            rules.append(("brakeH", "steerC", "gasL", w1 * 1.5))

        # 2) Critical side distance + speed -> brake & correct
        w2 = min(side_critical, max(med, fast))
        if w2 > 0:
            rules.append(("brakeM", "steerC", "gasL", w2 * 1.3))

        # === BRAKE & SLOW DOWN RULES ===
        # 3) Dekat & cepat -> rem sedang
        w3 = min(near, fast)
        if w3 > 0:
            rules.append(("brakeM", "steerC", "gasL", w3))

        # 4) Dekat tapi lambat -> rem ringan, gas rendah
        w4 = min(near, max(very_slow, slow))
        if w4 > 0:
            rules.append(("brakeL", "steerC", "gasL", w4))

        # 5) Jarak sedang & cepat -> rem ringan preventif
        w5 = min(mid, fast)
        if w5 > 0:
            rules.append(("brakeL", "steerC", "gasM", w5))

        # === SPEED CONTROL RULES ===
        # 6) Jauh & center & tidak terlalu cepat -> gas tinggi
        w6 = min(far, center, side_safe, max(very_slow, slow, med))
        if w6 > 0:
            rules.append(("brake0", "steerC", "gasH", w6))

        # 7) Jarak sedang & center -> gas sedang
        w7 = min(mid, center, side_safe, max(very_slow, slow, med))
        if w7 > 0:
            rules.append(("brake0", "steerC", "gasM", w7))

        # 8) Side close -> reduce speed
        w8 = min(side_close, max(med, fast))
        if w8 > 0:
            rules.append(("brakeL", "steerC", "gasM", w8))

        # === STEERING CORRECTION RULES ===
        # 9) Sangat ke kiri -> belok kanan kuat, slow down
        w9 = min(far_left_pos, side_safe)
        if w9 > 0:
            rules.append(("brakeL", "steerR", "gasM", w9))

        # 10) Ke kiri -> belok kanan sedang
        w10 = min(left_pos, side_safe)
        if w10 > 0:
            rules.append(("brake0", "steerR", "gasM", w10))

        # 11) Sangat ke kanan -> belok kiri kuat, slow down
        w11 = min(far_right_pos, side_safe)
        if w11 > 0:
            rules.append(("brakeL", "steerL", "gasM", w11))

        # 12) Ke kanan -> belok kiri sedang
        w12 = min(right_pos, side_safe)
        if w12 > 0:
            rules.append(("brake0", "steerL", "gasM", w12))

        # === CORNER DETECTION & HANDLING ===
        # 13) Tikungan tajam kiri (front dekat, kanan aman, kiri sempit)
        w13 = min(near, tri(R, 0.4, 1.0, 1.0), tri(L, 0.0, 0.0, 0.3))
        if w13 > 0:
            rules.append(("brakeM", "steerR", "gasL", w13 * 1.2))

        # 14) Tikungan tajam kanan (front dekat, kiri aman, kanan sempit)
        w14 = min(near, tri(L, 0.4, 1.0, 1.0), tri(R, 0.0, 0.0, 0.3))
        if w14 > 0:
            rules.append(("brakeM", "steerL", "gasL", w14 * 1.2))

        # peta defuzz (dengan lebih banyak level)
        steer_map = {"steerL": -0.75, "steerC": 0.0, "steerR": 0.75}
        gas_map = {"gasL": 0.30, "gasM": 0.60, "gasH": 0.90}
        brake_map = {"brake0": 0.0, "brakeL": 0.35, "brakeM": 0.65, "brakeH": 1.0}

        num_s = den_s = 0.0
        num_t = den_t = 0.0
        brake = 0.0

        for bl, st, gs, w in rules:
            if w <= 0:
                continue
            num_s += steer_map[st] * w
            den_s += w
            num_t += gas_map[gs] * w
            den_t += w
            brake = max(brake, brake_map[bl] * w)

        # defuzz
        steer_fuzzy = (num_s / den_s) if den_s > 0 else 0.0
        throttle = (num_t / den_t) if den_t > 0 else 0.5

        # koreksi halus ke tengah pakai bias B langsung
        steer_center = clamp(self.k_center * B, -0.35, 0.35)
        
        # wall avoidance correction berdasarkan sensor samping
        wall_correction = 0.0
        if L < 0.25:  # dinding kiri terlalu dekat
            wall_correction += self.k_wall_avoid * (0.25 - L)
        if R < 0.25:  # dinding kanan terlalu dekat
            wall_correction -= self.k_wall_avoid * (0.25 - R)
        
        # kombinasi steering dengan batas lebih ketat
        steer = clamp(steer_fuzzy + steer_center + wall_correction, -0.85, 0.85)
        
        # reduce throttle jika sedang steering tajam atau brake aktif
        if abs(steer) > 0.5 or brake > 0.3:
            throttle *= 0.75

        return steer, throttle, clamp(brake, 0.0, 1.0)
