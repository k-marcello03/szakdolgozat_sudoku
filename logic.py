class SudokuLogic:

    #üres (nullákkal teli) tábla (kétdimenziós lista) generálása
    def __init__(self):
        self.board = [[0 for _ in range(9)] for _ in range(9)]

    #ellenőrzések
    def is_valid(self, row, col, num):

        #ellenőrzi, hogy a megadott szám benne van-e az [1;9] tartományban
        if num < 1 or num > 9:
            return False

        #sorok ellenőzése
        for i in range(9):
            if self.board[row][i] == num:
                return False
            
        #oszlopok ellenőzése
        for i in range(9):
            if self.board[i][col] == num:
                return False

        #résztáblák ellenőzése
        start_row = (row // 3) * 3
        start_col = (col // 3) * 3

        for i in range(3):
            for j in range(3):
                if self.board[start_row + i][start_col + j] == num:
                    return False
        
        return True
    
    #szám elhelyzése
    def place_number(self, row, col, num) -> bool:
        if self.is_valid(row, col, num):
            self.board[row][col] = num
            return True
        return False
    
    #cellatörlés (0-ra állítás)
    def clear_cell(self, row, col):
        self.board[row][col] = 0

    #konzolra nyomtatás (debug célokra)
    def console_board(self):
        for i in range(9):
            if i % 3 == 0 and i != 0:
                print("- - - - - - - - - - - - - ")
            for j in range(9):
                if j % 3 == 0 and j != 0:
                    print(" | ", end="")
                if j == 8:
                    print(self.board[i][j])
                else:
                    print(str(self.board[i][j]) + " ", end="")