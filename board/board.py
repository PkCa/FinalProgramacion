from typing import Optional, List, Tuple, Dict, Any

from coordinate import Coordinate
from pawn import Pawn
from knight import Knight
from bishop import Bishop
from rook import Rook
from queen import Queen
from king import King

FILES = "abcdefgh"

# -----------------------------------------------------------------------------
# Board
# -----------------------------------------------------------------------------

class Board:
    def __init__(self):
        # Crea el array 2D vacío
        self.board: List[List[Optional[object]]] = self._empty_board()
        # Coloca las piezas en su posición inicial (instanciando primero)
        self._place_initial_position()


 