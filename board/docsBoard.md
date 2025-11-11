# Documentación técnica — Board, MovementsRecorder y Coordinate

---

## 1) Coordinate (Coordenate)

### Propósito

Representa una casilla del tablero de ajedrez con **columna** (letra `a..h`) y **fila** (número `1..8`). Actúa como tipo de dato simple y seguro para comunicar posiciones entre piezas, el tablero y los registradores de movimientos.

### Atributos

* `col: str` — letra entre `a` y `h`.
* `row: int` — entero entre `1` y `8`.

---

## 2) Board

### Propósito

Mantiene el **estado material** del juego en un arreglo 2D 8×8 con instancias reales de piezas, y ofrece utilidades para consulta y simulación necesarias por componentes de reglas (p. ej., `MovementsRecorder`).

### Estado interno

* `board: List[List[Optional[Piece]]]` — Matriz 8×8. Índices internos:

  * Fila (índice) = `row - 1` (fila 1→índice 0, fila 8→índice 7)
  * Columna (índice) = `ord(col) - ord('a')` (a→0, h→7)
* **Inicialización:** coloca todas las piezas en su posición inicial estándar (primero instancia, luego ubica).

* **Lectura / escritura**

  * `get_piece_at(coord: Coordinate) -> Optional[Piece]` — Devuelve la pieza (o `None`).
  * `is_empty(coord: Coordinate) -> bool` — `True` si la casilla no está ocupada.
  * `piece_color_at(coord: Coordinate) -> Optional[str]` — `"white"|"black"|None`.
  * `to_coordinate(square: str) -> Coordinate` — Convierte `"e4"` a `Coordinate('e', 4)`.

* **Geometría / trayectorias**

  * `squares_between(a: Coordinate, b: Coordinate) -> List[Coordinate]` — Lista de casillas estrictamente **entre** `a` y `b` en línea recta o diagonal.
  * `king_position(color: str) -> Coordinate` — Ubicación actual del rey de ese color.

* **Ataque y legalidad básica**

  * `is_square_attacked(coord: Coordinate, by_color: str) -> bool` — `True` si la casilla está atacada por el color dado (peones, caballos, deslizantes —alfiles/torres/reinas— y rey adyacente).
  * `has_legal_moves(color: str) -> bool` — *Versión mínima*: explora movimientos y simula si el rey queda a salvo (No implementado).

* **Registradores**

  * `find_sources(piece_name: str, color: str, to_coord: Coordinate, san_hint: dict) -> List[Coordinate]` — Candidatos de origen que **podrían** llegar a destino `to_coord` por patrón y camino libre.

* **Aplicación de movimientos**

  * `apply_move(move: Move) -> None` — Aplica un movimiento ya decidido (normal, captura, en passant, enroque, promoción). Se usa desde `MovementsRecorder` tras validar/determinar flags.

* **Depuración**

  * `to_ascii() -> str` — Dibujo de texto del tablero (para tests rápidos en consola).

### Invariantes y consideraciones

* `Board` **no** decide la legalidad total: su rol es de **estado + utilidades**. Reglas como jaque, enroque permisible, en passant disponible, etc., se coordinan con `MovementsRecorder`.
* `apply_move` **mueve** piezas reales en el estado del tablero: úsese solamente desde una capa que controle la validez del movimiento.

---

## 3) MovementsRecorder

### Propósito

Actúa como **intermediario** y **bitácora** de todos los movimientos. Registra historial con notación algebraica estándar (SAN), aplica los movimientos sobre `Board`, y determina estados clave:

* Jaque (`+`) y **jaque mate** (`#`) (No implementado el jaque mate aun).
* Elegibilidad de **captura al paso** (casilla objetivo y qué peón la habilitó) (No implementado).
* Posibilidad de **enroque** corto/largo (según posición actual y reglas básicas) (No implementado).

### Estado interno

* `history: List[Move]` — lista de movimientos (estructura `Move` con `piece`, `color`, `src`, `dst`, flags como `is_check`, `is_mate`, `is_en_passant_capture`, `castle_side`, `promotion`, y `san`).
* `_en_passant: Optional[dict]` — ventana de en passant activa, p. ej. `{ 'target': Coordinate, 'by_pawn_at': Coordinate, 'color': 'white'|'black' }`.
* `board: BoardLike` — referencia al tablero sobre el que se aplican los movimientos.

* `add(piece: str, color: str, src: Coordinate, dst: Coordinate, capture: Optional[bool] = None, promotion: Optional[str] = None) -> Move`

  * Construye el movimiento, infiere si es enroque (rey 2 columnas), distingue captura normal o **al paso**, aplica el movimiento en `Board`, actualiza en passant, calcula `+/#` y genera **SAN**.

* `add_san(san: str, color: str) -> Move`

  * Recibe SAN (parser **mínimo**: `O-O`, `O-O-O`, `e4`, `Nf3`, `Qxe5`, `exd5`, `e8=Q`, `exd8=Q+`) y delega a `Board.find_sources(...)` para ubicar el origen.
  * Resuelve ambigüedad simple con `origin_file` cuando está presente; si hay múltiples candidatos sin pista, lanza error.

* `last_move() -> Optional[Move]` — Último movimiento registrado.

* `en_passant_info() -> Optional[dict]` — Si hay captura al paso disponible **en la próxima media-jugada** del rival.

* `can_castle_kingside(color: str) -> bool` — Reglas básicas de enroque corto.

* `can_castle_queenside(color: str) -> bool` — Reglas básicas de enroque largo.

* `summary() -> dict` — Resumen útil para depuración (SAN, última jugada, en passant, enroques posibles por color).

### Flujo de un `add(...)`

1. **Inferencia de flags**: enroque (rey 2 columnas), captura normal, posible **en passant** si peón llega diagonal a casilla vacía que coincide con la ventana `_en_passant`.
2. **Aplicación en tablero**: `board.apply_move(move)` debe:

   * mover la pieza,
   * eliminar capturas (incluida al paso),
   * mover torre en enroque,
   * promocionar si corresponde.
3. **Actualizar en passant**: si un peón avanzó dos, se habilita la casilla intermedia como objetivo para la **próxima** jugada enemiga.
4. **Jaque y mate**: se consulta `board.is_square_attacked(king_pos, by_color=...)` y `board.has_legal_moves(...)`.
5. **Construcción de SAN**: `O-O` / `O-O-O`, pieza (`KQRBN` o vacío para peón) + captura `x` + destino `e4`, sufijos `=Q`, `+`, `#`.

### Limitaciones conocidas

* El **parser SAN** es intencionalmente mínimo y puede requerir desambiguación adicional en posiciones complejas.
* `has_legal_moves` es una aproximación útil para mate, pero no sustituye a un motor completo (EP/promoción como recurso defensivo pueden requerir ampliar).

---

## Integración entre módulos

* **Coordinate → Board**: `Board` consume `Coordinate` para acceder y modificar el estado 2D. Todo acceso a casillas públicas de `Board` se hace con coordenadas válidas.
* **Board ↔ MovementsRecorder**:

  * `MovementsRecorder` decide **qué** mover (y cómo anotar) y llama a `Board.apply_move` para **materializar** el cambio.
  * `MovementsRecorder` consulta en `Board` utilidades de ataque, posición de reyes, casillas intermedias y resolución de orígenes para SAN.

---

En un futuro se pueden implementar guardados de partida con el atributo history de esta clase, guardandolo en un archivo.
