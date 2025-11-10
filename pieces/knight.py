from piece import Piece

class Knight(Piece):
    def __init__(self, color: str, col: str, row: int):
        super().__init__("knight", color, col, row)
        self.pinned = False

    def moveL(self, vector_row: int, vector_col: int):
        if self.pinned:
            return
        if (abs(vector_row) == 2 and abs(vector_col) == 1) or (abs(vector_row) == 1 and abs(vector_col) == 2):
            super().move(vector_row=vector_row, vector_col=vector_col)
