from piece import Piece

class Bishop(Piece):
    def __init__(self, color: str, col: str, row: int):
        super().__init__("bishop", color, col, row)

    def moveDiagonal(self, direction_row: int, direction_col: int):
        super().move(vector_row=direction_row, vector_col=direction_col)
