# rule_controller.py
"""
Rule-Based AI Controller - PRO RACING FLOW
Fitur: 
1. Momentum Keeper: Menjaga 'Rolling Speed' di tikungan agar tidak stop-and-go.
2. Sharp Turn-in: Respons setir lebih cepat untuk masuk tikungan.
3. Smooth Throttle: Transisi gas yang lebih halus.
"""

from utils import clamp
import math

class RuleController:
    def __init__(self, sensor_len: float = 400.0, max_speed: float = 900.0): 
        # Sensor diperpanjang lagi (400) untuk melihat exit tikungan lebih awal
        self.sensor_len = float(sensor_len)
        self.max_speed = float(max_speed)

        # ===== PD CONTROLLER (STEERING) =====
        # Tuning untuk "Fast Entry"
        self.kp = 0.80  # Naikkan: Agar mobil cepat membelokkan hidung (turn-in)
        self.kd = 1.5   # Turunkan: Mengurangi "kekakuan" setir agar lebih lincah
        self.prev_error = 0.0

        # ===== LOOKAHEAD (ANTISIPASI) =====
        self.lookahead_weight = 0.85 # Sangat fokus pada bentuk jalan di depan

        # ===== OBSTACLE (CONE) PARAMETERS =====
        self.cone_dist_trigger = 280.0  
        self.cone_steer_force = 1.5     # Menghindar lebih agresif di speed tinggi

        # ===== SPEED CONTROL (MOMENTUM) =====
        # Braking factor lebih kecil = Ngerem lebih telat (Late Braking)
        self.braking_factor = 0.45  
        
        # Kecepatan minimum saat menikung. 
        # Mobil TIDAK BOLEH pelan di bawah ini kecuali mau nabrak.
        # Ini solusi untuk masalah "berhenti sebentar".
        self.min_corner_speed = 350.0 
        
        self.steer_deadzone = 0.08 

        # ===== SMOOTHING =====
        self.alpha_steer = 0.2 # Smoothing steer standar
        self._last_steer = 0.0  

    def act(self, s):
        """
        Input: s (dict sensor)
        Output: steer, throttle, brake
        """
        # 1. READ SENSORS
        left = s["left"]
        lmid = s["lmid"]
        front = s["front"]
        rmid = s["rmid"]
        right = s["right"]
        far_left = s.get("far_left", left)
        far_right = s.get("far_right", right)
        speed = s["speed"]

        # ==========================================================
        # 2. OBSTACLE AVOIDANCE
        # ==========================================================
        is_obstacle = False
        avoid_steer = 0.0
        
        min_front = min(front, lmid, rmid)
        
        if min_front < self.cone_dist_trigger:
            space_left = (left + far_left + lmid) / 3.0
            space_right = (right + far_right + rmid) / 3.0
            
            # Deteksi rintangan
            if abs(space_left - space_right) > 40.0 or min_front < 140:
                is_obstacle = True
                if space_left > space_right:
                    avoid_steer = -self.cone_steer_force
                else:
                    avoid_steer = self.cone_steer_force
        
        # ==========================================================
        # 3. STEERING LOGIC (SHARPER & SMOOTHER)
        # ==========================================================
        denom = (left + right)
        if denom < 1.0: denom = 1.0
        
        # Error posisi (-1 s/d 1)
        curr_error = (right - left) / denom
        
        # Derivative
        d_error = curr_error - self.prev_error
        self.prev_error = curr_error 
        
        # PD Calculation
        pd_steer = (self.kp * curr_error) + (self.kd * d_error)

        # Lookahead Target
        denom_far = (far_left + far_right)
        if denom_far < 1.0: denom_far = 1.0
        far_error = (far_right - far_left) / denom_far
        
        if is_obstacle:
            # Emergency Avoidance
            risk = clamp(1.0 - (min_front / self.cone_dist_trigger), 0.0, 1.0)
            target_steer = (1.0 - risk) * pd_steer + (risk * avoid_steer)
        else:
            # Racing Line: Blend PD (Center) + Lookahead (Prediction)
            target_steer = pd_steer + (self.lookahead_weight * far_error)

        # Smoothing
        final_steer = (1.0 - self.alpha_steer) * self._last_steer + self.alpha_steer * target_steer
        self._last_steer = final_steer
        final_steer = clamp(final_steer, -1.0, 1.0)

        # ==========================================================
        # 4. MOMENTUM-BASED SPEED LOGIC
        # ==========================================================
        
        # A. Hitung kebutuhan pengereman
        current_braking_dist = speed * self.braking_factor
        view_dist = min(front, max(far_left, far_right))
        
        # B. Base Target Speed
        target_speed_val = self.max_speed
        
        # Logic 1: Steering Penalty (Lebih ringan)
        # Kita izinkan mobil menikung lebih cepat (hanya turun 40% di full lock)
        steer_mag = abs(final_steer)
        if steer_mag > self.steer_deadzone:
            corner_factor = (steer_mag - self.steer_deadzone) / (1.0 - self.steer_deadzone)
            target_speed_val *= (1.0 - (corner_factor * 0.4)) 

        # Logic 2: Braking by Distance
        if view_dist < current_braking_dist:
            danger_ratio = view_dist / current_braking_dist
            # Kurva pengereman lebih landai (pangkat 1.2) agar tidak ngerem mendadak
            safe_speed_limit = self.max_speed * (danger_ratio ** 1.2)
            target_speed_val = min(target_speed_val, safe_speed_limit)

        # Logic 3: MOMENTUM KEEPER (SOLUSI STOP-AND-GO)
        # Selama jarak depan > 80px (tidak kritis), JANGAN biarkan target speed < min_corner_speed.
        # Ini memaksa mobil tetap "menggelinding" cepat di tikungan.
        if view_dist > 80.0:
            target_speed_val = max(target_speed_val, self.min_corner_speed)

        # C. Actuation
        throttle = 0.0
        brake = 0.0

        if speed < target_speed_val:
            throttle = 1.0
            # Smooth transition saat mendekati top speed
            if speed > target_speed_val - 30:
                throttle = 0.7 
        else:
            diff = speed - target_speed_val
            # Rem hanya digunakan jika benar-benar overspeed jauh
            # Jika overspeed sedikit, biarkan 'engine brake' (throttle 0) yang bekerja
            if diff > 40: 
                brake = clamp(diff / 80.0, 0.0, 1.0)
            else:
                brake = 0.0 # Coasting (menggelinding)

        # Emergency Panic Brake (Hanya kalau benar-benar mau nabrak)
        if min_front < 60 and speed > 80:
            throttle = 0.0
            brake = 1.0
            
        # Recovery Stuck
        if speed < 10 and min_front < 40:
             throttle = 1.0
             brake = 0.0
             final_steer = -1.0 if left > right else 1.0

        return final_steer, throttle, brake
    