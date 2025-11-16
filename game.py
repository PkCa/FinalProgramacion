# game.py
# ---------------------------------------------------------------------
# Chess con:
#  - Click-to-move
#  - Promoción simple a dama
#  - Enroque
#  - En passant
#  - Menú principal
#  - Menú de carga
#  - Guardar partida (.chess) en formato UCI
#  - Barra lateral con botones (guardar, menú, tablas, rendición)
#  - Popups con overlay oscuro (tablas, rendición, fin de partida)
#  - Detección de jaque mate y ahogado
# ---------------------------------------------------------------------

import os
import sys
import pygame
from typing import List, Optional, Tuple
from datetime import datetime

from board.board import Board
from board.coordenates import Coordenate
from pieces.queen import Queen  # para promover peones

# ---------- constantes ----------
TILE_SIZE = 64
BOARD_SIZE = 8
BOARD_PIXEL_W = TILE_SIZE * BOARD_SIZE
SIDEBAR_W = 160

WINDOW_W = BOARD_PIXEL_W + SIDEBAR_W
WINDOW_H = BOARD_PIXEL_W

LIGHT_SQ = (240, 217, 181)
DARK_SQ  = (181, 136, 99)

HOVER_COLOR = (255, 255, 0, 60)
SEL_COLOR   = (0, 200, 255, 80)
MOVE_COLOR  = (80, 160, 120, 120)

SIDEBAR_BG = (40, 40, 40)

NAME_TO_SPRITEBASE = {
    "pawn":   "pawn",
    "rook":   "rook",
    "bishop": "bishop",
    "queen":  "queen",
    "king":   "king",
    "knight": "knight"
}

GAMES_DIR = "games"


# ---------- helpers básicos ----------
def C(col: str, row: int) -> Coordenate:
    return Coordenate(row, col)


def idx_to_coord(r: int, c: int) -> Coordenate:
    return Coordenate(r + 1, chr(ord('a') + c))


def mouse_to_indices(mx: int, my: int) -> Optional[Tuple[int, int]]:
    if mx >= BOARD_PIXEL_W:  # clic en barra lateral
        return None
    c = mx // TILE_SIZE
    r_screen = my // TILE_SIZE
    r = (BOARD_SIZE - 1) - r_screen
    if 0 <= r < 8 and 0 <= c < 8:
        return (r, c)
    return None


# ---------- carga de imágenes ----------
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
                print(f"[WARN] No se pudo cargar sprite {filename}: {e}")
                surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                pygame.draw.circle(
                    surf, (220, 50, 50),
                    (tile_size//2, tile_size//2),
                    tile_size//3
                )
                sprites[(piece_name, color)] = surf
    return sprites


def load_board_background(width: int, height: int):
    root = os.path.dirname(__file__)
    candidates = [
        os.path.join(root, "board.png"),
        os.path.join(root, "sprites", "board.png")
    ]
    for path in candidates:
        try:
            img = pygame.image.load(path).convert_alpha()
            if img.get_width() != width or img.get_height() != height:
                img = pygame.transform.smoothscale(img, (width, height))
            return img
        except:
            pass
    print("[INFO] No se encontró board.png, usando casillas de colores.")
    return None


def load_background_image():
    root = os.path.dirname(__file__)
    path = os.path.join(root, "sprites", "background.png")
    try:
        img = pygame.image.load(path).convert()
        img = pygame.transform.smoothscale(img, (WINDOW_W, WINDOW_H))
        return img
    except Exception as e:
        print(f"[INFO] No se pudo cargar background.png: {e}")
        return None


def load_icon(name: str, size: int):
    root = os.path.dirname(__file__)
    path = os.path.join(root, "sprites", name)
    try:
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, (size, size))
        return img
    except Exception as e:
        print(f"[WARN] No se pudo cargar icono {name}: {e}")
        return None


# ---------- dibujo del tablero ----------
def draw_board(surface, board_bg):
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


