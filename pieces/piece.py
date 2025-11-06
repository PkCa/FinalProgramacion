from board.coordenates import Coordenate   # importar arriba

class Piece:
    selected = False

    def __init__(self,type:str,color:str, col:str, row:int, movements:dict):
        self.position = Coordenate(col, row) 
        self.color = color
        self.type = type

    
    def move(self, vector_row:int,vector_col:int):
        self.position.move_row(vector_row)
        self.position.move_col(vector_col)