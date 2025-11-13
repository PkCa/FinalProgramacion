# game.py
# ---------------------------------------------------------------------
# Click-to-move con Pygame + Board. Promoción simple a Dama.
# (Sin enroque ni en passant para mantenerlo simple por ahora.)
# ---------------------------------------------------------------------

import os
import sys
import pygame
from typing import List, Optional, Tuple

from board.board import Board
from board.coordenates import Coordenate
from pieces.queen import Queen  # para promoción

# ---------- ventana ----------
TILE_SIZE = 64
BOARD_SIZE = 8
WINDOW_W = TILE_SIZE * BOARD_SIZE
WINDOW_H = TILE_SIZE * BOARD_SIZE

LIGHT_SQ = (240, 217, 181)
DARK_SQ  = (181, 136, 99)

HOVER_COLOR = (255, 255, 0, 60)
SEL_COLOR   = (0, 200, 255, 80)
MOVE_COLOR  = (80, 160, 120, 120)

NAME_TO_SPRITEBASE = {
    "pawn":   "pawn",
    "rook":   "rook",
    "bishop": "bishop",
    "queen":  "queen",
    "king":   "king",
    "knight": "knight"
}

# ---------- helpers de coordenadas ----------
def C(col: str, row: int) -> Coordenate:
    """Coordenate(row, col) usando orden correcto (row first)."""
    return Coordenate(row, col)

def idx_to_coord(r_idx: int, c_idx: int) -> Coordenate:
    return Coordenate(r_idx + 1, chr(ord('a') + c_idx))

def mouse_to_indices(mx: int, my: int) -> Optional[Tuple[int, int]]:
    c = mx // TILE_SIZE
    r_screen = my // TILE_SIZE
    r = (BOARD_SIZE - 1) - r_screen  # a8 arriba
    if 0 <= c < 8 and 0 <= r < 8:
        return (r, c)
    return None

# ---------- carga de sprites ----------
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

def load_board_background(width: int, height: int) -> Optional[pygame.Surface]:
    """
    Busca board.png primero en la raíz (junto a este archivo) y luego en ./sprites.
    """
    root_dir = os.path.dirname(__file__)
    candidates = [
        os.path.join(root_dir, "board.png"),
        os.path.join(root_dir, "sprites", "board.png"),
    ]
    for path in candidates:
        try:
            img = pygame.image.load(path).convert_alpha()
            if img.get_width() != width or img.get_height() != height:
                img = pygame.transform.smoothscale(img, (width, height))
            return img
        except Exception:
            pass
    print("[INFO] No se encontró board.png. Se usarán casillas coloreadas.")
    return None

# ---------- dibujo ----------
def draw_board(surface: pygame.Surface, board_bg: Optional[pygame.Surface]):
    if board_bg:
        surface.blit(board_bg, (0, 0))
        return
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            x = c * TILE_SIZE
            y = (BOARD_SIZE - 1 - r) * TILE_SIZE
            pygame.draw.rect(surface, DARK_SQ if (r + c) % 2 else LIGHT_SQ, (x, y, TILE_SIZE, TILE_SIZE))

def draw_pieces(surface: pygame.Surface, board: Board, sprites: dict):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            piece = board.board[r][c]
            if not piece:
                continue
            x = c * TILE_SIZE
            y = (BOARD_SIZE - 1 - r) * TILE_SIZE
            name = getattr(piece, "name", getattr(piece, "type", None))
            color = getattr(piece, "color", None)
            img = sprites.get((name, color))
            if img:
                surface.blit(img, (x, y))

def draw_overlay_square(surface: pygame.Surface, r_idx: int, c_idx: int, rgba=(255,255,0,60)):
    overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    overlay.fill(rgba)
    x = c_idx * TILE_SIZE
    y = (BOARD_SIZE - 1 - r_idx) * TILE_SIZE
    surface.blit(overlay, (x, y))

# ---------- utilidades de movimiento ----------
def path_clear(board: Board, a: Coordenate, b: Coordenate) -> bool:
    between = board.squares_between(a, b)
    return all(board.is_empty(c) for c in between)

def enemy_at(board: Board, dst: Coordenate, my_color: str) -> bool:
    p = board.get_piece_at(dst)
    return bool(p) and getattr(p, "color", None) not in (None, my_color)

