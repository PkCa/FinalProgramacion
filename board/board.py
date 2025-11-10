from typing import Optional, List, Tuple, Dict, Any

from coordinate import Coordinate
from pawn import Pawn
from knight import Knight
from bishop import Bishop
from rook import Rook
from queen import Queen
from king import King

FILES = "abcdefgh"


class Board:
    def __init__(self):
        # Crea el array 2D vacío
        self.board: List[List[Optional[object]]] = self._empty_board()
        # Coloca las piezas en su posición inicial (instanciando primero)
        self._place_initial_position()
        

    def _empty_board(self) -> List[List[Optional[object]]]:
        return [[None for _ in range(8)] for _ in range(8)]

    def _place_initial_position(self) -> None:
        # Blancos (back rank = 1, pawns = 2)
        self._place_back_rank("white", 1)
        self._place_pawns("white", 2)
        # Negros (back rank = 8, pawns = 7)
        self._place_back_rank("black", 8)
        self._place_pawns("black", 7)

    def _place_back_rank(self, color: str, row: int) -> None:
        pieces_order = [
            ("rook",   "a"),
            ("knight", "b"),
            ("bishop", "c"),
            ("queen",  "d"),
            ("king",   "e"),
            ("bishop", "f"),
            ("knight", "g"),
            ("rook",   "h"),
        ]
        for name, col in pieces_order:
            piece = self._make_piece(name, color, col, row)
            self._set_piece_at(Coordinate(col, row), piece)

    def _place_pawns(self, color: str, row: int) -> None:
        for col in FILES:
            piece = Pawn(color, col, row)
            self._set_piece_at(Coordinate(col, row), piece)

    def _make_piece(self, name: str, color: str, col: str, row: int):
        if name == "rook":
            return Rook(color, col, row)
        if name == "knight":
            return Knight(color, col, row)
        if name == "bishop":
            return Bishop(color, col, row)
        if name == "queen":
            return Queen(color, col, row)
        if name == "king":
            return King(color, col, row)
        if name == "pawn":
            return Pawn(color, col, row)
        raise ValueError(f"Pieza desconocida: {name}")


    def _coord_to_idx(self, c: Coordinate) -> Tuple[int, int]:
        r_i = c.row - 1
        c_i = ord(c.col) - ord('a')
        if not (0 <= r_i < 8 and 0 <= c_i < 8):
            raise IndexError(f"Coordenada fuera de rango: {c}")
        return r_i, c_i

    def _idx_to_coord(self, r_i: int, c_i: int) -> Coordinate:
        return Coordinate(chr(ord('a') + c_i), r_i + 1)

    def get_piece_at(self, coord: Coordinate):
        r_i, c_i = self._coord_to_idx(coord)
        return self.board[r_i][c_i]

    def _set_piece_at(self, coord: Coordinate, piece: Optional[object]) -> None:
        r_i, c_i = self._coord_to_idx(coord)
        self.board[r_i][c_i] = piece

    def is_empty(self, coord: Coordinate) -> bool:
        return self.get_piece_at(coord) is None

    def piece_color_at(self, coord: Coordinate) -> Optional[str]:
        p = self.get_piece_at(coord)
        return getattr(p, "color", None) if p else None

    # ----------------------------- Utilidades --------------------------------

    def to_coordinate(self, square: str) -> Coordinate:
        square = square.strip().lower()
        if len(square) != 2 or square[0] not in FILES or square[1] not in "12345678":
            raise ValueError(f"Square inválido: {square}")
        return Coordinate(square[0], int(square[1]))

    def king_position(self, color: str) -> Coordinate:
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and getattr(p, "color", None) == color and getattr(p, "name", getattr(p, "type", None)) == "king":
                    return self._idx_to_coord(r, c)
        raise ValueError(f"No se encontró el rey de color {color}")

    def squares_between(self, a: Coordinate, b: Coordinate) -> List[Coordinate]:
        # Devuelve las casillas estrictamente entre a y b si están alineadas en recta/diagonal
        res: List[Coordinate] = []
        df = (ord(b.col) - ord(a.col))
        dr = (b.row - a.row)
        step_f = 0 if df == 0 else (1 if df > 0 else -1)
        step_r = 0 if dr == 0 else (1 if dr > 0 else -1)

        # Si no comparten línea recta ni diagonal, no hay "entre"
        if not (df == 0 or dr == 0 or abs(df) == abs(dr)):
            return res

        f = ord(a.col) + step_f
        r = a.row + step_r
        while (f != ord(b.col)) or (r != b.row):
            if (f == ord(b.col)) and (r == b.row):
                break
            res.append(Coordinate(chr(f), r))
            f += step_f
            r += step_r
            if chr(f) == b.col and r == b.row:
                break
        # quitar extremos si se metió el destino por la condición
        return [c for c in res if not (c.col == b.col and c.row == b.row)]

    def is_square_attacked(self, coord: Coordinate, by_color: str) -> bool:
        # Ataques de peones
        for df in (-1, 1):
            r = coord.row + (-1 if by_color == "white" else 1)
            f = chr(ord(coord.col) + df)
            if f in FILES and 1 <= r <= 8:
                c = Coordinate(f, r)
                p = self.get_piece_at(c)
                if p and getattr(p, "color", None) == by_color and getattr(p, "name", getattr(p, "type", None)) == "pawn":
                    return True

        # Ataques de caballos
        for df, dr in [(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)]:
            r = coord.row + dr
            f = chr(ord(coord.col) + df)
            if f in FILES and 1 <= r <= 8:
                c = Coordinate(f, r)
                p = self.get_piece_at(c)
                if p and getattr(p, "color", None) == by_color and getattr(p, "name", getattr(p, "type", None)) == "knight":
                    return True

        # Rayos diagonales (alfiles/reinas)
        for df, dr in [(1,1),(1,-1),(-1,1),(-1,-1)]:
            if self._ray_hits(coord, df, dr, by_color, ("bishop","queen")):
                return True

        # Rayos ortogonales (torres/reinas)
        for df, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
            if self._ray_hits(coord, df, dr, by_color, ("rook","queen")):
                return True

        # Rey adyacente
        for df in (-1,0,1):
            for dr in (-1,0,1):
                if df == 0 and dr == 0:
                    continue
                r = coord.row + dr
                f = chr(ord(coord.col) + df)
                if f in FILES and 1 <= r <= 8:
                    c = Coordinate(f, r)
                    p = self.get_piece_at(c)
                    if p and getattr(p, "color", None) == by_color and getattr(p, "name", getattr(p, "type", None)) == "king":
                        return True

        return False

    def _ray_hits(self, target: Coordinate, df: int, dr: int, by_color: str, sliding: Tuple[str, ...]) -> bool:
        f_i = ord(target.col) - ord('a')
        r_i = target.row - 1
        while True:
            f_i += df
            r_i += dr
            if not (0 <= f_i < 8 and 0 <= r_i < 8):
                return False
            c = self._idx_to_coord(r_i, f_i)
            p = self.get_piece_at(c)
            if p:
                name = getattr(p, "name", getattr(p, "type", None))
                if getattr(p, "color", None) == by_color and name in sliding:
                    return True
                return False

    def find_sources(self, piece_name: str, color: str, to_coord: Coordinate, san_hint: Dict[str, Any]) -> List[Coordinate]:
        """
        Busca piezas del tipo/color dado que podrían ir a 'to_coord' por patrón básico
        y sin capturar aliado. Para peones, usa origin_file si viene en san_hint.
        (No verifica jaque propio ni "pinned"; eso lo resuelve un gestor superior.)
        """
        candidates: List[Coordinate] = []
        origin_file = san_hint.get("origin_file")

        # Peones: tratar distinto porque dependen del color/dirección
        if piece_name == "pawn":
            # Captura: archivo distinto y una fila adelante
            for df in (-1, 1):
                f = chr(ord(to_coord.col) + df)
                if origin_file and f != origin_file:
                    continue
                src = Coordinate(f, to_coord.row - (1 if color == "white" else -1))
                if self._on_board(src) and self._is_piece(src, "pawn", color):
                    # Para SAN mínima nos basta; el capturado se chequeará en apply_move
                    candidates.append(src)

            # Avances rectos (1 o 2)
            f = to_coord.col
            one = Coordinate(f, to_coord.row - (1 if color == "white" else -1))
            if self._on_board(one) and self._is_piece(one, "pawn", color) and self.is_empty(to_coord):
                candidates.append(one)
            # doble (desde inicial)
            start = 2 if color == "white" else 7
            two = Coordinate(f, to_coord.row - (2 if color == "white" else -2))
            inter = Coordinate(f, start + (1 if color == "white" else -1)) if to_coord.row == (start + (2 if color == "white" else -2)) else None
            if self._on_board(two) and self._is_piece(two, "pawn", color) and inter and self.is_empty(inter) and self.is_empty(to_coord):
                candidates.append(two)

            return self._filter_same_color_at_dest(candidates, color, to_coord)

        # Otras piezas: barrido por el tablero y patrón básico
        for r in range(8):
            for c in range(8):
                coord = self._idx_to_coord(r, c)
                p = self.get_piece_at(coord)
                if not p:
                    continue
                name = getattr(p, "name", getattr(p, "type", None))
                col = getattr(p, "color", None)
                if name != piece_name or col != color:
                    continue
                if self._pattern_ok(coord, to_coord, name) and not self._same_color_at(to_coord, color):
                    # Si hay origin_file, filtrar por archivo
                    if origin_file and coord.col != origin_file:
                        continue
                    # camino libre si desliza
                    if name in ("bishop","rook","queen") and not self._path_clear(coord, to_coord):
                        continue
                    candidates.append(coord)

        return candidates

    def apply_move(self, move: Any) -> None:
        """
        Aplica un movimiento tipo Move (como el usado en un MovementsRecorder).
        Soporta:
          - movimientos normales y capturas
          - captura al paso si move.is_en_passant_capture y move._captured_square_for_ep definido
          - enroque si move.castle_side en {'king','queen'}
          - promoción si move.promotion en {'q','r','b','n'}
        """
        # Enroque
        if getattr(move, "castle_side", None) in ("king", "queen"):
            self._apply_castle(move.color, move.castle_side)
            return

        src = move.src
        dst = move.dst
        mover = self.get_piece_at(src)
        if mover is None:
            raise ValueError(f"No hay pieza en {src} para mover.")

        # Captura normal
        if self.get_piece_at(dst) is not None:
            self._set_piece_at(dst, None)

        # Captura al paso
        if getattr(move, "is_en_passant_capture", False):
            cap_sq = getattr(move, "_captured_square_for_ep", None)
            if cap_sq:
                self._set_piece_at(cap_sq, None)

        # Mover
        self._set_piece_at(src, None)
        self._set_piece_at(dst, mover)
        # Actualizar pos interna de la pieza (usando su método move por vector)
        try:
            vector_row = dst.row - src.row
            vector_col = (ord(dst.col) - ord(src.col))
            mover.move(vector_row=vector_row, vector_col=vector_col)
        except Exception:
            # Si tu Piece.move valida y lanza, puedes optar por no llamarlo aquí.
            pass

        # Promoción
        promo = getattr(move, "promotion", None)
        if promo:
            promo_map = {"q": "queen", "r": "rook", "b": "bishop", "n": "knight"}
            name = promo_map.get(promo.lower())
            if name:
                new_piece = self._make_piece(name, getattr(mover, "color", None), dst.col, dst.row)
                self._set_piece_at(dst, new_piece)

    def _apply_castle(self, color: str, side: str) -> None:
        back = 1 if color == "white" else 8
        king_from = Coordinate("e", back)
        if side == "king":
            king_to, rook_from, rook_to = Coordinate("g", back), Coordinate("h", back), Coordinate("f", back)
        else:
            king_to, rook_from, rook_to = Coordinate("c", back), Coordinate("a", back), Coordinate("d", back)

        king = self.get_piece_at(king_from)
        rook = self.get_piece_at(rook_from)
        if not king or not rook:
            raise ValueError("No se puede enrocar: faltan piezas.")

        self._set_piece_at(king_from, None)
        self._set_piece_at(rook_from, None)
        self._set_piece_at(king_to, king)
        self._set_piece_at(rook_to, rook)

        # Actualizar internas de movimiento (opcional)
        try:
            king.move(vector_row=0, vector_col=(ord(king_to.col) - ord(king_from.col)))
        except Exception:
            pass

    def _on_board(self, c: Coordinate) -> bool:
        return c.col in FILES and 1 <= c.row <= 8

    def _is_piece(self, coord: Coordinate, name: str, color: str) -> bool:
        p = self.get_piece_at(coord)
        if not p:
            return False
        pname = getattr(p, "name", getattr(p, "type", None))
        pcolor = getattr(p, "color", None)
        return pname == name and pcolor == color

    def _same_color_at(self, coord: Coordinate, color: str) -> bool:
        p = self.get_piece_at(coord)
        return bool(p) and getattr(p, "color", None) == color

    def _pattern_ok(self, src: Coordinate, dst: Coordinate, name: str) -> bool:
        df = (ord(dst.col) - ord(src.col))
        dr = (dst.row - src.row)
        adf, adr = abs(df), abs(dr)

        if name == "king":
            return max(adf, adr) == 1
        if name == "knight":
            return (adf, adr) in {(1,2),(2,1)}
        if name == "bishop":
            return adf == adr and adf > 0
        if name == "rook":
            return (df == 0 or dr == 0) and not (df == 0 and dr == 0)
        if name == "queen":
            return (adf == adr and adf > 0) or (df == 0 or dr == 0) and not (df == 0 and dr == 0)
        if name == "pawn":
            # Patrón mínimo; las verificaciones finas (bloqueos, capturas) las hace quien llama.
            return True
        return False

    def _path_clear(self, src: Coordinate, dst: Coordinate) -> bool:
        # Para piezas deslizantes (bishop/rook/queen)
        between = self.squares_between(src, dst)
        return all(self.is_empty(c) for c in between)

    def to_ascii(self) -> str:
        """
        Devuelve una representación simple del tablero:
        P (peón), N, B, R, Q, K en may/min para blancas/negras.
        """
        letter = {
            "pawn": "P",
            "knight": "N",
            "bishop": "B",
            "rook": "R",
            "queen": "Q",
            "king": "K",
        }
        lines: List[str] = []
        for r in range(7, -1, -1):
            row = []
            for c in range(8):
                p = self.board[r][c]
                if not p:
                    row.append(".")
                else:
                    name = getattr(p, "name", getattr(p, "type", None))
                    ch = letter.get(name, "?")
                    if getattr(p, "color", None) == "black":
                        ch = ch.lower()
                    row.append(ch)
            lines.append(f"{r+1} " + " ".join(row))
        lines.append("  a b c d e f g h")
        return "\n".join(lines)