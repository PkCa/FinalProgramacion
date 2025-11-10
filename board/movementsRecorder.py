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