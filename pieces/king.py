from piece import Piece

class King(Piece):
    def __init__(self, color: str, col: str, row: int):
        super().__init__("king", color, col, row)
        self.has_moved = False
        self.check = False      

    def moveOne(self, vector_row: int, vector_col: int):
        if abs(vector_row) <= 1 and abs(vector_col) <= 1:
            super().move(vector_row=vector_row, vector_col=vector_col)
            self.has_moved = True

    def castle(self, side: str):
        """
        side: 'king' (lado corto) o 'queen' (lado largo)
        """
        if self.has_moved or self.check:
            return 

        if side == "king":
            vector_col = 2 
        elif side == "queen":
            vector_col = -2
        else:
            raise ValueError("El lado del enroque debe ser 'king' o 'queen'.")

        super().move(vector_row=0, vector_col=vector_col)
        self.has_moved = True
