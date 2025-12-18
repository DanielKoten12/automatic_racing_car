# make_nascar_track.py
import pygame, os

WIDTH, HEIGHT = 1000, 600

def main():
    pygame.init()

    # Pastikan folder assets ada
    os.makedirs("assets", exist_ok=True)

    # Surface kosong
    surf = pygame.Surface((WIDTH, HEIGHT))

    # Warna-warna (disesuaikan dgn detektor jalan kamu)
    GRASS = (20, 80, 20)         # hijau rumput
    ROAD  = (120, 120, 120)      # abu-abu (gray-like, mid brightness)
    BLUE_LINE = (40, 80, 220)    # garis biru opsional

    # Background rumput
    surf.fill(GRASS)

    # Outer ellipse = badan lintasan luar
    outer_margin_x = 60
    outer_margin_y = 60
    outer_rect = pygame.Rect(
        outer_margin_x,
        outer_margin_y,
        WIDTH  - 2*outer_margin_x,
        HEIGHT - 2*outer_margin_y
    )
    pygame.draw.ellipse(surf, ROAD, outer_rect)

    # Inner ellipse = lubang tengah (diisi rumput lagi)
    inner_margin = 140
    inner_rect = pygame.Rect(
        outer_margin_x + inner_margin,
        outer_margin_y + inner_margin,
        WIDTH  - 2*outer_margin_x - 2*inner_margin,
        HEIGHT - 2*outer_margin_y - 2*inner_margin
    )
    pygame.draw.ellipse(surf, GRASS, inner_rect)

    # Garis biru di bagian dalam lintasan (optional, bantu visual)
    # ini juga masih dianggap 'road' karena Track._is_road cek warna biru
    pygame.draw.ellipse(surf, BLUE_LINE, inner_rect.inflate(-40, -40), 4)

    out_path = os.path.join("assets", "track_nascar.png")
    pygame.image.save(surf, out_path)
    print("Saved:", out_path)

    pygame.quit()

if __name__ == "__main__":
    main()
