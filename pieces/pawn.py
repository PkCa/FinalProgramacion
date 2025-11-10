from piece import Piece

class Pawn(Piece):
    def __init__(self,color:str, col:str,row:int):

        super().__init__("pawn", color, col, row)

    #Movimiento principal
    def moveOne(self):
    
        direction = 1 if self.color == "white" else -1
        super().move(vector_row=direction, vector_col=0)

