import random
from logic import SudokuLogic
from solver import DancingLinksSolver, BacktrackingSolver

class SudokuGenerator:
    #az osztály feladata egy teljesen kitöltött Sudoku tábla generálása,
    #majd a megadott nehézségi szintnek megfelelően egyedi megoldású 
    #feladvánnyá alakítása a hibrid (Backtrack/DLX) megoldómotorok segítségével.
    def __init__(self):
        #példányosítja a SudokuLogic osztályt, amely a Sudoku tábla alapvető 
        #logikáját és az érvényesség-ellenőrzést (is_valid) kezeli.
        self.game = SudokuLogic()

    def _fill_board(self) -> bool:
        #a _fill_board metódus rekurzívan próbálja kitölteni a Sudoku táblát a 
        #backtracking algoritmus segítségével. egy üres táblából kiindulva 
        #generál egy teljesen és szabályosan kitöltött, véletlenszerű játéktáblát.
        empty_cell = BacktrackingSolver.find_empty(self.game.board)
        #a find_empty példányosítása nem szükséges,
        #mivel az statikus metódus (@staticmethod), így közvetlenül az osztályból hívható.
        if not empty_cell:
            return True
        
        row, col = empty_cell
        
        numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        random.shuffle(numbers)

        for n in numbers:
            if self.game.is_valid(row, col, n):
                self.game.board[row][col] = n

                if self._fill_board():
                    return True
                
                self.game.board[row][col] = 0

        return False

    def _count_solutions(self) -> int:
        #a _count_solutions metódus a hagyományos rekurzív visszalépéses (backtracking) 
        #eljárással számolja meg, hogy hány lehetséges megoldása van a jelenlegi táblának. 
        #a hibrid modellben ez végzi a könnyű és közepes szintek validálását.
        empty_cell = BacktrackingSolver.find_empty(self.game.board)
        if not empty_cell:
            return 1

        row, col = empty_cell
        solutions = 0
        
        for n in range(1, 10):
            if self.game.is_valid(row, col, n):
                self.game.board[row][col] = n
                solutions += self._count_solutions()
                
                self.game.board[row][col] = 0
                
                if solutions > 1:
                    return solutions 

        return solutions

    def generate(self, difficulty: str) -> SudokuLogic:
        #a generate metódus először létrehoz egy teljesen kitöltött táblát, 
        #majd a teljesítmény optimalizálása érdekében hibrid megközelítést alkalmaz: 
        #a 'hard' szintű táblák validálását a villámgyors DLX algoritmussal végzi, 
        #míg az egyszerűbb pályáknál a klasszikus backtrackinget hívja segítségül.
        diff_map = {
            "easy": random.randint(30, 40),
            "medium": random.randint(41, 50),
            "hard": random.randint(51, 60)
        }
        
        target_holes = diff_map.get(difficulty)

        self.game = SudokuLogic()
        self._fill_board()

        coords = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(coords)

        holes_made = 0
        for row, col in coords:
            if holes_made >= target_holes:
                break

            original_val = self.game.board[row][col]
            self.game.board[row][col] = 0

            #hibrid megoldóválasztás a kért nehézségi szint alapján
            if difficulty == "hard":
                dlx_solver = DancingLinksSolver(self.game.board)
                solution_count = dlx_solver.get_solution_count()
            else:
                solution_count = self._count_solutions()

            #ha a törlés után is egyedi a megoldás, véglegesítjük a lyukat
            if solution_count == 1:
                holes_made += 1
            else:
                self.game.board[row][col] = original_val

        return self.game