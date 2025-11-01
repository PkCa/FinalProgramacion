class Coordenate:
    max_row = 7 # En el array
    min_row = 0 # En el array
    max_col = 'h' # Para la notacion
    min_col = 'a' # Para la notacion

    def __init__(self,row:int,col:str):
        self.row = row
        self.col = col

    def move_row(self,vector:int):
        result = self.row + vector

        if result > self.max_row:
            self.row = self.max_row
        elif result < self.min_row:
            self.row = self.min_row
        else:
            self.row = result


    def move_column(self,vector:int):

        max = ord(self.max_col)
        min = ord(self.min_col)
        current = ord(self.col)

        result = current + vector

        if result > max:
            self.col = chr(max)
        elif result < min:
            self.col = chr(min)
        else:
            self.col = chr(result)
