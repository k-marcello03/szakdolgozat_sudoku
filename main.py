import sys
import random
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                               QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, 
                               QLineEdit, QMessageBox, QLabel, QStackedWidget, QCheckBox, QDialog)   
from PySide6.QtCore import Qt, Signal, QRectF, QTimer
from PySide6.QtGui import QFont, QAction, QPainter, QColor, QShortcut, QKeySequence

from generator import SudokuGenerator
from solver import BacktrackingSolver, DancingLinksSolver

class SudokuCell(QLineEdit):
    #az osztály egy egyedi Sudoku cellát valósít meg QLineEdit alapokon
    #kezeli a cellára kattintást, a billentyűzetes navigációt, a jegyzetelést és az egyedi kirajzolást
    cell_clicked = Signal(int, int, bool)
    move_requested = Signal(int, int)
    input_requested = Signal(str)

    #konstruktor: beállítja a cella koordinátáit, méreteit, alapértelmezett állapotait és stílusát
    def __init__(self, row, col):
        super().__init__()
        #a cella rácsbeli koordinátái (0-8 közötti indexek)
        self.row = row
        self.col = col
        #jegyzetelési mód állapota (ceruza) és sötét mód állapota
        self.is_note = False
        self.is_dark = False
        #tippelt cella állapota
        self.is_hinted = False
        
        #legfeljebb 9 karakter férhet el egy cellában jegyzet esetén
        self.setMaxLength(9)
        #a szöveg vízszintesen és függőlegesen is középre igazítása
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        #erős fókuszpolicy beállítása a billentyűzet és egér események teljes fogadásához
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        #alapértelmezett keretstílus inicializálása vékony szürke szegéllyel
        self.border_style = "border: 1px solid #ccc; "
        #a 3x3-as blokkok határainak és a külső széleknek vastagabb fekete szegély beállítása
        if row % 3 == 0: self.border_style += "border-top: 3px solid black; "
        if col % 3 == 0: self.border_style += "border-left: 3px solid black; "
        if row == 8: self.border_style += "border-bottom: 3px solid black; "
        if col == 8: self.border_style += "border-right: 3px solid black; "
        
        #alapértelmezett fehér háttér és fekete betűszín
        self.bg_color = "white"
        self.text_color = "black"
        self.apply_style()

    #a stílusok és keretek dinamikus beállítása a háttér-, betűszín és a sötét mód állapota alapján
    def apply_style(self, bg_color=None, text_color=None, is_dark=None):
        #értékek frissítése ha új paramétereket kap a metódus
        if bg_color: self.bg_color = bg_color
        if text_color: self.text_color = text_color
        if is_dark is not None: self.is_dark = is_dark
        
        #sötét mód esetén világosabb szürke belső és külső keretszínek választása a kontraszt miatt
        grid_color = "#555" if self.is_dark else "#ccc"
        thick_color = "#888" if self.is_dark else "black"
        
        #vékony alapkeret összeállítása a témának megfelelő színnel
        border_style = f"border: 1px solid {grid_color}; "
        #a 3x3-as blokkok határain vastag keret beállítása
        if self.row % 3 == 0: border_style += f"border-top: 3px solid {thick_color}; "
        if self.col % 3 == 0: border_style += f"border-left: 3px solid {thick_color}; "
        #a tábla legalsó és legjobboldalibb külső szegélyének vastagítása
        if self.row == 8: border_style += f"border-bottom: 3px solid {thick_color}; "
        if self.col == 8: border_style += f"border-right: 3px solid {thick_color}; "
        
        #stíluslap összeállítása és érvényesítése a QLineEdit elemen
        style = f"QLineEdit {{ background-color: {self.bg_color}; color: {self.text_color}; {border_style} }}"
        self.setStyleSheet(style)

    #újrarajzolás: jegyzet mód esetén kirajzolja a 3x3-as rácsban elhelyezkedő apró számokat
    def paintEvent(self, event):
        super().paintEvent(event)
        #csak akkor rajzolunk egyedi jegyzeteket ha a cella jegyzet módban van és tartalmaz számokat
        if self.is_note and self.text():
            painter = QPainter(self)
            #élsimítás bekapcsolása a szebb és simább betűkirajzolás érdekében
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            #dinamikus betűméret: a cella magasságának kb. 16%-a, de minimum 6 pixel, hogy olvasható maradjon
            font_size = max(6, int(self.height() * 0.16))
            note_font = QFont("Arial", font_size, QFont.Weight.Normal)
            painter.setFont(note_font)
            
            #toll színe: sötét módban világosabb szürke (#aaaaaa), világosban sötétebb szürke (#777777)
            pen_color = "#aaaaaa" if self.is_dark else "#777777"
            painter.setPen(QColor(pen_color))
            
            #a cella felosztása 3 oszlopra és 3 sorra a belső 3x3-as jegyzetrácshoz
            cell_w = self.width() / 3.0
            cell_h = self.height() / 3.0
            
            #végigmegyünk az 1-9 számokon, és ha szerepel a jegyzetben, kirajzoljuk a megfelelő al-cellába
            for i in range(1, 10):
                if str(i) in self.text():
                    #oszlop és sorindex kiszámítása az aktuális számnak (0-2 közötti indexek)
                    col = (i - 1) % 3
                    row = (i - 1) // 3
                    #a kiszámolt téglalap bal felső koordinátái és mérete
                    x = col * cell_w
                    y = row * cell_h
                    rect = QRectF(x, y, cell_w, cell_h)
                    #a szám kirajzolása a megadott téglalap közepére igazítva
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(i))
            painter.end()

    #egérkattintás kezelése: továbbítja a koordinátákat és a Ctrl billentyű állapotát a többes kijelöléshez
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        #bites ÉS művelettel ellenőrizzük, hogy a Ctrl gomb le volt-e nyomva kattintáskor
        ctrl_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self.cell_clicked.emit(self.row, self.col, ctrl_pressed)

    #billentyűleütések szűrése: navigáció, számbevitel, törlés és nemkívánatos gombok kiszűrése
    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        
        #navigáció a nyilakkal
        if key == Qt.Key.Key_Up:
            self.move_requested.emit(-1, 0)
            event.accept()
            return
        elif key == Qt.Key.Key_Down:
            self.move_requested.emit(1, 0)
            event.accept()
            return
        elif key == Qt.Key.Key_Left:
            self.move_requested.emit(0, -1)
            event.accept()
            return
        elif key == Qt.Key.Key_Right:
            self.move_requested.emit(0, 1)
            event.accept()
            return
            
        #számok bevitele (1-9)
        elif text in "123456789" and text != "":
            self.input_requested.emit(text)
            event.accept()
            return
            
        #törlés kezelése (Backspace, Delete ÉS Szóköz gombokkal)
        elif key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Space):
            self.input_requested.emit("")
            event.accept()
            return
            
        #Ctrl + Z (Visszavonás) explicit hívása a főablakon
        elif key == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if hasattr(self.window(), 'undo'):
                self.window().undo()
            event.accept()
            return
            
        #N gomb (Jegyzet mód) explicit hívása a főablakon
        elif key == Qt.Key.Key_N:
            if hasattr(self.window(), 'toggle_pencil_shortcut'):
                self.window().toggle_pencil_shortcut()
            event.accept()
            return
            
        #T gomb (Tipp / Tanító mód) explicit hívása a főablakon
        elif key == Qt.Key.Key_T:
            if hasattr(self.window(), 'give_hint'):
                self.window().give_hint()
            event.accept()
            return
            
        #minden más (betűk, érvénytelen karakterek) blokkolása a cellában
        else:
            event.accept()

