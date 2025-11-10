# main.py
# -----------------------------------------------------------------------------
# Visualizador del tablero con Pygame usando un sprite de fondo: board.png
# -----------------------------------------------------------------------------

import os
import sys
import pygame

from board.board import Board

# ----------------------------------------------------------------------------- 
# Config
# -----------------------------------------------------------------------------
TILE_SIZE = 96
BOARD_SIZE = 8
WINDOW_W = TILE_SIZE * BOARD_SIZE
WINDOW_H = TILE_SIZE * BOARD_SIZE

# Fallback colors si no hay board.png
LIGHT_SQ = (240, 217, 181)
DARK_SQ  = (181, 136, 99)

HOVER_COLOR = (255, 255, 0, 60)
SEL_COLOR   = (0, 200, 255, 80)

NAME_TO_SPRITEBASE = {
    "pawn":   "pawn",
    "rook":   "rook",
    "bishop": "bishop",
    "queen":  "queen",
    "king":   "king",
    "knight": "knght",  # archivo del caballo se llama knght_*.png
}

# ----------------------------------------------------------------------------- 
# Sprites
# -----------------------------------------------------------------------------
def load_sprites(tile_size: int) -> dict:
    sprites = {}
    base_dir = os.path.join(os.path.dirname(__file__), "sprites")
    for piece_name, base in NAME_TO_SPRITEBASE.items():
        for color in ("white", "black"):
            filename = f"{base}_{color}.png"
            path = os.path.join(base_dir, filename)
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (tile_size, tile_size))
                sprites[(piece_name, color)] = img
            except Exception as e:
                print(f"[WARN] No se pudo cargar sprite: {filename} ({e})")
                surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                pygame.draw.circle(surf, (220, 50, 50), (tile_size//2, tile_size//2), tile_size//3)
                sprites[(piece_name, color)] = surf
    return sprites

def load_board_background(width: int, height: int) -> pygame.Surface | None:
    """
    Intenta cargar board.png (misma carpeta que main.py) y escalarlo al tamaño de la ventana.
    Si no existe o falla, devuelve None para usar fallback de casillas de colores.
    """
    path = os.path.join(os.path.dirname(__file__), "board.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        if img.get_width() != width or img.get_height() != height:
            img = pygame.transform.smoothscale(img, (width, height))
        return img
    except Exception as e:
        print(f"[INFO] No se pudo usar board.png, se dibujarán casillas. ({e})")
        return None

# ----------------------------------------------------------------------------- 
# Draw
# -----------------------------------------------------------------------------
def draw_board(surface: pygame.Surface, board_bg: pygame.Surface | None):
    """
    Dibuja el tablero. Si hay board.png, lo blitea completo.
    De lo contrario, pinta casillas alternando colores (a8 arriba a la izquierda).
    """
    if board_bg:
        surface.blit(board_bg, (0, 0))
        return

    # Fallback: casillas
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            x = c * TILE_SIZE
            y = (BOARD_SIZE - 1 - r) * TILE_SIZE  # a8 arriba
            is_dark = (r + c) % 2 == 1
            color = DARK_SQ if is_dark else LIGHT_SQ
            pygame.draw.rect(surface, color, (x, y, TILE_SIZE, TILE_SIZE))

def draw_pieces(surface: pygame.Surface, board: Board, sprites: dict):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            piece = board.board[r][c]
            if not piece:
                continue
            x = c * TILE_SIZE
            y = (BOARD_SIZE - 1 - r) * TILE_SIZE  # a8 arriba
            name = getattr(piece, "name", getattr(piece, "type", None))
            color = getattr(piece, "color", None)
            if not name or color not in ("white", "black"):
                continue
            img = sprites.get((name, color))
            if img:
                surface.blit(img, (x, y))

def draw_overlay_square(surface: pygame.Surface, col_idx: int, row_idx: int, rgba=(255,255,0,60)):
    overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    overlay.fill(rgba)
    x = col_idx * TILE_SIZE
    y = (BOARD_SIZE - 1 - row_idx) * TILE_SIZE
    surface.blit(overlay, (x, y))

# ----------------------------------------------------------------------------- 
# Main
# -----------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Chess — Pygame")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock = pygame.time.Clock()

    board = Board()
    sprites = load_sprites(TILE_SIZE)
    board_bg = load_board_background(WINDOW_W, WINDOW_H)

    hover_sq = None
    sel_sq = None

    running = True
    while running:
        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                c = mx // TILE_SIZE
                r_screen = my // TILE_SIZE
                r = (BOARD_SIZE - 1) - r_screen
                hover_sq = (c, r) if 0 <= c < 8 and 0 <= r < 8 else None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hover_sq:
                    sel_sq = None if sel_sq == hover_sq else hover_sq

        # Dibujo
        draw_board(screen, board_bg)
        draw_pieces(screen, board, sprites)
        if hover_sq:
            draw_overlay_square(screen, hover_sq[0], hover_sq[1], HOVER_COLOR)
        if sel_sq:
            draw_overlay_square(screen, sel_sq[0], sel_sq[1], SEL_COLOR)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
