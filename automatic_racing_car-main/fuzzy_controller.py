# fuzzy_controller.py
"""
Fuzzy Logic Controller - DECISIVE AVOIDANCE
Fitur Utama:
1. Indecision Breaker: Memaksa belok jika sensor kiri & kanan seimbang tapi depan buntu.
2. Dynamic Sensitivity: Setir jadi sangat sensitif saat pelan (untuk manuver cone).
3. Safety Speed: Melambat otomatis saat mendekati rintangan.
"""

from utils import clamp

class FuzzyController:
    def __init__(self, sensor_len=320, max_speed=900):
        self.sensor_len = sensor_len
        self.max_speed = max_speed
        
        # Variabel untuk logika mundur darurat
        self.stuck_timer = 0
        self.reversing = False
        self.reverse_frame = 0

    def act(self, s):
        # ===========================
        # 1. NORMALISASI SENSOR
        # ===========================
        # 0.0 = Nempel (Bahaya), 1.0 = Jauh (Aman)
        
        # Sensor Depan
        F = clamp(s["front"] / self.sensor_len, 0.0, 1.0)
        
        # Sensor Diagonal (Cone Detector)
        LM = clamp(s["lmid"] / self.sensor_len, 0.0, 1.0)
        RM = clamp(s["rmid"] / self.sensor_len, 0.0, 1.0)
        
        # Sensor Samping (Wall Detector)
        L = clamp(s["left"] / self.sensor_len, 0.0, 1.0)
        R = clamp(s["right"] / self.sensor_len, 0.0, 1.0)

        # Speed
        current_vel = s["speed"]
        V = clamp(abs(current_vel) / self.max_speed, 0.0, 1.0)

        # ===========================
        # 2. EMERGENCY RECOVERY (MUNDUR)
        # ===========================
        # Jika sedang mode mundur
        if self.reversing:
            self.reverse_frame -= 1
            if self.reverse_frame <= 0:
                self.reversing = False
                self.stuck_timer = 0
            # Setir dibalik saat mundur
            rev_steer = -1.0 if s["left"] < s["right"] else 1.0
            return rev_steer, -1.0, 0.0

        # Cek Stuck: Gas ditekan tapi mobil diam
        if abs(current_vel) < 10 and (F < 0.2 or LM < 0.2 or RM < 0.2):
            self.stuck_timer += 1
        else:
            self.stuck_timer = 0
            
        # Jika stuck > 0.5 detik, aktifkan mundur
        if self.stuck_timer > 30:
            self.reversing = True
            self.reverse_frame = 40 
            return 0.0, 0.0, 0.0

        # ===========================
        # 3. STEERING LOGIC (ANTI-BIMBANG)
        # ===========================
        
        # Hitung "Skor Ruang" (Space Score)
        # Semakin besar nilainya, semakin lega arah tersebut.
        # Kita beri bobot lebih pada diagonal (LM/RM) karena cone biasanya di situ.
        space_left  = (L * 0.4) + (LM * 0.6)
        space_right = (R * 0.4) + (RM * 0.6)
        
        # Hitung keinginan belok dasar
        raw_steer = space_right - space_left
        
        # --- ATURAN PEMECAH SERI (THE FIX) ---
        # Jika depan ada rintangan (F < 0.5)
        # TAPI selisih kiri dan kanan sangat kecil (mobil bingung/seimbang)
        if F < 0.5 and abs(raw_steer) < 0.15:
            # PAKSA MEMILIH!
            # Logika: Jika ada sedikit saja lebih luas di kanan, banting kanan penuh.
            # Jika benar-benar sama persis, default ke KANAN (1.0).
            if space_right >= space_left:
                raw_steer = 0.8  # Paksa Kanan
            else:
                raw_steer = -0.8 # Paksa Kiri
        
        # --- SENSITIVITAS DINAMIS ---
        # Saat mobil pelan atau ada rintangan dekat, setir harus responsif.
        sensitivity = 1.0
        min_dist = min(F, LM, RM)
        
        if min_dist < 0.4: 
            sensitivity = 2.5  # Responsif tinggi untuk menghindar
        elif V > 0.8:
            sensitivity = 0.7  # Kurangi sensitivitas saat ngebut biar stabil

        final_steer = clamp(raw_steer * sensitivity, -1.0, 1.0)

        # ===========================
        # 4. SPEED CONTROL (GAS & REM)
        # ===========================
        
        # Target Speed berdasarkan jarak pandang terdekat (Safety Factor)
        # Jarak 1.0 (Jauh) -> Target 100%
        # Jarak 0.2 (Dekat) -> Target 0%
        safety_factor = clamp((min_dist - 0.2) / 0.6, 0.0, 1.0)
        target_speed = 0.1 + (0.9 * safety_factor)
        
        throttle = 0.0
        brake = 0.0
        
        # Jika setir berbelok tajam, kurangi target speed (Cornering logic)
        if abs(final_steer) > 0.4:
            target_speed *= 0.6
            
        if V < target_speed:
            # Akselerasi
            throttle = 1.0 if safety_factor > 0.5 else 0.5
        else:
            # Pengereman Cerdas
            # Hanya rem jika speed jauh diatas target ATAU bahaya di depan mata
            diff = V - target_speed
            if diff > 0.1 or F < 0.3:
                brake = clamp(diff * 4.0, 0.0, 1.0)
                
        # Override Terakhir: Jika sangat dekat (< 15%), Rem Mati!
        if F < 0.15:
            brake = 1.0
            throttle = 0.0

        return final_steer, throttle, brake