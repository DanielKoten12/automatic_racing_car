import pygame
import sys

# --- ukuran window ---
WIDTH, HEIGHT = 1000, 600

# --- warna (disamain dengan gambar) ---
GREEN = (20, 80, 20)     # rumput / background
GRAY  = (120, 120, 120)  # aspal
BLUE  = (40, 80, 220)    # garis biru di tengah

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Track dengan Beberapa Belokan")

# titik-titik jalur tengah track (loop dengan beberapa belokan)
# mobil bisa mengikuti garis biru ini sebagai rute
track_points = [
    (220, 450),  # kiri bawah
    (180, 360),  # naik sedikit
    (190, 280),
    (240, 220),  # tikungan ke kanan
    (340, 180),
    (480, 160),
    (640, 170),
    (760, 200),
    (830, 260),  # tikungan kanan bawah
    (850, 330),
    (820, 400),  # mulai turun
    (720, 450),
    (580, 480),
    (420, 480),
    (300, 470),
]

ROAD_OUTER_WIDTH = 120  # lebar total aspal
ROAD_INNER_WIDTH = 70   # bagian "dipotong" hijau di tengah track
LINE_WIDTH       = 4    # garis biru

clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # latar hijau
    screen.fill(GREEN)

    # 1) aspal abu-abu (lebar)
    pygame.draw.lines(screen, GRAY, True, track_points, ROAD_OUTER_WIDTH)

    # 2) hijau di tengah track (membuatnya jadi jalur tertutup)
    pygame.draw.lines(screen, GREEN, True, track_points, ROAD_INNER_WIDTH)

    # 3) garis tengah biru (jalur yang akan diikuti mobil)
    pygame.draw.lines(screen, BLUE, True, track_points, LINE_WIDTH)

    pygame.display.flip()
    clock.tick(60)