def same_color_at(board: Board, dst: Coordenate, my_color: str) -> bool:
    p = board.get_piece_at(dst)
    return bool(p) and getattr(p, "color", None) == my_color

def king_safe_after(board: Board, src: Coordenate, dst: Coordenate, my_color: str) -> bool:
    """
    Simula src->dst y verifica si el rey propio queda a salvo.
    """
    enemy = "black" if my_color == "white" else "white"
    mover = board.get_piece_at(src)
    captured = board.get_piece_at(dst)

    if mover is None:
        return False

    # aplicar
    board._set_piece_at(src, None)
    board._set_piece_at(dst, mover)

    try:
        # localizar rey (si el que se movió es el rey, su nueva pos es dst)
        name = getattr(mover, "name", getattr(mover, "type", None))
        if name == "king":
            kpos = dst
        else:
            kpos = board.king_position(my_color)

        in_check = board.is_square_attacked(kpos, by_color=enemy)
        return not in_check
    finally:
        # revertir
        board._set_piece_at(dst, captured)
        board._set_piece_at(src, mover)

def generate_moves(board: Board, src: Coordenate, turn: str) -> List[Coordenate]:
    """
    Devuelve destinos pseudo-legales (patrones + bloqueos + sin capturar aliado).
    Filtrado de jaque propio se hace aparte.
    """
    piece = board.get_piece_at(src)
    if not piece:
        return []

    # respetar la pieza del turno
    if getattr(piece, "color", None) != turn:
        return []

    # si la pieza está clavada y tu lógica la usa, evitamos moverla
    if getattr(piece, "pinned", False):
        return []

    name = getattr(piece, "name", getattr(piece, "type", None))
    color = getattr(piece, "color", None)
    res: List[Coordenate] = []

    def push_if_ok(dst: Coordenate, need_enemy: bool = False, forbid_enemy: bool = False):
        if not (dst.col in "abcdefgh" and 1 <= dst.row <= 8):
            return
        if forbid_enemy and not board.is_empty(dst):
            return
        if same_color_at(board, dst, color):
            return
        if need_enemy and not enemy_at(board, dst, color):
            return
        res.append(dst)

    # patrones
    if name == "knight":
        for dx, dy in [(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)]:
            dst = Coordenate(src.row + dy, chr(ord(src.col) + dx))
            push_if_ok(dst)
        return res

    if name == "king":
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx == 0 and dy == 0:
                    continue
                dst = Coordenate(src.row + dy, chr(ord(src.col) + dx))
                push_if_ok(dst)
        return res

    if name in ("bishop", "rook", "queen"):
        directions = []
        if name in ("bishop", "queen"):
            directions += [(1,1),(1,-1),(-1,1),(-1,-1)]
        if name in ("rook", "queen"):
            directions += [(1,0),(-1,0),(0,1),(0,-1)]
        for dx, dy in directions:
            step = 1
            while True:
                dst = Coordenate(src.row + dy*step, chr(ord(src.col) + dx*step))
                if not (dst.col in "abcdefgh" and 1 <= dst.row <= 8):
                    break
                # cortar por bloqueo
                if not path_clear(board, src, dst):
                    break
                # agregar destino
                if same_color_at(board, dst, color):
                    break
                res.append(dst)
                # si hay captura, no seguimos más allá
                if enemy_at(board, dst, color):
                    break
                step += 1
        return res

    if name == "pawn":
        direction = 1 if color == "white" else -1
        start = 2 if color == "white" else 7
        # un paso
        one = Coordenate(src.row + direction, src.col)
        if 1 <= one.row <= 8 and board.is_empty(one):
            res.append(one)
            # dos pasos desde inicial si intermedia libre
            if src.row == start:
                two = Coordenate(src.row + 2*direction, src.col)
                inter = Coordenate(src.row + direction, src.col)
                if 1 <= two.row <= 8 and board.is_empty(two) and board.is_empty(inter):
                    res.append(two)
        # capturas diagonales
        for dx in (-1, 1):
            diag = Coordenate(src.row + direction, chr(ord(src.col) + dx))
            if 1 <= diag.row <= 8 and diag.col in "abcdefgh" and enemy_at(board, diag, color):
                res.append(diag)
        # captura al paso
        for dx in (-1, 1):
            diag = Coordenate(src.row, chr(ord(src.col) + dx))
            dest = Coordenate(src.row + direction, chr(ord(src.col) + dx))
            if 1 <= diag.row <= 8 and (diag.row == 5 or diag.row == 4) and diag.col in "abcdefgh" and enemy_at(board,diag,color):
                res.append(dest)

        return res

    return res

