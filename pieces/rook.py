from piece import Piece

class Rook(Piece):
    def __init__(self, color: str, col: str, row: int):
        super().__init__("rook", color, col, row)
        self.pinned = False

    def moveStraight(self, vector_row: int, vector_col: int):
        if self.pinned:
            return
        if vector_row == 0 or vector_col == 0:
            super().move(vector_row=vector_row, vector_col=vector_col)