def draw_pieces(surface, board: Board, sprites):
    for r in range(8):
        for c in range(8):
            p = board.board[r][c]
            if not p:
                continue
            x = c * TILE_SIZE
            y = (7 - r) * TILE_SIZE
            name = getattr(p, "name", getattr(p, "type", None))
            color = getattr(p, "color", None)
            img = sprites.get((name, color))
            if img:
                surface.blit(img, (x, y))


def draw_overlay_square(surface, r_idx, c_idx, rgba):
    overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    overlay.fill(rgba)
    x = c_idx * TILE_SIZE
    y = (7 - r_idx) * TILE_SIZE
    surface.blit(overlay, (x, y))


# ---------- barra lateral ----------
def get_sidebar_rects():
    center_x = BOARD_PIXEL_W + SIDEBAR_W // 2
    rects = {}

    # Guardar
    rects["save"] = pygame.Rect(0, 0, 72, 72)
    rects["save"].center = (center_x, 80)

    # Menú principal / cerrar
    rects["close"] = pygame.Rect(0, 0, 72, 72)
    rects["close"].center = (center_x, 180)

    # Tablas
    rects["draw"] = pygame.Rect(0, 0, 72, 72)
    rects["draw"].center = (center_x, 280)

    # Rendición
    rects["resign"] = pygame.Rect(0, 0, 72, 72)
    rects["resign"].center = (center_x, 380)

    return rects


def draw_sidebar(surface, save_icon, close_icon, draw_icon, resign_icon, font):
    sidebar = pygame.Rect(BOARD_PIXEL_W, 0, SIDEBAR_W, WINDOW_H)
    pygame.draw.rect(surface, SIDEBAR_BG, sidebar)

    rects = get_sidebar_rects()

    def draw_button(rect, icon, fallback_text):
        pygame.draw.rect(surface, (80, 80, 80), rect, border_radius=8)
        if icon:
            img_rect = icon.get_rect(center=rect.center)
            surface.blit(icon, img_rect)
        else:
            txt = font.render(fallback_text, True, (240, 240, 240))
            screen_txt = txt.get_rect(center=rect.center)
            surface.blit(txt, screen_txt)

    draw_button(rects["save"], save_icon, "Save")
    draw_button(rects["close"], close_icon, "Menú")
    draw_button(rects["draw"], draw_icon, "Tablas")
    draw_button(rects["resign"], resign_icon, "Rendir")

    return rects


# ---------- lógica de ataque / seguridad ----------
def enemy_at(board: Board, dst: Coordenate, my_color: str):
    p = board.get_piece_at(dst)
    return p and getattr(p, "color", None) != my_color


def same_color_at(board: Board, dst: Coordenate, my_color: str):
    p = board.get_piece_at(dst)
    return p and getattr(p, "color", None) == my_color


def path_clear(board: Board, a: Coordenate, b: Coordenate):
    return all(board.is_empty(c) for c in board.squares_between(a, b))


def king_safe_after(board: Board, src: Coordenate, dst: Coordenate, color: str, ep_target):
    enemy = "black" if color == "white" else "white"
    mover = board.get_piece_at(src)
    if mover is None:
        return False

    name = getattr(mover, "name", getattr(mover, "type", None))

    # --- Enroque ---
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

    if is_castle:
        king_orig = mover
        if castle_side == "king":
            rook_src = Coordenate(src.row, "h")
            rook_dst = Coordenate(src.row, "f")
        else:
            rook_src = Coordenate(src.row, "a")
            rook_dst = Coordenate(src.row, "d")

        rook = board.get_piece_at(rook_src)
        captured_dst = board.get_piece_at(dst)

        board._set_piece_at(src, None)
        board._set_piece_at(dst, mover)
        if rook:
            board._set_piece_at(rook_src, None)
            board._set_piece_at(rook_dst, rook)

        try:
            kpos = dst
            return not board.is_square_attacked(kpos, enemy)
        finally:
            if rook:
                board._set_piece_at(rook_dst, None)
                board._set_piece_at(rook_src, rook)
            board._set_piece_at(dst, captured_dst)
            board._set_piece_at(src, king_orig)

    # --- En passant ---
    is_ep = (
        name == "pawn" and
        ep_target is not None and
        dst.row == ep_target.row and
        dst.col == ep_target.col and
        dst.col != src.col and
        board.is_empty(dst)
    )

    captured_dst = board.get_piece_at(dst)
    captured_ep = None
    cap_sq = None

    if is_ep:
        cap_sq = Coordenate(src.row, dst.col)
        captured_ep = board.get_piece_at(cap_sq)

    board._set_piece_at(src, None)
    if is_ep:
        board._set_piece_at(cap_sq, None)
    board._set_piece_at(dst, mover)

    try:
        kpos = dst if name == "king" else board.king_position(color)
        return not board.is_square_attacked(kpos, enemy)
    finally:
        board._set_piece_at(dst, captured_dst)
        if is_ep:
            board._set_piece_at(cap_sq, captured_ep)
        board._set_piece_at(src, mover)