def legal_moves(board: Board, src: Coordenate, turn: str) -> List[Coordenate]:
    """Pseudo-legales filtrados por 'rey a salvo' tras el movimiento."""
    my_color = turn
    candidates = generate_moves(board, src, turn)
    safe: List[Coordenate] = []
    for dst in candidates:
        if king_safe_after(board, src, dst, my_color):
            safe.append(dst)
    return safe

def apply_simple_move(board: Board, src: Coordenate, dst: Coordenate, type=""):
    """Aplica movimiento físico (sin enroque ni EP). Maneja promoción a dama."""
    mover = board.get_piece_at(src)

    captured = board.get_piece_at(dst)
    board._set_piece_at(src, None)
    board._set_piece_at(dst, mover)

    # actualizar posición interna de la pieza si tiene .move(vector_row, vector_col)
    try:
        vector_row = dst.row - src.row
        vector_col = (ord(dst.col) - ord(src.col))
        mover.move(vector_row=vector_row, vector_col=vector_col)
    except Exception:
        pass

    # promoción simple a dama
    name = getattr(mover, "name", getattr(mover, "type", None))
    color = getattr(mover, "color", None)
    if name == "pawn":
        if (color == "white" and dst.row == 8) or (color == "black" and dst.row == 1):
            q = Queen(color, dst.col, dst.row)
            board._set_piece_at(dst, q)

# ---------- main loop ----------
def main():
    print("Controles: clic en una pieza del turno, luego clic en un destino válido. ESC para salir.")
    pygame.init()
    pygame.display.set_caption("Chess — Pygame")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock = pygame.time.Clock()

    board = Board()
    sprites = load_sprites(TILE_SIZE)
    board_bg = load_board_background(WINDOW_W, WINDOW_H)

    turn = "white"  # arranca blancas
    sel_sq: Optional[Tuple[int,int]] = None
    hover_sq: Optional[Tuple[int,int]] = None
    legal: List[Coordenate] = []

    running = True
    while running:
        # -------- eventos --------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                mi = mouse_to_indices(*event.pos)
                hover_sq = (mi[0], mi[1]) if mi else None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mi = mouse_to_indices(*event.pos)
                if not mi:
                    continue
                r, c = mi
                clicked = idx_to_coord(r, c)

                # si no hay selección, intentar seleccionar pieza del turno
                if sel_sq is None:
                    p = board.get_piece_at(clicked)
                    if p and getattr(p, "color", None) == turn:
                        sel_sq = (r, c)
                        legal = legal_moves(board, clicked, turn)
                    else:
                        sel_sq = None
                        legal = []
                else:
                    # si clickea el mismo cuadrado, deselecciona
                    if sel_sq == (r, c):
                        sel_sq = None
                        legal = []
                        continue

                    src = idx_to_coord(sel_sq[0], sel_sq[1])
                    # si clickea en otro propio, cambia selección
                    q = board.get_piece_at(clicked)
                    if q and getattr(q, "color", None) == turn:
                        sel_sq = (r, c)
                        legal = legal_moves(board, clicked, turn)
                        continue

                    # si es destino válido, mover
                    if any((d.row == clicked.row and d.col == clicked.col) for d in legal):
                        apply_simple_move(board, src, clicked)
                        # cambio de turno
                        turn = "black" if turn == "white" else "white"
                    # reset selección
                    sel_sq = None
                    legal = []

        # -------- dibujo --------
        draw_board(screen, board_bg)
        draw_pieces(screen, board, sprites)

        # overlays
        if sel_sq:
            draw_overlay_square(screen, sel_sq[0], sel_sq[1], SEL_COLOR)
            for d in legal:
                # convertir Coordinate a índices r,c
                r_idx = d.row - 1
                c_idx = ord(d.col) - ord('a')
                draw_overlay_square(screen, r_idx, c_idx, MOVE_COLOR)
        if hover_sq:
            draw_overlay_square(screen, hover_sq[0], hover_sq[1], HOVER_COLOR)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
