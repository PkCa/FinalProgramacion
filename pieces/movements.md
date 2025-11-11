## Sistema de movimiento de piezas

La clase `Coordenate` define posiciones mediante **columna (letra)** y **fila (número)**.  
La clase `Piece` proporciona el método base `move`, que recibe dos parámetros:

- `vector_row`: movimiento vertical (filas)  
- `vector_col`: movimiento horizontal (columnas)

Los movimientos se expresan en **vectores**, y la función `move()` actualiza la posición de la pieza utilizando esos vectores.

---

### Soporte especial

El gestor de movimientos de la partida soporta reglas especiales como:
- Enroque del rey (Aun no esta implementado en el juego final)
- Captura al paso del peón (Aun no esta implementado en el juego final)

---

## PAWN (Peón)

El peón se mueve siempre **una casilla hacia adelante**, dependiendo de su color:
- Blancos: fila +1  
- Negros: fila -1  

Puede moverse **dos casillas** si está en su posición inicial.  
Puede **capturar en diagonal** (una casilla hacia adelante y una hacia la izquierda o derecha).  
Además, tiene soporte para **captura al paso** (*en passant*) (No implementado). 

Funciones:

def moveOne()      # Movimiento normal

def moveTwo()      # Movimiento doble inicial

def capture(direction_col)  # Movimiento diagonal para capturar

def enPassant(direction_col)  # Movimiento especial de captura al paso

Atributos importantes:

- pinned → Si es True, el peón no puede moverse.

---

## KNIGHT (Caballo)

El caballo se mueve en forma de **L**:  
- Dos casillas en una dirección y una en perpendicular  
Puede saltar sobre otras piezas.

Funciones:

def moveL(vector_row, vector_col)

Atributos:

- pinned → Si está clavado, no puede moverse.

---

## BISHOP (Alfil)

El alfil se mueve en **diagonal** todas las casillas posibles.

Funciones:

def moveDiagonal(direction_row, direction_col)

Atributos:

- pinned → Impide movimiento si es True.

---

## ROOK (Torre)

La torre se mueve en línea **recta** horizontal o vertical.

Funciones:

def moveStraight(vector_row, vector_col)

Atributos:

- pinned → No puede moverse si está clavada.

---

## QUEEN (Reina)

La reina combina los movimientos de la **torre** y el **alfil**,  
puediendo moverse tanto en líneas rectas como diagonales.

Funciones:

def moveAny(vector_row, vector_col)

Atributos:

- pinned → Restringe el movimiento si es True.

---

## KING (Rey)

El rey se mueve **una casilla** en cualquier dirección.  
Además, puede realizar el movimiento especial de **enroque** (No implementado),  
donde se mueve dos columnas hacia un lado junto a la torre correspondiente.

Funciones:

def moveOne(vector_row, vector_col)

def castle(side)   # 'king' o 'queen'

Atributos:

- has_moved → Controla si ya se movió (para enroque)
- check → Marca si el rey está en jaque (True o False)