class NewGameDialog(QDialog):
    #az osztály egy modális párbeszédablakot valósít meg az új játék beállításainak kiválasztásához
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Új játék beállításai")
        #modális mód: megakadályozza a háttérablak kattintását a választásig
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        #nehézségi szint választó legördülő mező
        diff_layout = QHBoxLayout()
        diff_layout.addWidget(QLabel("Nehézségi szint:"))
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["Könnyű", "Közepes", "Nehéz"])
        diff_layout.addWidget(self.diff_combo)
        layout.addLayout(diff_layout)
        
        #tipp és tanító mód jelölőnégyzetek
        self.hint_checkbox = QCheckBox("Tipp engedélyezése")
        self.hint_checkbox.setChecked(True)
        layout.addWidget(self.hint_checkbox)
        
        self.tutor_checkbox = QCheckBox("Tanító mód (Magyarázatok és logikai tippek)")
        self.tutor_checkbox.setChecked(False)
        layout.addWidget(self.tutor_checkbox)

        #összekapcsoljuk a tanító mód jelölőnégyzetét a tipp állapotát szinkronizáló függvénnyel
        self.tutor_checkbox.toggled.connect(self.on_tutor_toggled)
        
        #indítás és mégse gombok hozzáadása a dialógushoz
        btn_layout = QHBoxLayout()
        start_btn = QPushButton("Indítás")
        #az accept elfogadja a párbeszédablakot és True értékkel zárja le
        start_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Mégse")
        #a reject elveti a párbeszédablakot és False értékkel zárja le
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    #ha a tanító mód be van kapcsolva, a tipp opció kötelezően bepipálódik és elszürkül
    def on_tutor_toggled(self, checked):
        if checked:
            self.hint_checkbox.setChecked(True)
            self.hint_checkbox.setEnabled(False)
        else:
            self.hint_checkbox.setEnabled(True)

