# rule_controller.py
"""Rule-Based AI Controller untuk mobil balap"""

from utils import clamp


class RuleController:
    """Controller berbasis aturan sederhana untuk mobil balap"""
    
    def __init__(self, max_speed=900):
        """Inisialisasi parameter controller"""
        self.max_speed = max_speed
        self.k_steer = 0.006  # konstanta steering proporsional
    
    def act(self, s):
        """
        Menentukan aksi berdasarkan sensor readings
        
        Args:
            s (dict): Sensor readings dengan keys:
                - left, lmid, front, rmid, right: jarak sensor
                - bias: selisih right - left
                - speed: kecepatan saat ini
        
        Returns:
            tuple: (steer, throttle, brake)
        """
        # steer proporsional terhadap 'bias', dibatasi
        steer = clamp(self.k_steer * s["bias"], -0.7, 0.7)

        # kecepatan target dari jarak depan & sisi
        front = s["front"]
        side = min(s["lmid"], s["rmid"])
        # throttle lebih rendah kalau ruang depan/samping sempit
        t_front = clamp((front - 60) / 220, 0.0, 1.0)  # 0 saat <60px, 1 saat >=280px
        t_side = clamp((side - 60) / 220, 0.0, 1.0)
        throttle = 0.35 + 0.65 * min(t_front, t_side)

        brake = 0.0
        if front < 70:  # emergency
            brake, throttle = 1.0, 0.0
        elif front < 110:
            brake = 0.4 * (110 - front) / 40

        return steer, throttle, brake
