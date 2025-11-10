from coordinate import Coordinate

FILES = "abcdefgh"
RANKS = "12345678"

PIECE_LETTER = {
    "king": "K",
    "queen": "Q",
    "rook": "R",
    "bishop": "B",
    "knight": "N",
    "pawn": "",
}
LETTER_PIECE = {v: k for k, v in PIECE_LETTER.items() if v} 

CHECK_PATTERNS = False

class MovementsChecker:
    history: str

    def __init__(self):
        self.history = ""

    def is_valid_move(self, current: Coordinate, piece_type: str, piece_instance, target: Coordinate) -> bool:

        if getattr(piece_instance, "pinned", False):
            return False

        color = getattr(piece_instance, "color", None)
        if color not in ("white", "black"):

            return False

        pos, to_move, ep_target = self._reconstruct_position_from_history()

        src_sq = self._sq(current)
        dst_sq = self._sq(target)

        if src_sq not in pos:
            return False
        src_piece, src_color = pos[src_sq]
        if src_color != color:
            return False
        if src_piece != piece_type:
            return False

        if dst_sq in pos and pos[dst_sq][1] == color:
            return False

        if CHECK_PATTERNS and not self._pattern_ok(pos, src_sq, dst_sq, src_piece, color, ep_target):
            return False

        sim_pos = dict(pos)

        is_en_passant = False
        if src_piece == "pawn":
            if self._file(dst_sq) != self._file(src_sq) and dst_sq not in sim_pos:

                if ep_target and dst_sq == ep_target:
                    is_en_passant = True

        if dst_sq in sim_pos:
            del sim_pos[dst_sq]
        if is_en_passant:

            cap_sq = self._en_passant_captured_square(src_sq, dst_sq, color)
            if cap_sq in sim_pos:
                del sim_pos[cap_sq]

        del sim_pos[src_sq]
        sim_pos[dst_sq] = (src_piece, color)

        if self._is_own_king_in_check(sim_pos, color):
            return False

        return True

    def _reconstruct_position_from_history(self) -> Tuple[Dict[str, Tuple[str, str]], str, Optional[str]]:
        """
        Reconstruye la posición desde tablero inicial y la historia SAN (coma-separada).
        Devuelve:
          - pos: dict['e4'] = ('pawn', 'white')  # ocupación
          - to_move: 'white'|'black' (a quién le toca mover después del historial)
          - ep_target: casilla de en passant disponible (o None)
        """
        pos = self._initial_position()
        ep_target: Optional[str] = None
        moves = [m.strip() for m in self.history.split(",") if m.strip()]
        to_move = "white"

        for san in moves:
            pos, to_move, ep_target = self._apply_san(pos, to_move, san, last_ep=ep_target)

        return pos, to_move, ep_target

    def _apply_san(self, pos, to_move, san, last_ep=None):
        """Aplica SAN básica a la posición. Devuelve (pos, next_to_move, ep_target)."""
        ep_target = None
        enemy = "black" if to_move == "white" else "white"
        s = san.strip()


        if s.endswith("+") or s.endswith("#"):
            s = s[:-1]


        if s in ("O-O", "0-0"):
            pos = self._castle(pos, to_move, "king")
            return pos, enemy, None
        if s in ("O-O-O", "0-0-0"):
            pos = self._castle(pos, to_move, "queen")
            return pos, enemy, None


        piece = "pawn"
        if s and s[0] in LETTER_PIECE:
            piece = LETTER_PIECE[s[0]]
            s = s[1:]


        capture = "x" in s
        origin_file_hint = None
        if capture:
            left, right = s.split("x", 1)

            if piece == "pawn" and len(left) == 1 and left in FILES:
                origin_file_hint = left
            s = right


        promotion = None
        if "=" in s:
            s, promo = s.split("=", 1)
            promotion = {"Q":"queen","R":"rook","B":"bishop","N":"knight"}.get(promo.upper(), None)

        # destino
        dst_sq = s.lower()
        if not self._valid_square(dst_sq):

            return pos, enemy, None

        src_sq = self._find_origin_for(pos, to_move, piece, dst_sq, origin_file_hint)

        if src_sq is None:
            return pos, enemy, None


        is_en_passant = False
        if piece == "pawn" and capture and dst_sq not in pos:
            if last_ep and dst_sq == last_ep:
                is_en_passant = True


        if dst_sq in pos:
            del pos[dst_sq]
        if is_en_passant:
            cap_sq = self._en_passant_captured_square(src_sq, dst_sq, to_move)
            if cap_sq in pos:
                del pos[cap_sq]


        del pos[src_sq]
        pos[dst_sq] = (promotion if promotion else piece, to_move)


        if piece == "pawn" and self._file(dst_sq) == self._file(src_sq):
            d = self._rank(dst_sq) - self._rank(src_sq)
            if (to_move == "white" and d == 2) or (to_move == "black" and d == -2):
                mid = self._mid_square(src_sq, dst_sq)
                ep_target = mid

        return pos, enemy, ep_target

    def _is_own_king_in_check(self, pos: Dict[str, Tuple[str, str]], color: str) -> bool:
        """Retorna True si el rey 'color' está atacado por alguna pieza enemiga."""
        king_sq = None
        for sq, (p, c) in pos.items():
            if p == "king" and c == color:
                king_sq = sq
                break
        if not king_sq:
            # Sin rey (posición corrupta); por seguridad, considerar en jaque.
            return True

        enemy = "black" if color == "white" else "white"
        return self._square_attacked_by(pos, king_sq, enemy)

    def _square_attacked_by(self, pos, target_sq, attacker_color) -> bool:
        # Ataques de peones
        for df in (-1, 1):
            sq = self._shift_file_rank(target_sq, df, -1 if attacker_color == "white" else 1)
            if sq and sq in pos and pos[sq] == ("pawn", attacker_color):
                return True

        # Ataques de caballos
        for df, dr in [(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)]:
            sq = self._shift_file_rank(target_sq, df, dr)
            if sq and sq in pos and pos[sq] == ("knight", attacker_color):
                return True

        # Rayos: alfiles/torres/reinas
        # diagonales (B/Q)
        for df, dr in [(1,1),(1,-1),(-1,1),(-1,-1)]:
            if self._ray_hits(pos, target_sq, df, dr, attacker_color, sliding=("bishop","queen")):
                return True
        # ortogonales (R/Q)
        for df, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
            if self._ray_hits(pos, target_sq, df, dr, attacker_color, sliding=("rook","queen")):
                return True

        # Rey enemigo adyacente
        for df in (-1,0,1):
            for dr in (-1,0,1):
                if df == 0 and dr == 0:
                    continue
                sq = self._shift_file_rank(target_sq, df, dr)
                if sq and sq in pos and pos[sq] == ("king", attacker_color):
                    return True

        return False

    def _ray_hits(self, pos, origin_sq, df, dr, attacker_color, sliding=("bishop","queen")) -> bool:
        f = FILES.index(origin_sq[0])
        r = int(origin_sq[1])
        while True:
            f += df
            r += dr
            if not (0 <= f < 8 and 1 <= r <= 8):
                return False
            sq = f"{FILES[f]}{r}"
            if sq in pos:
                piece, color = pos[sq]
                if color == attacker_color and piece in sliding:
                    return True
                return False

    def _find_origin_for(self, pos, color, piece, dst_sq, origin_file_hint=None) -> Optional[str]:
        if piece == "pawn":
            # Captura diagonal (archivo distinto) o avance recto
            candidates: List[str] = []
            dst_file = self._file(dst_sq)
            dst_rank = self._rank(dst_sq)
            direction = 1 if color == "white" else -1

            # Si hay archivo de origen indicado (exd5), forzamos ese archivo
            files_to_consider = [origin_file_hint] if origin_file_hint else list(FILES)

            # Captura: archivo cambia y suele haber pieza enemiga (o en passant)
            for f in files_to_consider:
                if f is None:
                    break
                if abs(FILES.index(f) - FILES.index(dst_file)) == 1 and dst_rank == ( (2 if color=="white" else 7) + direction if False else (dst_rank) ):
                    # Intento diagonal: origen sería una fila atrás en dirección opuesta
                    src_sq = f"{f}{dst_rank - direction}"
                    if src_sq in pos and pos[src_sq] == ("pawn", color):
                        candidates.append(src_sq)

            # Si no hay pista de archivo o no encontramos por captura, probar avance recto:
            if not candidates and origin_file_hint is None:
                # 1 paso
                src1 = f"{dst_file}{dst_rank - direction}"
                if src1 in pos and pos[src1] == ("pawn", color):
                    # verificar que no haya pieza en destino si consideramos avance recto
                    if dst_sq not in pos:
                        candidates.append(src1)
                # 2 pasos (solo si origen es fila inicial y la intermedia está libre)
                start_rank = 2 if color == "white" else 7
                if dst_rank == start_rank + 2*direction:
                    inter_sq = f"{dst_file}{start_rank + direction}"
                    src2 = f"{dst_file}{start_rank}"
                    if (src2 in pos and pos[src2] == ("pawn", color)
                        and inter_sq not in pos and dst_sq not in pos):
                        candidates.append(src2)

            return candidates[0] if candidates else None

        # Piezas no deslizantes (rey/caballo) y deslizantes (alfil/torre/reina)
        origins = []
        for sq, (p, c) in pos.items():
            if p == piece and c == color:
                if not CHECK_PATTERNS:
                    # Sin chequeo de patrón, alcanzan candidatos (la legalidad total la decide el jaque propio)
                    origins.append(sq)
                else:
                    if self._pattern_ok(pos, sq, dst_sq, piece, color, last_ep=None):
                        origins.append(sq)

        # Si hay pista de archivo (rara vez para piezas no peón en este parser mínimo)
        if origin_file_hint:
            origins = [o for o in origins if o[0] == origin_file_hint]

        # Elegimos el primero (SAN real requiere desambiguación; esto es mínimo)
        return origins[0] if origins else None

    def _castle(self, pos, color, side: str):
        back = "1" if color == "white" else "8"
        king_from = f"e{back}"
        if side == "king":
            king_to, rook_from, rook_to = f"g{back}", f"h{back}", f"f{back}"
        else:
            king_to, rook_from, rook_to = f"c{back}", f"a{back}", f"d{back}"

        if king_from in pos and pos.get(rook_from) == ("rook", color):
            # limpiar destino si hubiera algo raro
            if king_to in pos:
                del pos[king_to]
            if rook_to in pos:
                del pos[rook_to]
            # mover
            del pos[king_from]
            del pos[rook_from]
            pos[king_to] = ("king", color)
            pos[rook_to] = ("rook", color)
        return pos


    def _pattern_ok(self, pos, src_sq, dst_sq, piece, color, ep_target) -> bool:
        if piece == "king":
            return self._manhattan(src_sq, dst_sq) <= 2 and max(abs(self._df(src_sq, dst_sq)), abs(self._dr(src_sq, dst_sq))) == 1
        if piece == "knight":
            return (abs(self._df(src_sq, dst_sq)), abs(self._dr(src_sq, dst_sq))) in {(1,2),(2,1)}
        if piece == "bishop":
            return self._diagonal_clear(pos, src_sq, dst_sq)
        if piece == "rook":
            return self._straight_clear(pos, src_sq, dst_sq)
        if piece == "queen":
            return self._diagonal_clear(pos, src_sq, dst_sq) or self._straight_clear(pos, src_sq, dst_sq)
        if piece == "pawn":
            df = self._df(src_sq, dst_sq)
            dr = self._dr(src_sq, dst_sq)
            direction = 1 if color == "white" else -1
            # avance recto
            if df == 0 and dr == direction and dst_sq not in pos:
                return True
            # doble paso inicial
            start_rank = 2 if color == "white" else 7
            if df == 0 and dr == 2*direction and self._rank(src_sq) == start_rank:
                inter_sq = f"{self._file(src_sq)}{start_rank + direction}"
                return inter_sq not in pos and dst_sq not in pos
            # captura (incluye en passant si destino está vacío pero ep_target coincide)
            if abs(df) == 1 and dr == direction:
                return (dst_sq in pos and pos[dst_sq][1] != color) or (ep_target and dst_sq == ep_target)
            return False
        return True


    def _initial_position(self) -> Dict[str, Tuple[str, str]]:
        pos: Dict[str, Tuple[str, str]] = {}
        # peones
        for f in FILES:
            pos[f"{f}2"] = ("pawn", "white")
            pos[f"{f}7"] = ("pawn", "black")
        # mayores
        for color, rank in (("white", "1"), ("black", "8")):
            pos[f"a{rank}"] = ("rook", color)
            pos[f"h{rank}"] = ("rook", color)
            pos[f"b{rank}"] = ("knight", color)
            pos[f"g{rank}"] = ("knight", color)
            pos[f"c{rank}"] = ("bishop", color)
            pos[f"f{rank}"] = ("bishop", color)
            pos[f"d{rank}"] = ("queen", color)
            pos[f"e{rank}"] = ("king", color)
        return pos


    def _sq(self, c: Coordinate) -> str:
        return f"{c.col}{c.row}".lower()

    def _file(self, sq: str) -> str:
        return sq[0]

    def _rank(self, sq: str) -> int:
        return int(sq[1])

    def _valid_square(self, sq: str) -> bool:
        return len(sq) == 2 and sq[0] in FILES and sq[1] in RANKS

    def _df(self, a: str, b: str) -> int:
        return FILES.index(b[0]) - FILES.index(a[0])

    def _dr(self, a: str, b: str) -> int:
        return int(b[1]) - int(a[1])

    def _manhattan(self, a: str, b: str) -> int:
        return abs(self._df(a, b)) + abs(self._dr(a, b))

    def _diagonal_clear(self, pos, src, dst) -> bool:
        df = self._df(src, dst)
        dr = self._dr(src, dst)
        if abs(df) != abs(dr) or df == 0:
            return False
        step_f = 1 if df > 0 else -1
        step_r = 1 if dr > 0 else -1
        f = FILES.index(src[0]) + step_f
        r = int(src[1]) + step_r
        while f != FILES.index(dst[0]) and r != int(dst[1]):
            sq = f"{FILES[f]}{r}"
            if sq in pos:
                return False
            f += step_f
            r += step_r
        return True

    def _straight_clear(self, pos, src, dst) -> bool:
        df = self._df(src, dst)
        dr = self._dr(src, dst)
        if df != 0 and dr != 0:
            return False
        if df == 0:
            step_r = 1 if dr > 0 else -1
            r = int(src[1]) + step_r
            while r != int(dst[1]):
                sq = f"{src[0]}{r}"
                if sq in pos:
                    return False
                r += step_r
            return True
        else:
            step_f = 1 if df > 0 else -1
            f = FILES.index(src[0]) + step_f
            while f != FILES.index(dst[0]):
                sq = f"{FILES[f]}{src[1]}"
                if sq in pos:
                    return False
                f += step_f
            return True

    def _shift_file_rank(self, sq: str, df: int, dr: int) -> Optional[str]:
        f = FILES.index(sq[0]) + df
        r = int(sq[1]) + dr
        if 0 <= f < 8 and 1 <= r <= 8:
            return f"{FILES[f]}{r}"
        return None

    def _mid_square(self, src_sq: str, dst_sq: str) -> Optional[str]:
        if self._file(src_sq) != self._file(dst_sq):
            return None
        mid = (self._rank(src_sq) + self._rank(dst_sq)) // 2
        return f"{self._file(src_sq)}{mid}"

    def _en_passant_captured_square(self, src_sq: str, dst_sq: str, mover_color: str) -> str:
        # Peón que captura al paso: la pieza capturada está en la fila "atrás" del destino
        dr = -1 if mover_color == "white" else 1
        return f"{self._file(dst_sq)}{self._rank(dst_sq) + dr}"