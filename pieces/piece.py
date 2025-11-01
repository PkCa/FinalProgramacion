from board.coordenates import Coordenate   # importar arriba

class Piece:
    def __init__(self, col:str, row:int):
        self.position = Coordenate(col, row) 

    
    def move_vertical(self,vector_col:int, vector_row:int):
        self.position.move_row(vector_row)
        self.position.move_col(vector_col)