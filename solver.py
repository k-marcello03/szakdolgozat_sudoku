class BacktrackingSolver:
    #az osztály feladata egy meglévő Sudoku tábla megoldása
    #a megoldás során a backtracking algoritmust használja, ami rekurzívan próbálja kitölteni a táblát
    #visszalép, ha egy adott szám nem vezet megoldáshoz
    
    def __init__(self, board):
    #a konstruktor inicializálja a BacktrackingSolver objektumot a megadott táblával
    #a tábla egy kétdimenziós lista, ahol a 0 érték az üres cellákat jelöli
        self.board = [row[:] for row in board]

    @staticmethod
    def find_empty(board):
    #keres egy üres cellát (0 értékű) a táblán, és visszaadja annak koordinátáit (sor, oszlop)
        for r in range(9):
            for c in range(9):
                if board[r][c] == 0:
                    return r, c
        return None

    def is_valid(self, num, r, c):
    #ellenőrzi, hogy a megadott szám (num) elhelyezhető-e a táblán a (r, c) koordinátákon
        for i in range(9):
            if self.board[r][i] == num and c != i:
                return False

        for i in range(9):
            if self.board[i][c] == num and r != i:
                return False

        box_x = c // 3
        box_y = r // 3
        for i in range(box_y * 3, box_y * 3 + 3):
            for j in range(box_x * 3, box_x * 3 + 3):
                if self.board[i][j] == num and (i, j) != (r, c):
                    return False

        return True

    def solve(self):
    #a solve metódus a backtracking algoritmust használva próbálja megoldani a Sudoku táblát
        find = self.find_empty(self.board)
        
        if not find:
            return True
        else:
            row, col = find
 
        for i in range(1, 10):
            if self.is_valid(i, row, col):
                self.board[row][col] = i

                if self.solve():
                    return True

                self.board[row][col] = 0

        return False

class DancingLinksSolver:
    
    #az osztály a Donald Knuth-féle Algorithm X (Exact Cover) algoritmust implementálja
    #a Python beépített szótárait (hash tábláit) használva a Dancing Links technika szimulálására
    
    #osztályszintű gyorsítótár
    #ezek az adatszerkezetek csak egyszer jönnek létre a memóriában, amikor a program elindul, hogy csökkentse a futási időt.
    
    #az Exact Cover mátrix oszlopai, amelyek a Sudoku 4 alapvető szabályát (kényszerét) reprezentálják.
    #1. Minden cellában kell lennie egy számnak ("cell")
    #2. Minden sorban szerepelnie kell minden számnak 1-9-ig ("row")
    #3. Minden oszlopban szerepelnie kell minden számnak 1-9-ig ("col")
    #4. Minden 3x3-as blokkban szerepelnie kell minden számnak 1-9-ig ("box")
    X_EXACT_COVER = ({("cell", r, c) for r in range(9) for c in range(9)} |
                     {("row", r, n) for r in range(9) for n in range(1, 10)} |
                     {("col", c, n) for c in range(9) for n in range(1, 10)} |
                     {("box", r // 3, c // 3, n) for r in range(9) for c in range(9) for n in range(1, 10)})
    
    Y_EXACT_COVER = {}
    for r in range(9):
        for c in range(9):
            for n in range(1, 10):
                Y_EXACT_COVER[(r, c, n)] = [
                    ("cell", r, c), ("row", r, n),
                    ("col", c, n), ("box", r // 3, c // 3, n)
                ]

    #osztályszintű, előre feltöltött univerzális mátrix!
    #ez csak egyszer fut le, amikor a Python betölti a fájlt.
    X_UNIVERSAL_MATRIX = {j: set() for j in X_EXACT_COVER}
    for step, constraints in Y_EXACT_COVER.items():
        for j in constraints:
            X_UNIVERSAL_MATRIX[j].add(step)

    def __init__(self, board):
        self.board = [row[:] for row in board]

    def solve(self):
        #1. teljes mátrix villámgyors "másolása" (minden oszlopban az elemek új halmazt kapnak)
        X_dict = {j: set(self.X_UNIVERSAL_MATRIX[j]) for j in self.X_UNIVERSAL_MATRIX}
        
        solution = []
        
        #2. a táblában lévő fix számok beillesztése a megoldásba, és a DLX _select meghívása
        for r in range(9):
            for c in range(9):
                val = self.board[r][c]
                if val != 0:
                    step = (r, c, val)
                    solution.append(step)
                    #a _select eltávolítja a mátrixból az összes oszlopot és sort,
                    #ami ütközik ezzel a fix beinduló számmal (O(1) törlések a memóriából)
                    self._select(X_dict, self.Y_EXACT_COVER, step)
                    
        #3. keresés indítása a már szűkített mátrixon
        for s in self._search(X_dict, self.Y_EXACT_COVER, solution):
            for (r, c, n) in s:
                self.board[r][c] = n
            return True
        return False

    def get_solution_count(self):
        #ugyanaz az elv, mint a solve-nál
        X_dict = {j: set(self.X_UNIVERSAL_MATRIX[j]) for j in self.X_UNIVERSAL_MATRIX}
        
        solution = []
        
        for r in range(9):
            for c in range(9):
                val = self.board[r][c]
                if val != 0:
                    step = (r, c, val)
                    solution.append(step)
                    self._select(X_dict, self.Y_EXACT_COVER, step)
                    
        count = 0
        for _ in self._search(X_dict, self.Y_EXACT_COVER, solution):
            count += 1
            if count > 1:
                break
                
        return count

    def _search(self, X, Y, solution):
        #ha az X szótár üres, minden kényszert kielégítettünk, megvan a megoldás
        if not X:
            yield list(solution)
        else:
            #kiválasztjuk azt a kényszert (oszlopot), amelyhez a legkevesebb lehetséges lépés tartozik.
            #ez drasztikusan csökkenti a keresési fa méretét (gyorsítja az algoritmust).
            c = min(X, key=lambda k: len(X[k]))
            
            #végigpróbáljuk a kiválasztott kényszert kielégítő összes lehetséges lépést (sort)
            for r in list(X[c]):
                solution.append(r)
                # Eltávolítjuk a mátrixból azokat a sorokat és oszlopokat, amelyek ütköznének a választott lépéssel
                cols = self._select(X, Y, r)
                
                #rekurzív hívás a szűkített mátrixszal
                yield from self._search(X, Y, solution)
                
                #ha zsákutcába jutottunk, visszalépünk (backtrack): visszaállítjuk az eltávolított elemeket
                self._deselect(X, Y, r, cols)
                solution.pop()

    def _select(self, X, Y, r):
        #a kiválasztott lépés (r) által lefedett oszlopok eltávolítása a mátrixból
        cols = []
        for j in Y[r]:
            for i in X[j]:
                for k in Y[i]:
                    if k != j:
                        # Eltávolítjuk a hivatkozásokat az ütköző lépésekről
                        X[k].remove(i)
            #kimentjük az eltávolított oszlopot, hogy később visszaállítható legyen
            cols.append(X.pop(j))
        return cols

    def _deselect(self, X, Y, r, cols):
        #visszaállítja a _select metódus által eltávolított elemeket a memóriába (backtracking)
        for j in reversed(Y[r]):
            X[j] = cols.pop()
            for i in X[j]:
                for k in Y[i]:
                    if k != j:
                        X[k].add(i)