# ---------- generación de movimientos ----------
def generate_moves(board: Board, src: Coordenate, turn: str, ep_target):
    p = board.get_piece_at(src)
    if not p:
        return []
    if getattr(p, "color", None) != turn:
        return []
    if getattr(p, "pinned", False):
        return []

    name = getattr(p, "name", getattr(p, "type", None))
    color = getattr(p, "color", None)
    enemy = "black" if color == "white" else "white"
    res: List[Coordenate] = []

    def push(dst: Coordenate):
        if dst.col not in "abcdefgh" or not (1 <= dst.row <= 8):
            return
        if same_color_at(board, dst, color):
            return
        res.append(dst)

    # Caballo
    if name == "knight":
        for dx, dy in [(1, 2), (2, 1), (2, -1), (1, -2),
                       (-1, -2), (-2, -1), (-2, 1), (-1, 2)]:
            push(Coordenate(src.row + dy, chr(ord(src.col) + dx)))
        return res

    # Rey + enroque
    if name == "king":
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1),
                       (0, -1),             (0, 1),
                       (1, -1),  (1, 0),  (1, 1)]:
            push(Coordenate(src.row + dy, chr(ord(src.col) + dx)))

        if hasattr(p, "has_moved") and not p.has_moved:
            row = 1 if color == "white" else 8

            # enroque corto
            rook = board.get_piece_at(Coordenate(row, "h"))
            if rook and getattr(rook, "color", None) == color:
                if not getattr(rook, "has_moved", False):
                    f = Coordenate(row, "f")
                    g = Coordenate(row, "g")
                    if board.is_empty(f) and board.is_empty(g):
                        if (not board.is_square_attacked(src, enemy)
                            and not board.is_square_attacked(f, enemy)
                            and not board.is_square_attacked(g, enemy)):
                            res.append(g)

            # enroque largo
            rook = board.get_piece_at(Coordenate(row, "a"))
            if rook and getattr(rook, "color", None) == color:
                if not getattr(rook, "has_moved", False):
                    d = Coordenate(row, "d")
                    c = Coordenate(row, "c")
                    b = Coordenate(row, "b")
                    if board.is_empty(d) and board.is_empty(c) and board.is_empty(b):
                        if (not board.is_square_attacked(src, enemy)
                            and not board.is_square_attacked(d, enemy)
                            and not board.is_square_attacked(c, enemy)):
                            res.append(c)

        return res

    # Deslizantes
    if name in ("bishop", "rook", "queen"):
        dirs = []
        if name in ("bishop", "queen"):
            dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        if name in ("rook", "queen"):
            dirs += [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dx, dy in dirs:
            step = 1
            while True:
                dst = Coordenate(src.row + dy * step, chr(ord(src.col) + dx * step))
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

    # Peón
    if name == "pawn":
        direction = 1 if color == "white" else -1
        start_row = 2 if color == "white" else 7

        # avance 1
        one = Coordenate(src.row + direction, src.col)
        if 1 <= one.row <= 8 and board.is_empty(one):
            res.append(one)

            # avance doble
            if src.row == start_row:
                two = Coordenate(src.row + 2*direction, src.col)
                inter = Coordenate(src.row + direction, src.col)
                if (1 <= two.row <= 8 and
                    board.is_empty(two) and board.is_empty(inter)):
                    res.append(two)

        # capturas normales
        for dx in (-1, 1):
            diag = Coordenate(src.row + direction, chr(ord(src.col) + dx))
            if 1 <= diag.row <= 8 and diag.col in "abcdefgh":
                if enemy_at(board, diag, color):
                    res.append(diag)

        # captura al paso
        if ep_target is not None:
            if (ep_target.row == src.row + direction and
                abs(ord(ep_target.col) - ord(src.col)) == 1):
                victim_sq = Coordenate(src.row, ep_target.col)
                victim = board.get_piece_at(victim_sq)
                if victim:
                    vname = getattr(victim, "name", getattr(victim, "type", None))
                    vcolor = getattr(victim, "color", None)
                    if vname == "pawn" and vcolor != color:
                        res.append(ep_target)

        return res

    return res


def legal_moves(board: Board, src: Coordenate, turn: str, ep_target):
    res: List[Coordenate] = []
    for dst in generate_moves(board, src, turn, ep_target):
        if king_safe_after(board, src, dst, turn, ep_target):
            res.append(dst)
    return res


# ---------- aplicar movimiento ----------
def apply_simple_move(board: Board, src: Coordenate, dst: Coordenate, ep_target):
    mover = board.get_piece_at(src)
    if not mover:
        return None

    name = getattr(mover, "name", getattr(mover, "type", None))
    color = getattr(mover, "color", None)

    # Enroque
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
        board._set_piece_at(src, None)
        board._set_piece_at(dst, mover)

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
            setattr(rook, "has_moved", True)

        if hasattr(mover, "has_moved"):
            mover.has_moved = True
        else:
            setattr(mover, "has_moved", True)

        return None  # enroque no genera en passant

    # en passant
    is_ep = (
        name == "pawn" and
        ep_target is not None and
        dst.row == ep_target.row and
        dst.col == ep_target.col and
        dst.col != src.col and
        board.is_empty(dst)
    )

    if is_ep:
        cap_sq = Coordenate(src.row, dst.col)
        board._set_piece_at(cap_sq, None)

    # captura normal
    if not is_ep:
        if board.get_piece_at(dst):
            board._set_piece_at(dst, None)

    # mover pieza
    board._set_piece_at(src, None)
    board._set_piece_at(dst, mover)

    # actualizar posición interna (aunque tengas el lío row/col, lo dejamos como está)
    try:
        mover.position.move_row(dst.row - src.row)
        mover.position.move_col(ord(dst.col) - ord(src.col))
    except Exception:
        pass

    # marcar rey/torre como movidos
    if name == "king":
        if hasattr(mover, "has_moved"):
            mover.has_moved = True
        else:
            setattr(mover, "has_moved", True)
    if name == "rook":
        setattr(mover, "has_moved", True)

    # promoción
    if name == "pawn":
        if (color == "white" and dst.row == 8) or (color == "black" and dst.row == 1):
            q = Queen(color, dst.col, dst.row)
            board._set_piece_at(dst, q)

    # nueva casilla de en passant
    if name == "pawn" and dst.col == src.col and abs(dst.row - src.row) == 2:
        mid_row = (src.row + dst.row) // 2
        return Coordenate(mid_row, src.col)

    return None


# ---------- chequeo de jaque / mate / ahogado ----------
def is_in_check(board: Board, color: str) -> bool:
    kpos = board.king_position(color)
    enemy = "black" if color == "white" else "white"
    return board.is_square_attacked(kpos, enemy)


def has_any_legal_move(board: Board, color: str, ep_target) -> bool:
    for r in range(8):
        for c in range(8):
            coord = idx_to_coord(r, c)
            piece = board.get_piece_at(coord)
            if not piece:
                continue
            if getattr(piece, "color", None) != color:
                continue
            moves = legal_moves(board, coord, color, ep_target)
            if moves:
                return True
    return False


def is_checkmate(board: Board, color: str, ep_target) -> bool:
    if not is_in_check(board, color):
        return False
    if has_any_legal_move(board, color, ep_target):
        return False
    return True


def is_stalemate(board: Board, color: str, ep_target) -> bool:
    if is_in_check(board, color):
        return False
    if has_any_legal_move(board, color, ep_target):
        return False
    return True


# ---------- guardado y carga ----------
def coord_to_alg(c: Coordenate) -> str:
    return f"{c.col}{c.row}"


def alg_to_coord(sq: str) -> Coordenate:
    return Coordenate(int(sq[1]), sq[0])


def save_game(history: List[str]):
    if not history:
        print("[INFO] Nada para guardar.")
        return
    os.makedirs(GAMES_DIR, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(GAMES_DIR, f"game_{now}.chess")
    try:
        with open(path, "w", encoding="utf-8") as f:
            for mv in history:
                f.write(mv + "\n")
        print(f"[INFO] Partida guardada en {path}")
    except Exception as e:
        print(f"[ERROR] No se pudo guardar la partida: {e}")


def list_saved_games() -> List[str]:
    if not os.path.isdir(GAMES_DIR):
        return []
    files = [
        os.path.join(GAMES_DIR, f)
        for f in os.listdir(GAMES_DIR)
        if f.lower().endswith(".chess")
    ]
    files.sort()
    return files


def load_game_from_file(path: str):
    board = Board()
    turn = "white"
    ep = None
    history: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except Exception as e:
        print(f"[ERROR] No se pudo leer {path}: {e}")
        return board, "white", None, []

    for mv in lines:
        if len(mv) < 4:
            continue
        src = alg_to_coord(mv[:2])
        dst = alg_to_coord(mv[2:4])
        ep = apply_simple_move(board, src, dst, ep)
        history.append(mv)
        turn = "black" if turn == "white" else "white"

    print(f"[INFO] Partida cargada desde {path}")
    return board, turn, ep, history


# ---------- menú principal ----------
def draw_menu(screen, bg, font):
    if bg:
        screen.blit(bg, (0, 0))
    else:
        screen.fill((0, 0, 0))
    title = font.render("Chess", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(WINDOW_W // 2, WINDOW_H // 4)))


def make_menu_buttons(font):
    w, h = 260, 60
    x = (WINDOW_W - w) // 2
    new_rect = pygame.Rect(x, WINDOW_H // 2 - 40, w, h)
    load_rect = pygame.Rect(x, WINDOW_H // 2 + 40, w, h)
    return (new_rect, "Nueva partida"), (load_rect, "Cargar partida")


def draw_menu_buttons(screen, buttons, font):
    for rect, label in buttons:
        pygame.draw.rect(screen, (60, 60, 60), rect, border_radius=10)
        text = font.render(label, True, (240, 240, 240))
        screen.blit(text, text.get_rect(center=rect.center))


# ---------- menú cargar partida ----------
def draw_load_menu(screen, bg, font, files, back_icon):
    if bg:
        screen.blit(bg, (0, 0))
    else:
        screen.fill((20, 20, 20))

    title = font.render("Cargar partida", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 40)))

    # botón volver
    back_rect = pygame.Rect(0, 0, 72, 72)
    back_rect.center = (WINDOW_W // 2, WINDOW_H - 80)
    pygame.draw.rect(screen, (80, 80, 80), back_rect, border_radius=8)
    if back_icon:
        screen.blit(back_icon, back_icon.get_rect(center=back_rect.center))
    else:
        txt = font.render("Volver", True, (240, 240, 240))
        screen.blit(txt, txt.get_rect(center=back_rect.center))

    # lista de archivos
    items = []
    y = 120
    w, h = 400, 40
    for i, path in enumerate(files):
        rect = pygame.Rect((WINDOW_W - w) // 2, y + i * (h + 10), w, h)
        pygame.draw.rect(screen, (60, 60, 60), rect, border_radius=8)
        txt = font.render(os.path.basename(path), True, (230, 230, 230))
        screen.blit(txt, txt.get_rect(center=rect.center))
        items.append((rect, path))

    return items, back_rect


# ---------- popups (overlay oscuro) ----------
def draw_overlay_dark(screen):
    overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))


def get_draw_offer_popup_rects():
    w, h = 420, 160
    box = pygame.Rect(0, 0, w, h)
    box.center = (WINDOW_W // 2, WINDOW_H // 2)

    btn_w, btn_h = 120, 40
    yes_rect = pygame.Rect(0, 0, btn_w, btn_h)
    no_rect = pygame.Rect(0, 0, btn_w, btn_h)

    yes_rect.center = (box.centerx - 80, box.centery + 30)
    no_rect.center  = (box.centerx + 80, box.centery + 30)

    return {"box": box, "yes": yes_rect, "no": no_rect}


def draw_draw_offer_popup(screen, font):
    draw_overlay_dark(screen)
    rects = get_draw_offer_popup_rects()
    box = rects["box"]
    pygame.draw.rect(screen, (40, 40, 40), box, border_radius=12)

    title = font.render("¿Aceptar tablas?", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(box.centerx, box.top + 40)))

    # botones
    for key, label in (("yes", "Sí"), ("no", "No")):
        r = rects[key]
        pygame.draw.rect(screen, (90, 90, 90), r, border_radius=8)
        txt = font.render(label, True, (240, 240, 240))
        screen.blit(txt, txt.get_rect(center=r.center))


def get_resign_popup_rects():
    w, h = 460, 180
    box = pygame.Rect(0, 0, w, h)
    box.center = (WINDOW_W // 2, WINDOW_H // 2)

    btn_w, btn_h = 150, 40
    white_rect = pygame.Rect(0, 0, btn_w, btn_h)
    black_rect = pygame.Rect(0, 0, btn_w, btn_h)

    white_rect.center = (box.centerx - 90, box.centery + 40)
    black_rect.center = (box.centerx + 90, box.centery + 40)

    return {"box": box, "white": white_rect, "black": black_rect}


def draw_resign_popup(screen, font):
    draw_overlay_dark(screen)
    rects = get_resign_popup_rects()
    box = rects["box"]
    pygame.draw.rect(screen, (40, 40, 40), box, border_radius=12)

    title = font.render("¿Quién se rinde?", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(box.centerx, box.top + 50)))

    for key, label in (("white", "Blancas"), ("black", "Negras")):
        r = rects[key]
        pygame.draw.rect(screen, (90, 90, 90), r, border_radius=8)
        txt = font.render(label, True, (240, 240, 240))
        screen.blit(txt, txt.get_rect(center=r.center))


def get_game_over_popup_rects():
    w, h = 480, 200
    box = pygame.Rect(0, 0, w, h)
    box.center = (WINDOW_W // 2, WINDOW_H // 2)

    btn_w, btn_h = 170, 44
    new_rect = pygame.Rect(0, 0, btn_w, btn_h)
    menu_rect = pygame.Rect(0, 0, btn_w, btn_h)

    new_rect.center  = (box.centerx - 100, box.centery + 50)
    menu_rect.center = (box.centerx + 100, box.centery + 50)

    return {"box": box, "new": new_rect, "menu": menu_rect}


def draw_game_over_popup(screen, font, message: str):
    draw_overlay_dark(screen)
    rects = get_game_over_popup_rects()
    box = rects["box"]
    pygame.draw.rect(screen, (40, 40, 40), box, border_radius=12)

    title = font.render("Fin de la partida", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(box.centerx, box.top + 40)))

    msg = font.render(message, True, (240, 240, 0))
    screen.blit(msg, msg.get_rect(center=(box.centerx, box.top + 90)))

    for key, label in (("new", "Nuevo juego"), ("menu", "Menú principal")):
        r = rects[key]
        pygame.draw.rect(screen, (90, 90, 90), r, border_radius=8)
        txt = font.render(label, True, (240, 240, 240))
        screen.blit(txt, txt.get_rect(center=r.center))


# ---------- main ----------
def main():
    pygame.init()
    pygame.display.set_caption("Chess — Pygame")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 32)

    sprites = load_sprites(TILE_SIZE)
    board_bg = load_board_background(BOARD_PIXEL_W, WINDOW_H)
    bg_menu = load_background_image()

    save_icon  = load_icon("save.png",   40)
    close_icon = load_icon("close.png",  40)
    back_icon  = load_icon("back.png",   40)
    draw_icon  = load_icon("tablas.png", 40)
    resign_icon = load_icon("flag.png",  40)

    # estado general
    state = "menu"  # "menu", "load_menu", "game", "popup_draw", "popup_resign", "game_over"

    # estado de partida
    board: Optional[Board] = None
    turn = "white"
    sel_sq: Optional[Tuple[int, int]] = None
    hover_sq: Optional[Tuple[int, int]] = None
    legal: List[Coordenate] = []
    ep_target: Optional[Coordenate] = None
    history: List[str] = []

    # estado menú de carga
    load_files: List[str] = []

    # estado de fin / mensajes
    result_message: str = ""

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                break

            # -------------------- MENÚ PRINCIPAL --------------------
            if state == "menu":
                new_btn, load_btn = make_menu_buttons(font)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if new_btn[0].collidepoint(mx, my):
                        board = Board()
                        turn = "white"
                        sel_sq = None
                        hover_sq = None
                        legal = []
                        ep_target = None
                        history = []
                        state = "game"
                    elif load_btn[0].collidepoint(mx, my):
                        load_files = list_saved_games()
                        state = "load_menu"

            # -------------------- MENÚ DE CARGA --------------------
            elif state == "load_menu":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos

                    # reconstruir rects de archivos
                    items = []
                    y = 120
                    w, h = 400, 40
                    for i, path in enumerate(load_files):
                        rect = pygame.Rect((WINDOW_W - w) // 2, y + i * (h + 10), w, h)
                        items.append((rect, path))

                    # botón volver
                    back_rect = pygame.Rect(0, 0, 72, 72)
                    back_rect.center = (WINDOW_W // 2, WINDOW_H - 80)

                    if back_rect.collidepoint(mx, my):
                        state = "menu"
                        continue

                    clicked = None
                    for rect, path in items:
                        if rect.collidepoint(mx, my):
                            clicked = path
                            break

                    if clicked:
                        board, turn, ep_target, history = load_game_from_file(clicked)
                        sel_sq = None
                        hover_sq = None
                        legal = []
                        state = "game"

            # -------------------- POPUP TABLAS --------------------
            elif state == "popup_draw":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    rects = get_draw_offer_popup_rects()
                    if rects["yes"].collidepoint(mx, my):
                        result_message = "Partida empatada por tablas"
                        state = "game_over"
                    elif rects["no"].collidepoint(mx, my):
                        state = "game"

            # -------------------- POPUP RENDICIÓN --------------------
            elif state == "popup_resign":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    rects = get_resign_popup_rects()
                    if rects["white"].collidepoint(mx, my):
                        result_message = "Negras ganan por rendición de Blancas"
                        state = "game_over"
                    elif rects["black"].collidepoint(mx, my):
                        result_message = "Blancas ganan por rendición de Negras"
                        state = "game_over"

            # -------------------- PANTALLA DE GAME OVER --------------------
            elif state == "game_over":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    rects = get_game_over_popup_rects()
                    if rects["new"].collidepoint(mx, my):
                        # Nuevo juego
                        board = Board()
                        turn = "white"
                        sel_sq = None
                        hover_sq = None
                        legal = []
                        ep_target = None
                        history = []
                        state = "game"
                    elif rects["menu"].collidepoint(mx, my):
                        # Volver al menú
                        board = None
                        sel_sq = None
                        hover_sq = None
                        legal = []
                        ep_target = None
                        history = []
                        state = "menu"

            # -------------------- MODO PARTIDA --------------------
            elif state == "game" and board is not None:
                if event.type == pygame.MOUSEMOTION:
                    mi = mouse_to_indices(*event.pos)
                    hover_sq = (mi[0], mi[1]) if mi else None

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos

                    # clic en barra lateral
                    if mx >= BOARD_PIXEL_W:
                        rects = get_sidebar_rects()

                        if rects["save"].collidepoint(mx, my):
                            save_game(history)

                        elif rects["close"].collidepoint(mx, my):
                            # volver al menú, descartando la posición actual
                            board = None
                            sel_sq = None
                            hover_sq = None
                            legal = []
                            ep_target = None
                            history = []
                            state = "menu"

                        elif rects["draw"].collidepoint(mx, my):
                            # ofrecer tablas
                            state = "popup_draw"

                        elif rects["resign"].collidepoint(mx, my):
                            # abrir popup de rendición
                            state = "popup_resign"

                        continue  # no seguir con lógica de movimiento

                    # clic en tablero
                    mi = mouse_to_indices(mx, my)
                    if not mi:
                        continue
                    r, c = mi
                    clicked = idx_to_coord(r, c)

                    if sel_sq is None:
                        p = board.get_piece_at(clicked)
                        if p and getattr(p, "color", None) == turn:
                            sel_sq = (r, c)
                            legal = legal_moves(board, clicked, turn, ep_target)
                        else:
                            sel_sq = None
                            legal = []
                    else:
                        # clic en la misma casilla -> deseleccionar
                        if sel_sq == (r, c):
                            sel_sq = None
                            legal = []
                            continue

                        src = idx_to_coord(sel_sq[0], sel_sq[1])
                        q = board.get_piece_at(clicked)

                        # cambiar selección si clic en otra propia
                        if q and getattr(q, "color", None) == turn:
                            sel_sq = (r, c)
                            legal = legal_moves(board, clicked, turn, ep_target)
                            continue

                        # si el destino es legal, mover
                        if any(d.row == clicked.row and d.col == clicked.col for d in legal):
                            mv = f"{src.col}{src.row}{clicked.col}{clicked.row}"
                            history.append(mv)

                            ep_target = apply_simple_move(board, src, clicked, ep_target)

                            # cambiar turno
                            turn = "black" if turn == "white" else "white"

                            # comprobar mate / ahogado
                            if is_checkmate(board, turn, ep_target):
                                if turn == "white":
                                    result_message = "Negras ganan por jaque mate"
                                else:
                                    result_message = "Blancas ganan por jaque mate"
                                state = "game_over"
                            elif is_stalemate(board, turn, ep_target):
                                result_message = "Tablas por ahogado"
                                state = "game_over"

                        # reset selección
                        sel_sq = None
                        legal = []

        # ---------- DIBUJO ----------
        if not running:
            break

        if state == "menu":
            draw_menu(screen, bg_menu, font)
            draw_menu_buttons(screen, make_menu_buttons(font), font)

        elif state == "load_menu":
            draw_load_menu(screen, bg_menu, font, load_files, back_icon)

        elif state in ("game", "popup_draw", "popup_resign", "game_over") and board is not None:
            # base: tablero + piezas + barra lateral
            draw_board(screen, board_bg)
            draw_pieces(screen, board, sprites)

            if sel_sq:
                draw_overlay_square(screen, sel_sq[0], sel_sq[1], SEL_COLOR)
                for d in legal:
                    draw_overlay_square(
                        screen,
                        d.row - 1,
                        ord(d.col) - ord('a'),
                        MOVE_COLOR
                    )
            if hover_sq and state == "game":
                draw_overlay_square(screen, hover_sq[0], hover_sq[1], HOVER_COLOR)

            draw_sidebar(screen, save_icon, close_icon, draw_icon, resign_icon, font)

            # popups encima
            if state == "popup_draw":
                draw_draw_offer_popup(screen, font)
            elif state == "popup_resign":
                draw_resign_popup(screen, font)
            elif state == "game_over":
                draw_game_over_popup(screen, font, result_message)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