class SudokuApp(QMainWindow):
    #a főablak és a játék teljes grafikus felületét és logikai összeköttetéseit kezelő osztály
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sudoku")
        
        #generátor és 9x9-es cellamátrix inicializálása
        self.generator = SudokuGenerator()
        self.game = None
        self.cells = [[None for _ in range(9)] for _ in range(9)]

        #aktív cella koordinátái és a többes kijelölést tároló halmaz
        self.last_active_row = -1
        self.last_active_col = -1
        self.selected_cells = set()

        #számbillentyűzet gombjait tároló szótár (1-9)
        self.number_buttons = {}

        #befejezett sorok, oszlopok és blokkok nyilvántartása a zöld villanásokhoz
        self.completed_rows = set()
        self.completed_cols = set()
        self.completed_blocks = set()

        #visszavonási lépések előzményeit tároló lista
        self.history = []

        #időmérő változói és 1 másodperces időzítő (QTimer) létrehozása
        self.elapsed_seconds = 0
        self.is_paused = False
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)

        #felhasználói felület, menü és gyorsgombok inicializálása
        self.setup_ui()
        self.create_menu()
        self.setup_shortcuts()

    #a grafikus felhasználói felület (UI) elemeinek felépítése és elrendezése
    def setup_ui(self):
        #külső tartály widget a tartalom középre igazításához méretezéskor
        outer_widget = QWidget()
        self.setCentralWidget(outer_widget)
        outer_layout = QGridLayout(outer_widget)
        
        #belső widget a méretezhető fix arányú tartalom tárolására
        self.main_content_widget = QWidget()
        main_layout = QVBoxLayout(self.main_content_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        #a belső tartalom rácson belüli középre igazítása
        outer_layout.addWidget(self.main_content_widget, 0, 0, Qt.AlignmentFlag.AlignCenter)
        
        #felső vezérlősáv: óra, új játék gomb és szünet gomb
        control_layout = QGridLayout()
        
        #óra inicializálása és elrejtése induláskor
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.timer_label.hide()

        #új játék gomb inicializálása és eseménykezelő bekötése
        new_game_btn = QPushButton("Új Játék Generálása")
        new_game_btn.setMinimumHeight(40)
        new_game_btn.clicked.connect(self.new_game)
        
        #szünet gomb inicializálása és elrejtése induláskor
        self.pause_btn = QPushButton("Szünet")
        self.pause_btn.setMinimumWidth(80)
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.hide()
        
        #elemek elrendezése rácsban a tökéletes középre igazításért
        control_layout.addWidget(self.timer_label, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        control_layout.addWidget(new_game_btn, 0, 1, Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self.pause_btn, 0, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        #a bal és jobb oszlopok egyforma nyújtása biztosítja a középső elem fix középen maradását
        control_layout.setColumnStretch(0, 1)
        control_layout.setColumnStretch(1, 0)
        control_layout.setColumnStretch(2, 1)
        
        main_layout.addLayout(control_layout)
        
        #játéktér konténer: rács és a vezérlőgombok
        self.game_container = QWidget()
        game_layout = QVBoxLayout(self.game_container)
        game_layout.setContentsMargins(0, 10, 0, 0)
        
        #rétegváltó (QStackedWidget) a tábla és a szünet képernyő közötti váltáshoz
        self.board_stack = QStackedWidget()
        game_layout.addWidget(self.board_stack)
        
        #1. réteg: a 9x9-es sudoku rács celláinak létrehozása és elhelyezése
        self.grid_widget = QWidget()
        grid_container = QHBoxLayout(self.grid_widget)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(0)
        
        #81 cella inicializálása és szignáljaik bekötése
        for r in range(9):
            for c in range(9):
                cell = SudokuCell(r, c)
                self.cells[r][c] = cell
                cell.setFixedSize(50, 50) 
                grid_layout.addWidget(cell, r, c)
                
                #szignálok összekötése az alkalmazás kezelőmetódusaival
                cell.cell_clicked.connect(self.handle_cell_click)
                cell.input_requested.connect(self.numpad_clicked)
                cell.move_requested.connect(self.move_focus)
                
        grid_container.addStretch()
        grid_container.addLayout(grid_layout)
        grid_container.addStretch()
        self.board_stack.addWidget(self.grid_widget)
        
        #2. réteg: a szünet képernyő létrehozása szürke háttérrel és felirattal
        self.pause_widget = QWidget()
        self.pause_widget.setStyleSheet("background-color: #cccccc;")
        pause_layout = QVBoxLayout(self.pause_widget)
        
        pause_label = QLabel("Szünet")
        pause_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        pause_label.setStyleSheet("color: #444444;")
        pause_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pause_layout.addWidget(pause_label)
        self.board_stack.addWidget(self.pause_widget)
        
        #számbillentyűzet gombjainak (1-9) létrehozása és stílusozása
        numbers_layout = QHBoxLayout()
        
        #rugalmas térkitöltő a bal oldalra
        numbers_layout.addStretch()
        
        for i in range(1, 10):
            btn = QPushButton(str(i))
            btn.setFixedSize(40, 40)
            btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))

            #stíluslap az aktív (halványzöld), lebegő és inaktív (szürke) állapotokhoz
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e8f5e9;
                    color: black;
                    border: 1px solid #b9cba6;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #c8e6c9;
                }
                QPushButton:disabled { 
                    background-color: #e0e0e0;
                    color: #a0a0a0; 
                    border: 1px solid #ccc;
                }
            """)
            
            #lambda függvény segítségével kötjük be a gombhoz tartozó számot
            btn.clicked.connect(lambda checked, num=str(i): self.numpad_clicked(num))
            numbers_layout.addWidget(btn)
            self.number_buttons[str(i)] = btn
            
        #rugalmas térkitöltő a jobb oldalra
        numbers_layout.addStretch()
            
        game_layout.addLayout(numbers_layout)

        #akciógombok: visszavonás, tipp, törlés és jegyzet mód
        actions_layout = QHBoxLayout()

        undo_btn = QPushButton("Visszavonás")
        undo_btn.setMinimumHeight(40)
        undo_btn.setShortcut("Ctrl+Z")
        undo_btn.clicked.connect(self.undo)
        actions_layout.addWidget(undo_btn)

        self.hint_btn = QPushButton("Tipp (+30 mp)")
        self.hint_btn.setMinimumHeight(40)
        self.hint_btn.clicked.connect(self.give_hint)
        actions_layout.addWidget(self.hint_btn)
        
        clear_btn = QPushButton("Törlés")
        clear_btn.setMinimumHeight(40)
        clear_btn.clicked.connect(lambda: self.numpad_clicked(""))
        actions_layout.addWidget(clear_btn)

        self.pencil_btn = QPushButton("Jegyzet")
        self.pencil_btn.setCheckable(True)
        self.pencil_btn.setMinimumHeight(40)
        self.pencil_btn.setStyleSheet("QPushButton:checked { background-color: #ffeb3b; font-weight: bold; }")
        actions_layout.addWidget(self.pencil_btn)
        
        game_layout.addLayout(actions_layout)

        #vízszintes elrendezés (QHBoxLayout) létrehozása a két megoldó gomb egymás mellé helyezéséhez
        solve_buttons_layout = QHBoxLayout()
        
        #1. gomb: A klasszikus Backtrack megoldó meghívása
        self.auto_solve_btn = QPushButton("Kirakás (Backtracking)")
        self.auto_solve_btn.clicked.connect(self.auto_solve)
        self.auto_solve_btn.setMinimumHeight(40)
        self.auto_solve_btn.setStyleSheet("""
            QPushButton { background-color: #d4edda; color: #155724; font-weight: normal; border: 1px solid #2e7d32; border-radius: 0px; } 
            QPushButton:hover { background-color: #c3e6cb; }
        """)
        solve_buttons_layout.addWidget(self.auto_solve_btn)
        
        #2. gomb: Az új Dancing Links (DLX) megoldó meghívása
        self.dlx_solve_btn = QPushButton("Kirakás (DLX)")
        self.dlx_solve_btn.clicked.connect(self.auto_solve_dlx)
        self.dlx_solve_btn.setMinimumHeight(40)
        self.dlx_solve_btn.setStyleSheet("""
            QPushButton { background-color: #cce5ff; color: #004085; font-weight: normal; border: 1px solid #1565c0; border-radius: 0px; } 
            QPushButton:hover { background-color: #b8daff; }
        """)
        solve_buttons_layout.addWidget(self.dlx_solve_btn)
        
        #a gombokat tartalmazó elrendezés hozzáadása a játéktér fő függőleges layoutjához
        game_layout.addLayout(solve_buttons_layout)
        
        #játéktér elhelyezése a fő layoutban és alapértelmezett elrejtése
        main_layout.addWidget(self.game_container)
        self.game_container.hide()
        
        main_layout.addStretch()
        
        #ablak alapméreteinek és minimum méretének beállítása induláskor
        self.setMinimumSize(400, 80)
        self.resize(400, 80)

    #globális billentyűparancsok (gyorsgombok) inicializálása
    def setup_shortcuts(self):
        #N: ceruza / jegyzet mód ki- és bekapcsolása
        self.shortcut_n = QShortcut(QKeySequence("N"), self)
        self.shortcut_n.activated.connect(self.toggle_pencil_shortcut)
        
        #Szóköz: aktív cella tartalmának ürítése
        self.shortcut_space = QShortcut(QKeySequence("Space"), self)
        self.shortcut_space.activated.connect(self.clear_cell_shortcut)
        
        #T: segítség / tipp kérése
        self.shortcut_t = QShortcut(QKeySequence("T"), self)
        self.shortcut_t.activated.connect(self.give_hint)

    #jegyzet mód ki- és bekapcsolása gyorsgombbal ha a játék nem áll szünet alatt
    def toggle_pencil_shortcut(self):
        if not hasattr(self, 'is_paused') or not self.is_paused:
            self.pencil_btn.toggle()

    #cella tartalmának törlése gyorsgombbal ha a játék nem áll szünet alatt
    def clear_cell_shortcut(self):
        if not hasattr(self, 'is_paused') or not self.is_paused:
            self.numpad_clicked("")

    #kiszámolja egy adott cellába beírható lehetséges számok (kandidátusok) halmazát
    def get_candidates(self, r, c):
        #ha a cella már végleges számot tartalmaz, nincsenek szabad lehetőségei
        if self.cells[r][c].text() != "" and not self.cells[r][c].is_note:
            return set()
            
        used = set()
        #sorban és oszlopban lévő már beírt számok összegyűjtése
        for i in range(9):
            c_row = self.cells[r][i]
            if not c_row.is_note and c_row.text().isdigit():
                used.add(int(c_row.text()))
            c_col = self.cells[i][c]
            if not c_col.is_note and c_col.text().isdigit():
                used.add(int(c_col.text()))
                
        #a cellát tartalmazó 3x3-as blokk kezdőkoordinátáinak kiszámítása
        br, bc = (r // 3) * 3, (c // 3) * 3
        #a 3x3-as blokkban már szereplő számok hozzáadása a tiltólistához
        for i in range(3):
            for j in range(3):
                cell = self.cells[br + i][bc + j]
                if not cell.is_note and cell.text().isdigit():
                    used.add(int(cell.text()))
                    
        #az 1-9 tartományból kivonjuk a tiltott számokat, megkapva az érvényes kandidátusokat
        return set(range(1, 10)) - used

    #részletesen kielemzi a kiválasztott cellát az oktató mód számára
    def analyze_selected_cell(self, r, c):
        candidates = sorted(list(self.get_candidates(r, c)))
        
        #1. eset: egyetlen lehetséges szám maradt (naked single)
        if len(candidates) == 1:
            val = str(candidates[0])
            title = "Egyértelmű mező! (Egyetlen lehetőség)"
            explanation = (
                f"A kijelölt <b>{r+1}. sor, {c+1}. oszlop</b> cellájába kizárólag a <b>{val}</b>-es szám írható be!<br><br>"
                "A környező sorban, oszlopban és a 3×3-as blokkban lévő számok minden más lehetőséget kizárnak."
            )
            #a 4. visszatérési érték jelzi, hogy felajánlható-e az automatikus beírás
            return val, title, explanation, True

        #2. eset: több lehetséges szám is szóba jöhet még
        elif len(candidates) > 1:
            cand_str = ", ".join(map(str, candidates))
            title = "Nem egyértelmű mező"
            explanation = (
                f"A kijelölt <b>{r+1}. sor, {c+1}. oszlop</b> jelenleg nem dönthető el egyértelműen.<br><br>"
                f"<b>Lehetséges számok ide:</b> <span style='color: #007bff; font-weight: bold;'>{cand_str}</span><br><br>"
                "<i>Tipp:</i> Érdemes ezeket a számokat feljegyezni (Jegyzet mód), vagy keresni egy másik mezőt a sorban/blokkban, amely jobban leszűkíti a lehetőségeket!"
            )
            return None, title, explanation, False

        #3. eset: nincs érvényes kandidátus (korábbi hiba vagy ellentmondás miatt)
        else:
            title = "Ellentmondás / Hiba a táblán"
            explanation = (
                f"A <b>{r+1}. sor, {c+1}. oszlop</b> cellájába a jelenlegi állás szerint <b>egyetlen szám sem írható be</b>!<br><br>"
                "Ez azt jelenti, hogy valamelyik korábban beírt szám rossz helyen van. Érdemes átnézni a sort, oszlopot vagy visszavonni pár lépést."
            )
            return None, title, explanation, False

    #tippet ad a játékosnak vagy meghívja a kijelölt cella tanító elemzését
    def give_hint(self):
        #érvényesség és szüneteltetés ellenőrzése
        if not hasattr(self, 'game') or not self.game or self.is_paused:
            return
            
        #ha a tipp funkció tiltva van a játékban, kilépünk
        if not getattr(self, 'hints_allowed', True):
            return

        #tanító mód logikája
        if getattr(self, 'tutor_mode', False):
            #pontosan egy cellának kell kijelölve lennie az elemzéshez
            if len(self.selected_cells) != 1:
                QMessageBox.information(
                    self, 
                    "Oktató mód", 
                    "Kérlek, válassz ki <b>pontosan egy üres cellát</b> a táblán, amit elemezni szeretnél!"
                )
                return

            r, c = list(self.selected_cells)[0]
            cell = self.cells[r][c]

            #fix kezdőszámok vagy kész számok esetén figyelmeztetést adunk
            if cell.isReadOnly() or (cell.text() != "" and not cell.is_note):
                QMessageBox.information(
                    self, 
                    "Oktató mód", 
                    "Ez a mező már ki van töltve! Válassz egy <b>üres vagy jegyzetelt</b> cellát az elemzéshez."
                )
                return

            #a kiválasztott cella logikai elemzése
            val, title, explanation, can_autofill = self.analyze_selected_cell(r, c)
            
            #az elemzett cella sárgás kiemelése a táblán
            cell.apply_style(bg_color="#fff3cd", text_color="#6b5714")

            msg = QMessageBox(self)
            msg.setWindowTitle(f"Oktató: {title}")
            msg.setIcon(QMessageBox.Icon.Information)

            #ha a mező egyértelmű, gombot adunk a közvetlen beíráshoz
            if can_autofill:
                msg.setText(f"{explanation}<br><br>Szeretnéd, hogy a program automatikusan beírja a számot?")
                yes_btn = msg.addButton("Igen, írja be", QMessageBox.ButtonRole.YesRole)
                no_btn = msg.addButton("Köszönöm, beírom én", QMessageBox.ButtonRole.NoRole)
            else:
                msg.setText(explanation)
                msg.addButton("Értem", QMessageBox.ButtonRole.AcceptRole)

            #sötét mód stílus alkalmazása a magyarázó ablakra
            if hasattr(self, 'dark_mode_action') and self.dark_mode_action.isChecked():
                msg.setStyleSheet("""
                    QMessageBox { background-color: #121212; color: white; } 
                    QLabel { color: white; font-size: 14px; } 
                    QPushButton { background-color: #333; color: white; padding: 5px 12px; border: 1px solid #555; }
                """)

            msg.exec()

            #ha a felhasználó az automatikus beírásra kattintott
            if can_autofill and msg.clickedButton() == yes_btn:
                if self.pencil_btn.isChecked():
                    self.pencil_btn.setChecked(False)
                self.numpad_clicked(val)
            else:
                #különben 600 ms múlva visszaállítjuk a normál táblaszínezést
                QTimer.singleShot(600, self.refresh_highlights)
            return

        #hagyományos tipp kérése (+30 másodperc büntetéssel) - mindig véletlenszerű
        
        #összegyűjtjük az összes üres (vagy csak jegyzetet tartalmazó) cellát a táblán
        empty_cells = [(r, c) for r in range(9) for c in range(9) if self.cells[r][c].text() == "" or self.cells[r][c].is_note]
        
        #ha már nincs üres cella, a tipp funkció nem csinál semmit
        if not empty_cells:
            return
            
        #véletlenszerűen kiválasztunk egyet a lehetséges üres cellák közül
        target_r, target_c = random.choice(empty_cells)
                    
        #a helyes megoldásból kiolvassuk és beírjuk a számot
        if hasattr(self, 'correct_solution'):
            correct_val = str(self.correct_solution[target_r][target_c])
            
            #a cella megjelölése tippeltként
            target_cell = self.cells[target_r][target_c]
            target_cell.is_hinted = True
            
            self.selected_cells = {(target_r, target_c)}
            self.last_active_row = target_r
            self.last_active_col = target_c
            
            if self.pencil_btn.isChecked():
                self.pencil_btn.setChecked(False)
                
            self.numpad_clicked(correct_val)
            
            #30 másodperc büntetés hozzáadása az eltelt időhöz és órafrissítés
            self.elapsed_seconds += 30
            mins = self.elapsed_seconds // 60
            secs = self.elapsed_seconds % 60
            self.timer_label.setText(f"{mins:02d}:{secs:02d}")
            
            #kijelölés megszüntetése, hogy azonnal a normál háttérrel látszódjon a narancssárga szám
            self.selected_cells = set()
            self.last_active_row = -1
            self.last_active_col = -1
            
            self.refresh_highlights()

    #felső menüsor létrehozása (beállítások és súgó menüpontok)
    def create_menu(self):
        menu_bar = self.menuBar()
        
        #beállítások menü
        settings_menu = menu_bar.addMenu("Beállítások")
        
        #vizuális kiemelés kapcsoló
        self.highlight_action = QAction("Vizuális kiemelés", self)
        self.highlight_action.setCheckable(True)
        self.highlight_action.setChecked(True)
        self.highlight_action.toggled.connect(self.refresh_highlights)
        settings_menu.addAction(self.highlight_action)
        
        #sötét mód kapcsoló
        self.dark_mode_action = QAction("Sötét mód", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(False)
        self.dark_mode_action.toggled.connect(self.apply_theme)
        settings_menu.addAction(self.dark_mode_action)

        #teljesítménymutatók kapcsolói
        self.show_metrics_action = QAction("Idő megjelenítése automatikus kirakáskor", self)
        self.show_metrics_action.setCheckable(True)
        self.show_metrics_action.setChecked(False)
        settings_menu.addAction(self.show_metrics_action)

        #súgó menü
        help_menu = menu_bar.addMenu("Segítség")
        
        #játékszabályok és útmutató megjelenítése
        rules_action = QAction("Súgó", self)
        rules_action.triggered.connect(self.show_rules) 
        help_menu.addAction(rules_action)

    #új játék indítása, a tábla generálása, megoldás kiszámítása és állapotok alaphelyzetbe állítása
    def new_game(self):
        #mindig felugrik az új játék beállító ablak
        dialog = NewGameDialog(self)
        
        #előre beállítjuk a dialógust a legutóbbi állapotra (vagy alapértelmezettre)
        dialog.hint_checkbox.setChecked(getattr(self, 'hints_allowed', True))
        dialog.tutor_checkbox.setChecked(getattr(self, 'tutor_mode', False))
        
        #sötét téma alkalmazása a felugró ablakra
        if hasattr(self, 'dark_mode_action') and self.dark_mode_action.isChecked():
            dialog.setStyleSheet("""
                QDialog { background-color: #121212; color: white; } 
                QLabel, QCheckBox { color: white; } 
                QPushButton { background-color: #333; color: white; border: 1px solid #555; padding: 5px 10px; } 
                QComboBox { background-color: #333; color: white; border: 1px solid #555; }
            """)
            
        #ha a felhasználó a 'mégse' gombra nyom vagy bezárja az ablakot, megszakítjuk az indítást
        if not dialog.exec():
            return
            
        #beállítások kiolvasása a dialógusból
        diff_text = dialog.diff_combo.currentText()
        hints_allowed = dialog.hint_checkbox.isChecked()
        tutor_mode = dialog.tutor_checkbox.isChecked()

        #ha ez a legelső indítás, most fedjük fel és méretezzük át az ablakot
        if self.game_container.isHidden():
            self.game_container.show()
            self.timer_label.show()
            self.pause_btn.show()
            self.setMinimumSize(400, 580)
            self.resize(440, 600)
        
        #kész egységek és előzmények kiürítése
        self.completed_rows.clear()
        self.completed_cols.clear()
        self.completed_blocks.clear()
        self.history.clear()
        
        #tipp és oktató mód állapotának érvényesítése a felületen
        self.hints_allowed = hints_allowed
        self.tutor_mode = tutor_mode
        self.hint_btn.setVisible(self.hints_allowed)
        
        if self.tutor_mode:
            self.hint_btn.setText("Magyarázat")
        else:
            self.hint_btn.setText("Tipp (+30 mp)")

        #nehézségi szint leképezése belső kulcsszavakra
        if diff_text == "Könnyű": diff = "easy"
        elif diff_text == "Közepes": diff = "medium"
        else: diff = "hard"
        
        #feladvány legenerálása a generator modullal időméréssel
        start_time = time.perf_counter()
        self.game = self.generator.generate(difficulty=diff)
        end_time = time.perf_counter()

        #csak akkor dobja fel az ablakot, ha a menüben be van kapcsolva
        if hasattr(self, 'show_metrics_action') and self.show_metrics_action.isChecked():
            gen_time_ms = (end_time - start_time) * 1000
            QMessageBox.information(self, "Generálás", f"A feladvány sikeresen létrejött!\nGenerálási idő: {gen_time_ms:.2f} ms")

        #helyes megoldás legenerálása és tárolása a háttérben
        initial_board = [[self.game.board[r][c] for c in range(9)] for r in range(9)]
        
        #neehéz pálya esetén DLX-et, egyébként backtrackinget használunk a megoldáshoz
        if diff == "hard":
            solver = DancingLinksSolver(initial_board)
        else:
            solver = BacktrackingSolver(initial_board)
            
        solver.solve()
        self.correct_solution = solver.board
        
        #cellák feltöltése és stílusozása a generált feladvány alapján
        for r in range(9):
            for c in range(9):
                val = self.game.board[r][c]
                cell = self.cells[r][c]
                
                if val != 0:
                    cell.setText(str(val))
                    cell.setReadOnly(True)
                    cell.apply_style(bg_color="#f0f0f0", text_color="#0044cc")
                else:
                    cell.setReadOnly(False)
                    cell.clear()
                    cell.is_note = False
                    cell.is_hinted = False
                    cell.apply_style(bg_color="white", text_color="black")
                    
        #kijelölések törlése és állapotok frissítése
        self.last_active_row = -1
        self.last_active_col = -1
        self.refresh_highlights()
        self.update_numpad_state()
        
        #statisztikák és stopper újraindítása
        self.mistakes = 0
        self.elapsed_seconds = 0
        self.timer_label.setText("00:00")
        
        self.is_paused = False
        self.pause_btn.setText("Szünet")
        self.board_stack.setCurrentIndex(0)
        
        #stopper elindítása másodpercenkénti (1000 ms) periódussal
        self.clock_timer.start(1000)

    #visszavonja a játékos legutóbbi lépését a tábla előző mentett állapota alapján
    def undo(self):
        if not hasattr(self, 'history') or not self.history:
            return
            
        #legutolsó állapot kivétele a memóriából
        last_state = self.history.pop()
        
        #a nem írásvédett cellák visszaállítása a korábbi állapotra
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                if not cell.isReadOnly():
                    text, is_note = last_state[r][c]
                    cell.setText(text)
                    cell.is_note = is_note
                    
        #vizuális állapotok, gombok és befejezett egységek újraszámolása
        self.refresh_highlights()
        self.update_numpad_state()
        self.check_completed_units()

    #ellenőrzi, hogy a tábla teljesen és helyesen ki lett-e töltve, majd megjeleníti az eredményt
    def check_victory(self):
        if not hasattr(self, 'game') or not self.game:
            return

        #ha van üres cella vagy jegyzet, a játék még nem ért véget
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                if cell.text() == "" or cell.is_note:
                    return

        #stopper megállítása győzelem esetén
        self.clock_timer.stop() 
        
        #eltelt idő formázása perc:másodperc (00:00) formátumba
        minutes = self.elapsed_seconds // 60
        seconds = self.elapsed_seconds % 60
        time_formatted = f"{minutes:02d}:{seconds:02d}"

        #győzelmi értesítő ablak megjelenítése a statisztikákkal
        msg = QMessageBox(self)
        msg.setWindowTitle("Győzelem!")
        
        msg_text = (
            "Gratulálok! Sikeresen megoldottad a Sudokut!\n\n"
            f"Eltelt idő: {time_formatted}\n"
            f"Hibák száma: {self.mistakes}"
        )
        msg.setText(msg_text)
        
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("QLabel{font-size: 14px;}")
        msg.exec()
    
    #megjeleníti a játékszabályokat, billentyűparancsokat és beállításokat a súgó ablakban
    def show_rules(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Súgó")
        
        #html formázott leírás a szabályzatról és az új funkciókról
        rules_text = """
        <h3>Játékszabályok</h3>
        <p>A 9×9-es játéktábla minden sorában és oszlopában az 1-től 9-ig terjedő egész számokat kell elhelyezni oly módon, hogy minden érték pontosan egyszer forduljon elő. A feltétel továbbá kiterjed a felbontott 3×3-as blokkokra is, melyeket vastag, fekete vonal határol.</p>
        <h3>Billentyűparancsok (Gyorsgombok)</h3>
        <ul>
            <li><b>Nyílbillentyűk:</b> Navigálás a cellák között.</li>
            <li><b>1-9:</b> Szám beírása a kijelölt cellába.</li>
            <li><b>N:</b> Jegyzet mód (ceruza) ki- és bekapcsolása.</li>
            <li><b>Backspace / Delete:</b> A kijelölt cella törlése.</li>
            <li><b>T:</b> Tipp kérése vagy a Tanító elemzés indítása.</li>
            <li><b>Ctrl + Z:</b> Utolsó lépés visszavonása.</li>
            <li><b>Ctrl + Kattintás:</b> Több cella egyidejű kijelölése.</li>
        </ul>

        <h3>Funkciók és Játékmódok</h3>
        <ul>
            <li><b>Új játék:</b> A gombra kattintva felugró ablakban nehézségi szint választható, és a segédletek beállíthatóak.</li>
            <li><b>Tanító mód:</b> Ha aktív, a Megoldás gomb logikai elemzést készít az aktuálisan kijelölt celláról (mik a lehetséges opciók, és meg lehet-e már határozni a számot).</li>
            <li><b>Tipp (+30 mp):</b> Hagyományos mód esetén egy véletlenszerű helyes szám felfedhető 30 másodperc büntetésért cserébe, mely narancssárga színnel jelenik meg.</li>
            <li><b>Kirakás DLX vagy Backtracking módszerrel:</b> A program automatikusan kiszámolja és zöld színnel beírja a hiányzó számokat a választott algoritmussal.</li>
            <li><b>Vizuális kiemelés:</b> A felső menüből kapcsolható, segít átlátni a sorok, oszlopok, blokkok és azonos számok kapcsolatait.</li>
        </ul>
        """
        
        msg.setText(rules_text)
        msg.setIcon(QMessageBox.Icon.Information)
        
        #sötét mód stílusának alkalmazása az ablakra ha aktív
        is_dark = hasattr(self, 'dark_mode_action') and self.dark_mode_action.isChecked()
        if is_dark:
            msg.setStyleSheet("QMessageBox { background-color: #121212; color: white; } QLabel { color: white; font-size: 14px; } QPushButton { background-color: #333; color: white; padding: 5px 15px; }")
        else:
            msg.setStyleSheet("QLabel { font-size: 14px; }")
            
        msg.exec()

    #megkeresi azokat a cellákat egy sorban, oszlopban vagy blokkban, amelyek ütköznek a beírandó számmal
    def find_conflicts(self, row, col, value):
        conflicts = []
        
        for i in range(9):
            #sor ütközések keresése
            cell_row = self.cells[row][i]
            if not cell_row.is_note and cell_row.text() == value and i != col:
                conflicts.append((row, i))
                
            #oszlop ütközések keresése
            cell_col = self.cells[i][col]
            if not cell_col.is_note and cell_col.text() == value and i != row:
                conflicts.append((i, col))
                
        #3x3-as blokk ütközések keresése
        start_r = (row // 3) * 3
        start_c = (col // 3) * 3
        for r in range(start_r, start_r + 3):
            for c in range(start_c, start_c + 3):
                cell_block = self.cells[r][c]
                if not cell_block.is_note and cell_block.text() == value and (r != row or c != col):
                    conflicts.append((r, c))
                    
        return conflicts

    #piros színnel villantja fel a hibásan ütköző cellákat 200 ms időtartamra
    def flash_conflicts(self, conflict_coords):
        for r, c in conflict_coords:
            cell = self.cells[r][c]
            #háttér megtartása mellett a betűszín pirosra állítása
            cell.apply_style(bg_color=cell.bg_color, text_color="red")
            
        #200 ms elteltével a színező visszaállítja a normál kiemelést
        QTimer.singleShot(200, self.refresh_highlights)

    #ellenőrzi az elkészült sorokat, oszlopokat és blokkokat, és zöld felvillanással jutalmazza őket
    def check_completed_units(self):
        if not hasattr(self, 'game') or not self.game:
            return

        cells_to_flash = set()

        #sorok teljességének vizsgálata
        for r in range(9):
            is_complete = True
            for c in range(9):
                cell = self.cells[r][c]
                if cell.text() == "" or cell.is_note:
                    is_complete = False
                    break
            
            #új befejezett sor hozzáadása a villantandó halmazhoz
            if is_complete and r not in self.completed_rows:
                self.completed_rows.add(r)
                for c in range(9): cells_to_flash.add((r, c))
            elif not is_complete and r in self.completed_rows:
                self.completed_rows.remove(r)

        #oszlopok teljességének vizsgálata
        for c in range(9):
            is_complete = True
            for r in range(9):
                cell = self.cells[r][c]
                if cell.text() == "" or cell.is_note:
                    is_complete = False
                    break
            
            #új befejezett oszlop hozzáadása
            if is_complete and c not in self.completed_cols:
                self.completed_cols.add(c)
                for r in range(9): cells_to_flash.add((r, c))
            elif not is_complete and c in self.completed_cols:
                self.completed_cols.remove(c)

        #3x3-as blokkok teljességének vizsgálata
        for br in range(3):
            for bc in range(3):
                block_idx = (br, bc)
                is_complete = True
                for i in range(3):
                    for j in range(3):
                        cell = self.cells[br * 3 + i][bc * 3 + j]
                        if cell.text() == "" or cell.is_note:
                            is_complete = False
                            break
                    if not is_complete: break
                
                #új befejezett blokk hozzáadása
                if is_complete and block_idx not in self.completed_blocks:
                    self.completed_blocks.add(block_idx)
                    for i in range(3):
                        for j in range(3):
                            cells_to_flash.add((br * 3 + i, bc * 3 + j))
                elif not is_complete and block_idx in self.completed_blocks:
                    self.completed_blocks.remove(block_idx)

        #ha van új kész egység, zöld háttérrel villantjuk fel
        if cells_to_flash:
            for r, c in cells_to_flash:
                cell = self.cells[r][c]
                cell.apply_style(bg_color="#d4edda", text_color=cell.text_color)
                
            #200 ms elteltével a színezés visszaáll a normál állapotra
            QTimer.singleShot(200, self.refresh_highlights)

    #kezeli a cellára kattintást (sima és Ctrl-billentyűs többes kijelölés)
    def handle_cell_click(self, row, col, ctrl_pressed):
        if ctrl_pressed:
            #Ctrl esetén ki-be kapcsoljuk a cellát a halmazban (toggle)
            if (row, col) in self.selected_cells:
                self.selected_cells.remove((row, col))
                if self.last_active_row == row and self.last_active_col == col:
                    self.last_active_row = -1
                    self.last_active_col = -1
            else:
                self.selected_cells.add((row, col))
                self.last_active_row = row
                self.last_active_col = col
        else:
            #sima kattintáskor töröljük a többes kijelölést, és csak ez az egy lesz aktív
            self.selected_cells = {(row, col)}
            self.last_active_row = row
            self.last_active_col = col
            
        self.refresh_highlights()

        if self.last_active_row != -1:
            self.cells[self.last_active_row][self.last_active_col].setFocus()

    #áthelyezi az aktív fókuszt a billentyűzet nyilainak lenyomásakor
    def move_focus(self, d_row, d_col):
        if self.last_active_row == -1 or self.last_active_col == -1:
            return

        #moduló 9 segítségével a rács szélein körbefordul a navigáció
        new_row = (self.last_active_row + d_row) % 9
        new_col = (self.last_active_col + d_col) % 9

        self.selected_cells = {(new_row, new_col)}
        self.last_active_row = new_row
        self.last_active_col = new_col

        self.refresh_highlights()
        self.cells[new_row][new_col].setFocus()

    #számok beírása, jegyzetelés, konfliktus-ellenőrzés és jegyzettakarítás
    def numpad_clicked(self, value):
        if not self.selected_cells:
            return
            
        is_pencil = self.pencil_btn.isChecked()
        
        #konfliktusok ellenőrzése új számok beírása előtt
        conflicts = set()
        if value != "":
            for r, c in self.selected_cells:
                cell = self.cells[r][c]
                if cell.isReadOnly():
                    continue
                    
                is_adding = True
                #jegyzetből való törlésnél nem vizsgálunk ütközést
                if is_pencil and cell.is_note and value in cell.text():
                    is_adding = False
                    
                if is_adding:
                    cell_conflicts = self.find_conflicts(r, c, value)
                    if cell_conflicts:
                        conflicts.update(cell_conflicts)
                        
        #ha ütközés van, növeljük a hibák számát és felvillantjuk a hibás mezőket
        if conflicts:
            self.mistakes += 1
            self.flash_conflicts(conflicts)
            if self.last_active_row != -1:
                self.cells[self.last_active_row][self.last_active_col].setFocus()
            return
        
        #aktuális táblaállapot mentése a visszavonási előzményekbe
        current_state = [[(self.cells[r][c].text(), self.cells[r][c].is_note) for c in range(9)] for r in range(9)]
        self.history.append(current_state)
            
        #érték beírása vagy jegyzetek frissítése a kijelölt cellákban
        for r, c in self.selected_cells:
            cell = self.cells[r][c]
            
            if cell.isReadOnly():
                continue
                
            #törlés művelet
            if value == "":
                cell.setText("")
                cell.is_note = False
            #jegyzetelés ceruzával: szám hozzáadása vagy eltávolítása és rendezése
            elif is_pencil:
                if not cell.is_note:
                    cell.setText(value)
                    cell.is_note = True
                else:
                    current = cell.text()
                    if value in current:
                        current = current.replace(value, "") 
                    else:
                        current += value 
                    current = "".join(sorted(current))
                    cell.setText(current)
            #végleges szám beírása tollal
            else:
                cell.setText(value)
                cell.is_note = False
                
                #automatikus jegyzettakarítás a kapcsolódó sorban, oszlopban és blokkban
                for r2 in range(9):
                    for c2 in range(9):
                        if r2 == r and c2 == c: continue
                        if r2 == r or c2 == c or (r2 // 3 == r // 3 and c2 // 3 == c // 3):
                            target_cell = self.cells[r2][c2]
                            if target_cell.is_note and value in target_cell.text():
                                new_note = target_cell.text().replace(value, "")
                                target_cell.setText(new_note)
                                if new_note == "":
                                    target_cell.is_note = False
                
        if self.last_active_row != -1:
            self.cells[self.last_active_row][self.last_active_col].setFocus()
            
        #táblaszínek, gombok inaktiválása, kész egységek és győzelem ellenőrzése
        self.refresh_highlights()
        self.update_numpad_state()
        self.check_completed_units()
        self.check_victory()

    #megoldja a táblát a háttérben a BacktrackingSolver segítségével, és kitölti az üres helyeket
    def auto_solve(self):
        if not self.game:
            QMessageBox.warning(self, "Hiba", "Előbb generálj egy játékot!")
            return

        #aktuális táblaértékek kinyerése a felületről a megoldó számára
        current_board = [[0 for _ in range(9)] for _ in range(9)]
        for r in range(9):
            for c in range(9):
                text = self.cells[r][c].text()
                if text.isdigit():
                    current_board[r][c] = int(text)
                else:
                    current_board[r][c] = 0

        solver = BacktrackingSolver(current_board)
        
        #időmérés indítása a perf_counter segítségével
        start_time = time.perf_counter()
        
        #ha a backtracking algoritmus talált érvényes megoldást, elmentjük az eredményt
        is_solved = solver.solve()
        
        #időmérés leállítása
        end_time = time.perf_counter()
        
        if is_solved:
            #zöld számmal beírjuk az üres helyekre a megoldást
            for r in range(9):
                for c in range(9):
                    cell = self.cells[r][c]
                    if cell.text() == "":
                        cell.setText(str(solver.board[r][c]))
                        
                        base_style = cell.styleSheet()
                        new_style = base_style.replace("color: black;", "color: #008800;")
                        cell.setStyleSheet(new_style)
                        
            #eltelt idő kiszámítása milliszekundumban és formázott kiírása
            elapsed_ms = (end_time - start_time) * 1000
            
            #csak akkor dobja fel az ablakot, ha a menüben be van kapcsolva
            if hasattr(self, 'show_metrics_action') and self.show_metrics_action.isChecked():
                QMessageBox.information(
                    self, 
                    "Kész", 
                    f"A Backtracking algoritmus megoldotta a feladványt!\n\nFutási idő: {elapsed_ms:.2f} ms"
                )
        else:
            QMessageBox.warning(self, "Hiba", "Ebből az állapotból nem lehet megoldani a Sudokut! Valószínűleg rossz számot írtál be valahová.")

    #megoldja a táblát a Dancing Links (DLX) algoritmus segítségével, és kitölti az üres helyeket
    def auto_solve_dlx(self):
        #ellenőrizzük, hogy fut-e már érvényes játék
        if not self.game:
            QMessageBox.warning(self, "Hiba", "Előbb generálj egy játékot!")
            return

        #9x9-es mátrix inicializálása az aktuális GUI táblaállapot kinyeréséhez
        current_board = [[0 for _ in range(9)] for _ in range(9)]
        for r in range(9):
            for c in range(9):
                text = self.cells[r][c].text()
                #ha a cella számot tartalmaz (nem üres és nem csak jegyzet), beírjuk a mátrixba
                if text.isdigit():
                    current_board[r][c] = int(text)
                else:
                    current_board[r][c] = 0

        #példányosítjuk az új Dancing Links alapú megoldót az aktuális táblaállapottal
        solver = DancingLinksSolver(current_board)
        
        #időmérés indítása
        start_time = time.perf_counter()
        
        #ha a DLX algoritmus talál megoldást (True értékkel tér vissza)
        is_solved = solver.solve()
        
        #időmérés leállítása
        end_time = time.perf_counter()
        
        if is_solved:
            for r in range(9):
                for c in range(9):
                    cell = self.cells[r][c]
                    #csak azokat a cellákat frissítjük a GUI-n, amelyek eddig üresek voltak
                    if cell.text() == "":
                        cell.setText(str(solver.board[r][c]))
                        
                        #vizuális visszacsatolás: A program által beírt számok betűszínét zöldre állítjuk
                        base_style = cell.styleSheet()
                        new_style = base_style.replace("color: black;", "color: #008800;")
                        cell.setStyleSheet(new_style)
                        
            #eltelt idő kiszámítása milliszekundumban és formázott kiírása
            elapsed_ms = (end_time - start_time) * 1000
            
            #csak akkor dobja fel az ablakot, ha a menüben be van kapcsolva
            if hasattr(self, 'show_metrics_action') and self.show_metrics_action.isChecked():
                QMessageBox.information(
                    self, 
                    "Kész", 
                    f"A Dancing Links (DLX) algoritmus megoldotta a feladványt!\n\nFutási idő: {elapsed_ms:.2f} ms"
                )
        else:
            #ha a megoldó False értékkel tér vissza, a táblán lévő (felhasználó által beírt) adatok ellentmondásosak
            QMessageBox.warning(self, "Hiba", "Ebből az állapotból nem lehet megoldani a Sudokut!")

    #elmenti az aktív cella pozícióját, majd frissíti a kiemelést
    def highlight_cells(self, active_row, active_col):
        self.last_active_row = active_row
        self.last_active_col = active_col
        self.refresh_highlights()

    #újrarajzolja a tábla színeit a kijelölések, a sötét mód és az azonos számok alapján
    def refresh_highlights(self):
        if not hasattr(self, 'game') or not self.game:
            return

        highlight_enabled = self.highlight_action.isChecked()
        is_dark = hasattr(self, 'dark_mode_action') and self.dark_mode_action.isChecked()
        active_text = ""
        active_is_note = False
        
        #aktív fókuszban lévő cella adatainak lekérése
        if self.last_active_row != -1 and self.last_active_col != -1:
            active_cell = self.cells[self.last_active_row][self.last_active_col]
            active_text = active_cell.text()
            active_is_note = active_cell.is_note

        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]

                #ha a cella tippel kapta a számot, írásvédetté tesszük, hogy ne lehessen módosítani
                if getattr(cell, 'is_hinted', False):
                    cell.setReadOnly(True)
                
                #1. alapértelmezett színek beállítása téma és írásvédettség szerint
                if cell.isReadOnly() and not getattr(cell, 'is_hinted', False):
                    bg_color = "#2c2c2c" if is_dark else "#f0f0f0"
                    text_color = "#66b2ff" if is_dark else "#0044cc"
                else:
                    bg_color = "#1e1e1e" if is_dark else "white"
                    
                    #ha tippel kapta a számot, narancssárga a betű, KÜLÖNBEN normál (fehér/fekete)
                    if getattr(cell, 'is_hinted', False):
                        text_color = "transparent" if cell.is_note else "#ff8c00"
                    else:
                        text_color = "transparent" if cell.is_note else ("white" if is_dark else "black")

                #2. sor, oszlop, blokk és azonos számok intelligens kiemelése
                if highlight_enabled and self.last_active_row != -1:
                    is_same_row = (r == self.last_active_row)
                    is_same_col = (c == self.last_active_col)
                    is_same_block = (r // 3 == self.last_active_row // 3 and c // 3 == self.last_active_col // 3)

                    #kapcsolódó sor, oszlop vagy blokk színezése
                    if is_same_row or is_same_col or is_same_block:
                        if cell.isReadOnly():
                            bg_color = "#3d3d3d" if is_dark else "#e2e2e2"
                        else:
                            bg_color = "#2a3f54" if is_dark else "#e6f2ff"
                            
                    #azonos számok sárgás kiemelése a tábla többi részén
                    if (active_text != "" and not active_is_note and not cell.is_note and cell.text() == active_text):
                        bg_color = "#6b5714" if is_dark else "#fff3cd"
                        
                #3. többes kijelölésben lévő cellák egyedi színezése
                if (r, c) in self.selected_cells:
                    bg_color = "#1f4b7a" if is_dark else "#cce5ff" 
                    text_color = "transparent" if cell.is_note else ("#d6a8ff" if is_dark else "purple")
                
                cell.apply_style(bg_color=bg_color, text_color=text_color, is_dark=is_dark)

    #átméretezési esemény kezelése: arányosan skálázza a cellákat, gombokat és betűméreteket
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        #csak akkor számolunk ha a játéktér már látható
        if not hasattr(self, 'game_container') or self.game_container.isHidden():
            return
            
        #szélességi és magassági skálafaktor kiszámítása az 460x660 bázismérethez képest
        scale_w = self.width() / 460.0
        scale_h = self.height() / 660.0
        #a kisebb faktor választása az oldalarányok torzulásmentes megtartásához
        scale = min(scale_w, scale_h)
        
        #fő konténer átméretezése
        self.main_content_widget.setFixedSize(int(440 * scale), int(600 * scale))
        
        #cellák és betűméretek skálázása (minimum 8 pixel)
        cell_size = int(50 * scale)
        main_font_size = max(8, int(18 * scale))
        main_font = QFont("Arial", main_font_size, QFont.Weight.Bold)
        
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                cell.setFixedSize(cell_size, cell_size)
                
                #minden cella megkapja a skálázott betűtípust (kivétel nélkül!)
                cell.setFont(main_font)
                    
        #számbillentyűzet gombjainak skálázása
        btn_size = int(40 * scale)
        btn_font = QFont("Arial", max(8, int(14 * scale)), QFont.Weight.Bold)
        for btn in self.number_buttons.values():
            btn.setFixedSize(btn_size, btn_size)
            btn.setFont(btn_font)
            
        #akciógombok magasságának arányos növelése
        action_h = int(40 * scale)
        for btn in self.findChildren(QPushButton):
            #csak a számgombokat szűrjük ki, így a szünet gomb is nőni fog
            if btn.text() not in [str(i) for i in range(1, 10)]:
                btn.setMinimumHeight(action_h)
    
    #alkalmazás szintű sötét és világos színtéma érvényesítése a felület elemein
    #alkalmazás szintű sötét és világos színtéma érvényesítése a felület elemein
    def apply_theme(self):
        is_dark = self.dark_mode_action.isChecked()
        
        if is_dark:
            #sötét téma CSS stíluslapjai a felület elemeire
            self.setStyleSheet("""
                QMainWindow, QWidget#centralwidget { background-color: #121212; color: #ffffff; }
                
                /* Gombok szögletesítése (border-radius: 0px) */
                QPushButton { background-color: #333333; color: white; border: 1px solid #555; border-radius: 0px; }
                QPushButton:hover { background-color: #444444; }
                QPushButton:disabled { background-color: #222222; color: #666666; border: 1px solid #333; }
                QComboBox { background-color: #333333; color: white; border: 1px solid #555; }
                
                /* Visszajelző ablakok háttere és minden szöveges címke (QLabel) fehérré tétele */
                QMessageBox, QDialog { background-color: #121212; color: white; }
                QLabel { color: white; }
            """)
            
            #számbillentyűzet gombjainak stíluslapja sötét módban (szintén szögletesítve)
            num_style = """
                QPushButton { background-color: #1b3a20; color: white; border: 1px solid #2d5a34; border-radius: 0px; }
                QPushButton:hover { background-color: #26542d; }
                QPushButton:disabled { background-color: #1a1a1a; color: #444444; border: 1px solid #333; }
            """
        else:
            #világos téma alaphelyzetbe állítása (alapértelmezett lekerekítések visszakapcsolása)
            self.setStyleSheet("") 
            num_style = """
                QPushButton { background-color: #e8f5e9; color: black; border: 1px solid #b9cba6; border-radius: 4px; }
                QPushButton:hover { background-color: #c8e6c9; }
                QPushButton:disabled { background-color: #e0e0e0; color: #a0a0a0; border: 1px solid #ccc; }
            """
            
        #számgombok stílusának frissítése a témának megfelelően
        if hasattr(self, 'number_buttons'):
            for btn in self.number_buttons.values():
                btn.setStyleSheet(num_style)
                
        #jegyzet gomb bekapcsolt állapotának stílusozása sötét és világos módban
        if hasattr(self, 'pencil_btn'):
            if is_dark:
                self.pencil_btn.setStyleSheet("QPushButton:checked { background-color: #b29500; color: white; font-weight: normal; border-radius: 0px; }")
            else:
                self.pencil_btn.setStyleSheet("QPushButton:checked { background-color: #ffeb3b; color: black; font-weight: normal; border-radius: 4px; }")

        #az óra felirat színének beállítása (sötétben fehér, világosban fekete)
        if hasattr(self, 'timer_label'):
            if is_dark:
                self.timer_label.setStyleSheet("color: white;")
            else:
                self.timer_label.setStyleSheet("color: black;")

        #megoldó gombok stílusának frissítése a témának megfelelően
        if hasattr(self, 'auto_solve_btn') and hasattr(self, 'dlx_solve_btn'):
            if is_dark:
                self.auto_solve_btn.setStyleSheet("""
                    QPushButton { background-color: #1e4620; color: #d4edda; font-weight: normal; border: 1px solid #2d5a34; border-radius: 0px; } 
                    QPushButton:hover { background-color: #26542d; }
                """)
                self.dlx_solve_btn.setStyleSheet("""
                    QPushButton { background-color: #0a3663; color: #cce5ff; font-weight: normal; border: 1px solid #1c4b7a; border-radius: 0px; } 
                    QPushButton:hover { background-color: #124375; }
                """)
            else:
                self.auto_solve_btn.setStyleSheet("""
                    QPushButton { background-color: #d4edda; color: #155724; font-weight: normal; border: 1px solid #2e7d32; border-radius: 0px; } 
                    QPushButton:hover { background-color: #c3e6cb; }
                """)
                self.dlx_solve_btn.setStyleSheet("""
                    QPushButton { background-color: #cce5ff; color: #004085; font-weight: normal; border: 1px solid #1565c0; border-radius: 0px; } 
                    QPushButton:hover { background-color: #b8daff; }
                """)

        self.refresh_highlights()

    #az eltelt játékidő másodpercenkénti növelése és formázott kiírása (perc:másodperc)
    def update_clock(self):
        self.elapsed_seconds += 1
        #egész osztással a percek, maradékos osztással a másodpercek kiszámítása
        mins = self.elapsed_seconds // 60
        secs = self.elapsed_seconds % 60
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    #a játék szüneteltetésének és folytatásának kezelése, a stopper és a felület elrejtése/felfedése
    def toggle_pause(self):
        if not hasattr(self, 'game') or not self.game:
            return
            
        #szünet állapotának megfordítása (toggle)
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            #stopper leállítása és váltás a szürke szünet képernyőre (1-es réteg)
            self.clock_timer.stop()
            self.board_stack.setCurrentIndex(1)
            self.pause_btn.setText("Folytatás")
            
            #számgombok inaktiválása a szünet ideje alatt
            for btn in self.number_buttons.values():
                btn.setEnabled(False)
        else:
            #stopper újraindítása és visszaváltás a táblára (0-ás réteg)
            self.clock_timer.start(1000)
            self.board_stack.setCurrentIndex(0)
            self.pause_btn.setText("Szünet")
            self.update_numpad_state()

    #inaktiválja azokat a számgombokat, amelyekből mind a 9 a helyes pozícióban van a táblán
    def update_numpad_state(self):
        if not hasattr(self, 'number_buttons'):
            return

        #számláló inicializálása az 1-9 számjegyekhez
        counts = {str(i): 0 for i in range(1, 10)}
        
        #megszámoljuk azokat a végleges számokat, amelyek egyeznek a háttérben lévő helyes megoldással
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                val = cell.text()
                
                if val in counts and not cell.is_note:
                    if hasattr(self, 'correct_solution') and int(val) == self.correct_solution[r][c]:
                        counts[val] += 1

        #ha egy számból mind a 9 helyesen a helyén van, letiltjuk a gombját
        for num, btn in self.number_buttons.items():
            if counts[num] >= 9:
                btn.setEnabled(False)
            else:
                btn.setEnabled(True)

if __name__ == "__main__":
    #az alkalmazás inicializálása és a főablak megjelenítése
    app = QApplication(sys.argv)
    window = SudokuApp()
    window.show()
    sys.exit(app.exec())