from piece import Piece

class Queen(Piece):
    def __init__(self, color: str, col: str, row: int):
        super().__init__("queen", color, col, row)
        self.pinned = False

    def moveAny(self, vector_row: int, vector_col: int):
        if self.pinned:
            return
        if vector_row == 0 or vector_col == 0 or abs(vector_row) == abs(vector_col):
            super().move(vector_row=vector_row, vector_col=vector_col)
