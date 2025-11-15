# game.py
# ---------------------------------------------------------------------
# Click-to-move con Pygame + Board. Promoción simple a Dama.
# Soporta En Passant y Enroque (corto y largo).
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
    return Coordenate(row, col)

def idx_to_coord(r_idx: int, c_idx: int) -> Coordenate:
    return Coordenate(r_idx + 1, chr(ord('a') + c_idx))

def mouse_to_indices(mx: int, my: int) -> Optional[Tuple[int, int]]:
    c = mx // TILE_SIZE
    r_screen = my // TILE_SIZE
    r = (BOARD_SIZE - 1) - r_screen
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
            except Exception:
                surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                pygame.draw.circle(surf, (220, 50, 50), (tile_size//2, tile_size//2), tile_size//3)
                sprites[(piece_name, color)] = surf
    return sprites

def load_board_background(width: int, height: int):
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
        except:
            pass
    print("[INFO] No board.png, usando colores.")
    return None

# ---------- dibujo ----------
def draw_board(surface, board_bg):
    if board_bg:
        surface.blit(board_bg, (0, 0))
        return
    for r in range(8):
        for c in range(8):
            x = c * TILE_SIZE
            y = (BOARD_SIZE - 1 - r) * TILE_SIZE
            pygame.draw.rect(surface, DARK_SQ if (r + c) % 2 else LIGHT_SQ, (x, y, TILE_SIZE, TILE_SIZE))

def draw_pieces(surface, board, sprites):
    for r in range(8):
        for c in range(8):
            p = board.board[r][c]
            if not p: continue
            x = c * TILE_SIZE
            y = (BOARD_SIZE - 1 - r) * TILE_SIZE
            name = getattr(p, "name", getattr(p, "type", None))
            color = getattr(p, "color", None)
            img = sprites.get((name, color))
            if img: surface.blit(img, (x, y))

def draw_overlay_square(surface, r_idx, c_idx, rgba):
    overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    overlay.fill(rgba)
    x = c_idx * TILE_SIZE
    y = (BOARD_SIZE - 1 - r_idx) * TILE_SIZE
    surface.blit(overlay, (x, y))

# ---------- utilidades ----------
def path_clear(board, a, b):
    return all(board.is_empty(c) for c in board.squares_between(a, b))

def enemy_at(board, coord, my_color):
    p = board.get_piece_at(coord)
    return p and getattr(p, "color", None) != my_color

def same_color_at(board, coord, my_color):
    p = board.get_piece_at(coord)
    return p and getattr(p, "color", None) == my_color


# ======================================================================================
#                          generate_moves  (Incluye ENROQUE)
# ======================================================================================
def generate_moves(board, src, turn, en_passant_target=None):
    piece = board.get_piece_at(src)
    if not piece: return []
    if getattr(piece, "color", None) != turn: return []
    if getattr(piece, "pinned", False): return []

    name = getattr(piece, "name", getattr(piece, "type", None))
    color = getattr(piece, "color", None)
    enemy = "black" if color == "white" else "white"

    res = []

    def push_if_ok(dst):
        if dst.col not in "abcdefgh" or not (1 <= dst.row <= 8): return
        if same_color_at(board, dst, color): return
        res.append(dst)

    # ------------------------- CABALLO
    if name == "knight":
        for dx, dy in [(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)]:
            dst = Coordenate(src.row + dy, chr(ord(src.col) + dx))
            push_if_ok(dst)
        return res

    # ------------------------- REY (incluye ENROQUE)
    if name == "king":
        # movimientos normales 1 casilla
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx == 0 and dy == 0: continue
                dst = Coordenate(src.row + dy, chr(ord(src.col) + dx))
                push_if_ok(dst)

        # ==========================
        #        ENROQUE
        # ==========================
        king = piece
        if hasattr(king, "has_moved") and not king.has_moved:
            back = 1 if color == "white" else 8

            # --- Enroque corto ---
            rook_sq = Coordenate(back, "h")
            rook = board.get_piece_at(rook_sq)
            if rook and getattr(rook, "color", None) == color:
                if not hasattr(rook, "has_moved"):
                    rook.has_moved = False
                if not rook.has_moved:
                    f_sq = Coordenate(back, "f")
                    g_sq = Coordenate(back, "g")
                    if (board.is_empty(f_sq) and board.is_empty(g_sq)
                        and not board.is_square_attacked(src, enemy)
                        and not board.is_square_attacked(f_sq, enemy)
                        and not board.is_square_attacked(g_sq, enemy)):
                        res.append(g_sq)

            # --- Enroque largo ---
            rook_sq = Coordenate(back, "a")
            rook = board.get_piece_at(rook_sq)
            if rook and getattr(rook, "color", None) == color:
                if not hasattr(rook, "has_moved"):
                    rook.has_moved = False
                if not rook.has_moved:
                    d_sq = Coordenate(back, "d")
                    c_sq = Coordenate(back, "c")
                    b_sq = Coordenate(back, "b")
                    if (board.is_empty(d_sq) and board.is_empty(c_sq) and board.is_empty(b_sq)
                        and not board.is_square_attacked(src, enemy)
                        and not board.is_square_attacked(d_sq, enemy)
                        and not board.is_square_attacked(c_sq, enemy)):
                        res.append(c_sq)

        return res

# game.py
# ---------------------------------------------------------------------
# Click-to-move con Pygame + Board.
# Soporta:
#   - Promoción simple a Dama
#   - Captura al paso (En Passant)
#   - Enroque corto y largo (blancas/negras)
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
                pygame.draw.circle(surf, (220, 50, 50),
                                   (tile_size//2, tile_size//2),
                                   tile_size//3)
                sprites[(piece_name, color)] = surf
    return sprites

def load_board_background(width: int, height: int) -> Optional[pygame.Surface]:
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
            pygame.draw.rect(
                surface,
                DARK_SQ if (r + c) % 2 else LIGHT_SQ,
                (x, y, TILE_SIZE, TILE_SIZE)
            )

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

# ---------- simulación de jaque ----------
def king_safe_after(
    board: Board,
    src: Coordenate,
    dst: Coordenate,
    my_color: str,
    en_passant_target: Optional[Coordenate] = None
) -> bool:
    """
    Simula src->dst y verifica si el rey propio queda a salvo.
    Soporta:
      - movimiento normal
      - captura normal
      - captura al paso
      - enroque (mueve rey + torre en la simulación)
    """
    enemy = "black" if my_color == "white" else "white"
    mover = board.get_piece_at(src)
    if mover is None:
        return False

    name = getattr(mover, "name", getattr(mover, "type", None))
    color = getattr(mover, "color", None)

    # --- Detectar enroque (desde e1/e8 a g1/c1/g8/c8) ---
    is_castle = False
    castle_side = None  # "king" o "queen"
    if name == "king":
        if color == "white" and src.row == 1 and src.col == "e":
            if dst.row == 1 and dst.col == "g":
                is_castle = True
                castle_side = "king"
            elif dst.row == 1 and dst.col == "c":
                is_castle = True
                castle_side = "queen"
        elif color == "black" and src.row == 8 and src.col == "e":
            if dst.row == 8 and dst.col == "g":
                is_castle = True
                castle_side = "king"
            elif dst.row == 8 and dst.col == "c":
                is_castle = True
                castle_side = "queen"

    # --- Si es enroque, simulamos mover rey + torre ---
    if is_castle:
        # guardar piezas originales
        king_orig = mover
        # posición de torre
        if castle_side == "king":
            rook_src = Coordenate(src.row, "h")
            rook_dst = Coordenate(src.row, "f")
        else:
            rook_src = Coordenate(src.row, "a")
            rook_dst = Coordenate(src.row, "d")

        rook = board.get_piece_at(rook_src)
        captured_dst = board.get_piece_at(dst)  # por si había algo raro

        # aplicar enroque en el board
        board._set_piece_at(src, None)
        board._set_piece_at(dst, king_orig)
        if rook:
            board._set_piece_at(rook_src, None)
            board._set_piece_at(rook_dst, rook)

        try:
            kpos = dst  # rey termina en dst
            in_check = board.is_square_attacked(kpos, by_color=enemy)
            return not in_check
        finally:
            # revertir
            if rook:
                board._set_piece_at(rook_dst, None)
                board._set_piece_at(rook_src, rook)
            board._set_piece_at(dst, captured_dst)
            board._set_piece_at(src, king_orig)

    # --- Detectar si es captura al paso ---
    is_en_passant = False
    ep_captured_square: Optional[Coordenate] = None
    captured_at_dst = None
    captured_ep = None

    if (
        en_passant_target is not None and
        name == "pawn" and
        dst.row == en_passant_target.row and
        dst.col == en_passant_target.col and
        board.is_empty(dst) and
        dst.col != src.col
    ):
        is_en_passant = True
        ep_captured_square = Coordenate(src.row, dst.col)
        captured_ep = board.get_piece_at(ep_captured_square)
    else:
        captured_at_dst = board.get_piece_at(dst)

    # aplicar simulación
    board._set_piece_at(src, None)
    if is_en_passant and ep_captured_square:
        board._set_piece_at(ep_captured_square, None)
    board._set_piece_at(dst, mover)

    try:
        # localizar rey propio
        if name == "king":
            kpos = dst
        else:
            kpos = board.king_position(my_color)

        in_check = board.is_square_attacked(kpos, by_color=enemy)
        return not in_check
    finally:
        # revertir
        board._set_piece_at(dst, captured_at_dst)
        if is_en_passant and ep_captured_square:
            board._set_piece_at(ep_captured_square, captured_ep)
        board._set_piece_at(src, mover)

# ---------- generación de movimientos ----------
def generate_moves(
    board: Board,
    src: Coordenate,
    turn: str,
    en_passant_target: Optional[Coordenate] = None
) -> List[Coordenate]:
    """
    Devuelve destinos pseudo-legales (patrones + bloqueos + sin capturar aliado).
    Filtrado de jaque propio se hace aparte en legal_moves.
    Incluye:
      - movimientos normales
      - captura al paso (usando en_passant_target)
      - enroque (si rey/torre no se movieron y casillas libres + no atacadas)
    """
    piece = board.get_piece_at(src)
    if not piece:
        return []

    if getattr(piece, "color", None) != turn:
        return []

    if getattr(piece, "pinned", False):
        return []

    name = getattr(piece, "name", getattr(piece, "type", None))
    color = getattr(piece, "color", None)
    enemy = "black" if color == "white" else "white"
    res: List[Coordenate] = []

    def push_if_ok(dst: Coordenate):
        if dst.col not in "abcdefgh" or not (1 <= dst.row <= 8):
            return
        if same_color_at(board, dst, color):
            return
        res.append(dst)

    # ---------------------- CABALLO ----------------------
    if name == "knight":
        for dx, dy in [(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)]:
            dst = Coordenate(src.row + dy, chr(ord(src.col) + dx))
            push_if_ok(dst)
        return res

    # ---------------------- REY + ENROQUE ----------------
    if name == "king":
        # movimientos normales de rey (1 casilla en cualquier dirección)
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx == 0 and dy == 0:
                    continue
                dst = Coordenate(src.row + dy, chr(ord(src.col) + dx))
                push_if_ok(dst)

        # enroque
        king = piece
        if hasattr(king, "has_moved") and not king.has_moved:
            back = 1 if color == "white" else 8

            # --- Enroque corto ---
            rook_sq = Coordenate(back, "h")
            rook = board.get_piece_at(rook_sq)
            if rook and getattr(rook, "color", None) == color:
                if not hasattr(rook, "has_moved"):
                    rook.has_moved = False
                if not rook.has_moved:
                    f_sq = Coordenate(back, "f")
                    g_sq = Coordenate(back, "g")
                    if (board.is_empty(f_sq) and board.is_empty(g_sq)
                        and not board.is_square_attacked(src, enemy)
                        and not board.is_square_attacked(f_sq, enemy)
                        and not board.is_square_attacked(g_sq, enemy)):
                        res.append(g_sq)

            # --- Enroque largo ---
            rook_sq = Coordenate(back, "a")
            rook = board.get_piece_at(rook_sq)
            if rook and getattr(rook, "color", None) == color:
                if not hasattr(rook, "has_moved"):
                    rook.has_moved = False
                if not rook.has_moved:
                    d_sq = Coordenate(back, "d")
                    c_sq = Coordenate(back, "c")
                    b_sq = Coordenate(back, "b")
                    if (board.is_empty(d_sq) and board.is_empty(c_sq) and board.is_empty(b_sq)
                        and not board.is_square_attacked(src, enemy)
                        and not board.is_square_attacked(d_sq, enemy)
                        and not board.is_square_attacked(c_sq, enemy)):
                        res.append(c_sq)

        return res

    # ---------------------- ALFIL / TORRE / DAMA --------
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
                if dst.col not in "abcdefgh" or not (1 <= dst.row <= 8):
                    break
                if not path_clear(board, src, dst):
                    break
                if same_color_at(board, dst, color):
                    break
                res.append(dst)
                if enemy_at(board, dst, color):
                    break
                step += 1
        return res

    # ---------------------- PEÓN ------------------------
    if name == "pawn":
        direction = 1 if color == "white" else -1
        start = 2 if color == "white" else 7

        # avance 1
        one = Coordenate(src.row + direction, src.col)
        if 1 <= one.row <= 8 and board.is_empty(one):
            res.append(one)
            # avance doble desde fila inicial
            if src.row == start:
                two = Coordenate(src.row + 2*direction, src.col)
                inter = Coordenate(src.row + direction, src.col)
                if (1 <= two.row <= 8 and
                    board.is_empty(two) and board.is_empty(inter)):
                    res.append(two)

        # capturas diagonales normales
        for dx in (-1, 1):
            diag = Coordenate(src.row + direction, chr(ord(src.col) + dx))
            if (1 <= diag.row <= 8 and diag.col in "abcdefgh"
                and enemy_at(board, diag, color)):
                res.append(diag)

        # captura al paso
        if en_passant_target is not None:
            if (en_passant_target.row == src.row + direction and
                abs(ord(en_passant_target.col) - ord(src.col)) == 1):
                victim_square = Coordenate(src.row, en_passant_target.col)
                victim = board.get_piece_at(victim_square)
                v_name = getattr(victim, "name", getattr(victim, "type", None)) if victim else None
                v_color = getattr(victim, "color", None) if victim else None
                if victim and v_name == "pawn" and v_color != color:
                    res.append(en_passant_target)

        return res

    return res

def legal_moves(
    board: Board,
    src: Coordenate,
    turn: str,
    en_passant_target: Optional[Coordenate] = None
) -> List[Coordenate]:
    """Pseudo-legales filtrados por 'rey a salvo' tras el movimiento."""
    my_color = turn
    candidates = generate_moves(board, src, turn, en_passant_target)
    safe: List[Coordenate] = []
    for dst in candidates:
        if king_safe_after(board, src, dst, my_color, en_passant_target):
            safe.append(dst)
    return safe

# ---------- aplicar movimiento físico ----------
def apply_simple_move(
    board: Board,
    src: Coordenate,
    dst: Coordenate,
    en_passant_target: Optional[Coordenate] = None
) -> Optional[Coordenate]:
    """
    Aplica movimiento físico en el tablero:
      - movimientos normales
      - captura normal
      - captura al paso
      - enroque (mueve rey + torre)
      - promoción a dama
    Devuelve:
      - nueva casilla de en passant (si hay)
      - o None si no hay en passant disponible tras este movimiento
    """
    mover = board.get_piece_at(src)
    if mover is None:
        return None

    name = getattr(mover, "name", getattr(mover, "type", None))
    color = getattr(mover, "color", None)

    # ---- Detectar si este movimiento es enroque ----
    is_castle = False
    castle_side = None
    if name == "king":
        if color == "white" and src.row == 1 and src.col == "e":
            if dst.row == 1 and dst.col == "g":
                is_castle = True
                castle_side = "king"
            elif dst.row == 1 and dst.col == "c":
                is_castle = True
                castle_side = "queen"
        elif color == "black" and src.row == 8 and src.col == "e":
            if dst.row == 8 and dst.col == "g":
                is_castle = True
                castle_side = "king"
            elif dst.row == 8 and dst.col == "c":
                is_castle = True
                castle_side = "queen"

    if is_castle:
        # mover rey
        board._set_piece_at(src, None)
        board._set_piece_at(dst, mover)

        # mover torre correspondiente
        if castle_side == "king":
            rook_src = Coordenate(src.row, "h")
            rook_dst = Coordenate(src.row, "f")
        else:
            rook_src = Coordenate(src.row, "a")
            rook_dst = Coordenate(src.row, "d")

        rook = board.get_piece_at(rook_src)
        if rook:
            board._set_piece_at(rook_src, None)
            board._set_piece_at(rook_dst, rook)

            # marcar torre como movida
            if not hasattr(rook, "has_moved"):
                rook.has_moved = True
            else:
                rook.has_moved = True

        # marcar rey como movido
        if hasattr(mover, "has_moved"):
            mover.has_moved = True

        # enroque nunca genera en_passant_target
        return None

    # ---- Detectar captura al paso ----
    is_en_passant = False
    if (
        en_passant_target is not None and
        name == "pawn" and
        dst.row == en_passant_target.row and
        dst.col == en_passant_target.col and
        board.is_empty(dst) and
        dst.col != src.col
    ):
        is_en_passant = True
        cap_sq = Coordenate(src.row, dst.col)
        # eliminar peón capturado
        board._set_piece_at(cap_sq, None)

    # captura normal en dst
    if not is_en_passant:
        if board.get_piece_at(dst) is not None:
            board._set_piece_at(dst, None)

    # mover pieza
    board._set_piece_at(src, None)
    board._set_piece_at(dst, mover)

    # actualizar posición interna (aunque no confiemos demasiado en ella)
    try:
        vector_row = dst.row - src.row
        vector_col = (ord(dst.col) - ord(src.col))
        mover.move(vector_row=vector_row, vector_col=vector_col)
    except Exception:
        pass

    # marcar king/rook como movidos si corresponde
    if name == "king" and hasattr(mover, "has_moved"):
        mover.has_moved = True
    if name == "rook":
        if not hasattr(mover, "has_moved"):
            mover.has_moved = True
        else:
            mover.has_moved = True

    # promoción simple a dama
    if name == "pawn":
        if (color == "white" and dst.row == 8) or (color == "black" and dst.row == 1):
            q = Queen(color, dst.col, dst.row)
            board._set_piece_at(dst, q)

    # determinar nuevo en_passant_target
    new_en_passant_target: Optional[Coordenate] = None
    if name == "pawn" and dst.col == src.col and abs(dst.row - src.row) == 2:
        mid_row = (src.row + dst.row) // 2
        new_en_passant_target = Coordenate(mid_row, src.col)

    return new_en_passant_target

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

    # estado de en passant: casilla destino a la que se puede capturar al paso
    en_passant_target: Optional[Coordenate] = None

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

                if sel_sq is None:
                    # seleccionar pieza propia
                    p = board.get_piece_at(clicked)
                    if p and getattr(p, "color", None) == turn:
                        sel_sq = (r, c)
                        legal = legal_moves(board, clicked, turn, en_passant_target)
                    else:
                        sel_sq = None
                        legal = []
                else:
                    # clic en misma casilla -> deseleccionar
                    if sel_sq == (r, c):
                        sel_sq = None
                        legal = []
                        continue

                    src = idx_to_coord(sel_sq[0], sel_sq[1])
                    q = board.get_piece_at(clicked)

                    # clic en otra pieza propia -> cambiar selección
                    if q and getattr(q, "color", None) == turn:
                        sel_sq = (r, c)
                        legal = legal_moves(board, clicked, turn, en_passant_target)
                        continue

                    # intentar mover
                    if any((d.row == clicked.row and d.col == clicked.col) for d in legal):
                        # aplicar movimiento, actualizando en_passant_target
                        new_ep = apply_simple_move(board, src, clicked, en_passant_target)
                        en_passant_target = new_ep

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
