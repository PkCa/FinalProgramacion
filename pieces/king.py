from piece import Piece

class King(Piece):
    def __init__(self, color: str, col: str, row: int):
        super().__init__("king", color, col, row)
        self.has_moved = False

    def moveOne(self, vector_row: int, vector_col: int):
        if abs(vector_row) <= 1 and abs(vector_col) <= 1:
            super().move(vector_row=vector_row, vector_col=vector_col)
            self.has_moved = True