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
