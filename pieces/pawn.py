from piece import Piece

class Pawn(Piece):
    def __init__(self, color: str, col: str, row: int):
        super().__init__("pawn", color, col, row)

    def moveOne(self):
        direction = 1 if self.color == "white" else -1
        super().move(vector_row=direction, vector_col=0)

    def moveTwo(self):
        direction = 1 if self.color == "white" else -1
        super().move(vector_row=2 * direction, vector_col=0)

    def capture(self, direction_col: int):
        """
        direction_col: -1 para izquierda, +1 para derecha
        """
        
        direction_row = 1 if self.color == "white" else -1
        super().move(vector_row=direction_row, vector_col=direction_col)

    def enPassant(self, direction_col: int):
        """
        direction_col: -1 para izquierda, +1 para derecha
        """
        direction_row = 1 if self.color == "white" else -1
        super().move(vector_row=direction_row, vector_col=direction_col)
