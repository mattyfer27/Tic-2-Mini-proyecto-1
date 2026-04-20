import sys
import serial 
import numpy as np
from dataclasses import dataclass
 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QGridLayout
)
from PyQt6.QtWidgets import QMessageBox 
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap
 
 
##### Entidades
 
@dataclass
class Entity:
    kind: str         
    subtype: str
    health: int
    energy: int
    max_energy: int
    age: int = 0     
 
    def clone(self):
        return Entity(
            self.kind,
            self.subtype,
            self.health,
            self.energy,
            self.max_energy,
            self.age
        )
 
 
def lanzaguizantes():
    return Entity("planta", "lanzaguisantes", 100, 0, 5)
 
 
def metralladora():
    return Entity("planta", "guisantralladora", 250, 5, 5)
 
 
def hongo_noche():
    return Entity("planta", "seta desesporada", 100, 0, 5)
 
 
def gasoseta():
    return Entity("planta", "gasoseta", 250, 5, 5)
 
 
def zombie():
    return Entity("zombie", "zombie normal", 100, 0, 10)
 
 
def zombistein():
    return Entity("zombie", "zombistein", 300, 0, 10)
 
 
def soles():
    return Entity("sol", "sol", 1, 0, 0, 0)
 
 
### Juego
 
class PlantasvsZombies(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Plantas vs Zombies")
        self.setGeometry(100, 100, 1150, 800)

        self.rng = np.random.default_rng()

        self.grid_size = 35
        self.timer_interval = 250
        self.is_running = False
        self.turn = 0

        # Ciclo día y noche
        self.day_night_period = 8
        self.current_phase_text = "Día"

        # Tamaño vecindad
        self.neighborhood_size = 3

        # Estado del juego
        self.game_over = False

        # Arduino
        self.serial_port_name = "COM6"   # cámbialo por el puerto a usar
        self.serial_baudrate = 9600
        self.arduino = None

        # Tablero inicial
        self.grid = self.create_random_board(self.grid_size)

        # Timer del juego
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)

        # Timer para leer Arduino
        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self.read_arduino_messages)

        self.init_ui()
        self.connect_arduino()

        # Empezar a escuchar Arduino
        self.serial_timer.start(50)

        self.draw_grid()
        self.update_info()
        self.send_state_to_arduino()
        self.check_game_over()
        
    ### Interfaz del juego
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
 
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
 
        # Canvas de matplotlib
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.image = None
 
        self.canvas.mpl_connect("button_press_event", self.on_canvas_click)
 
        main_layout.addWidget(self.canvas)
 
        # Controles
        controls_layout = QGridLayout()
 
        self.size_label = QLabel(f"Tamaño grilla: {self.grid_size}")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(10, 60)
        self.size_slider.setValue(self.grid_size)
        self.size_slider.valueChanged.connect(
            lambda value: self.size_label.setText(f"Tamaño grilla: {value}")
        )
 
        self.speed_label = QLabel(f"Velocidad: {self.timer_interval} ms")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 1000)
        self.speed_slider.setValue(self.timer_interval)
        self.speed_slider.valueChanged.connect(self.change_speed)
 
        controls_layout.addWidget(self.size_label, 0, 0)
        controls_layout.addWidget(self.size_slider, 0, 1)
        controls_layout.addWidget(self.speed_label, 1, 0)
        controls_layout.addWidget(self.speed_slider, 1, 1)
 
        main_layout.addLayout(controls_layout)
 
        # Botones
        buttons_layout = QHBoxLayout()
 
        self.play_button = QPushButton("Iniciar")
        self.play_button.clicked.connect(self.toggle_simulation)
 
        self.reset_button = QPushButton("Reiniciar")
        self.reset_button.clicked.connect(self.reset_random_board)
 
        self.clear_button = QPushButton("Limpiar tablero")
        self.clear_button.clicked.connect(self.clear_board)
 
        buttons_layout.addWidget(self.play_button)
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.clear_button)
 
        main_layout.addLayout(buttons_layout)
 
        # Info
        info_layout = QVBoxLayout()
 
        self.turn_label = QLabel("Turno: 0")
        self.phase_label = QLabel("Fase: Día")
        self.counts_label = QLabel("Plantas: 0 | Zombies: 0 | Soles: 0")
        
        
        self.winner_label = QLabel("")
        self.winner_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
        info_layout.addWidget(self.winner_label)
        
        
        legend_label = QLabel(
            "Colores: blanco = vacío, amarillo = sol, verde = lanzaguisantes, "
            "verde oscuro = guisantralladora, morado = seta desesporada, "
            "violeta oscuro = gasoseta, rojo = zombie normal, negro = zombistein"
        )
 
        info_layout.addWidget(self.turn_label) 
        info_layout.addWidget(self.phase_label)
        info_layout.addWidget(self.counts_label)
        info_layout.addWidget(legend_label)
 
        main_layout.addLayout(info_layout)
 
  
    ### Tablero
     
    def create_random_board(self, size):

        board = [[None for _ in range(size)] for _ in range(size)]
 
        values = self.rng.choice(
            [0, 1, 2, 3],
            size=(size, size),
            p=[0.10, 0.20, 0.50, 0.20] # Probabilidad de que aparezcan siendo 0 vacío, 1 sol, 2 planta, 3 zombie
         )
 
        for r in range(size):
            for c in range(size):
                v = values[r, c]
                if v == 1:
                    board[r][c] = soles()
                elif v == 2:
                    board[r][c] = lanzaguizantes()
                elif v == 3:
                    board[r][c] = zombie()
 
        return board
 
    def clone_grid(self, grid):
        new_grid = []
        for row in grid:
            new_row = []
            for cell in row:
                new_row.append(None if cell is None else cell.clone())
            new_grid.append(new_row)
        return new_grid
 
    def is_night(self):
        return (self.turn // self.day_night_period) % 2 == 1
 
    def posicion_vecinos(self, row, col):
        radius = self.neighborhood_size // 2
        positions = []
 
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if dr == 0 and dc == 0:
                    continue
 
                nr = row + dr
                nc = col + dc
 
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    positions.append((nr, nc))
 
        return positions
 
    def count_neighbor_suns(self, grid, row, col):
        count = 0
        for nr, nc in self.posicion_vecinos(row, col):
            cell = grid[nr][nc]
            if cell is not None and cell.kind == "sol":
                count += 1
        return count
 
    ### Parte visual
 
    def build_display_matrix(self):

        matrix = np.zeros((self.grid_size, self.grid_size), dtype=int)
 
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                cell = self.grid[r][c]
 
                if cell is None:
                    matrix[r, c] = 0
                elif cell.kind == "sol":
                    matrix[r, c] = 1
                elif cell.kind == "planta":
                    if cell.subtype == "lanzaguisantes":
                        matrix[r, c] = 2
                    elif cell.subtype == "guisantralladora":
                        matrix[r, c] = 4
                    elif cell.subtype == "seta desesporada":
                        matrix[r, c] = 5
                    elif cell.subtype == "gasoseta":
                        matrix[r, c] = 6
                elif cell.kind == "zombie":
                    if cell.subtype == "zombie normal":
                        matrix[r, c] = 3
                    elif cell.subtype == "zombistein":
                        matrix[r, c] = 7
 
        return matrix
 
    def draw_grid(self):
        matrix = self.build_display_matrix()
 
        cmap = ListedColormap([
            "#ffffff",  # vacío
            "#f1c40f",  # sol
            "#2ecc71",  # lanzaguisantes
            "#e74c3c",  # zombie normal
            "#145a32",  # guisantralladora
            "#8e44ad",  # seta desesporada
            "#4a235a",  # gasoseta
            "#000000"   # zombistein
        ])
 
        if self.image is None or self.image.get_array().shape != matrix.shape:
            self.ax.clear()
            self.image = self.ax.imshow(
                matrix,
                cmap=cmap,
                interpolation="nearest",
                vmin=0,
                vmax=7
            )
            self.ax.set_title("Plants vs Zombies")
            self.ax.set_xticks([])
            self.ax.set_yticks([])
        else:
            self.image.set_data(matrix)
 
        self.canvas.draw_idle()
 
    def update_info(self):
        plants = 0
        zombies = 0
        soles = 0

        for row in self.grid:
            for cell in row:
                if cell is None:
                    continue
                if cell.kind == "planta":
                    plants += 1
                elif cell.kind == "zombie":
                    zombies += 1
                elif cell.kind == "sol":
                    soles += 1

        self.turn_label.setText(f"Turno: {self.turn}")
        self.phase_label.setText(f"Fase: {self.current_phase_text}")
        self.counts_label.setText(
            f"Plantas: {plants} | Zombies: {zombies} | Soles: {soles}"
        )
        
    ### Detalles
 
    def apply_end_of_turn_spawns(self, grid, night_mode):
        final_grid = self.clone_grid(grid)
 
        # 30% de las celdas vacías se convierten en soles
     
        empty_positions = [
            (r, c)
            for r in range(self.grid_size)
            for c in range(self.grid_size)
            if final_grid[r][c] is None
        ]
 
        if empty_positions:
            num_suns = int(round(0.30 * len(empty_positions)))
            num_suns = min(num_suns, len(empty_positions))
 
            if num_suns > 0:
                selected_indices = self.rng.choice(
                    len(empty_positions),
                    size=num_suns,
                    replace=False
                )
 
                for idx in np.atleast_1d(selected_indices):
                    r, c = empty_positions[int(idx)]
                    final_grid[r][c] = soles()

        # Evaluar las celdas que siguen vacías
   
        snapshot = self.clone_grid(final_grid)
 
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if snapshot[r][c] is not None:
                    continue
 
                sun_count = self.count_neighbor_suns(snapshot, r, c)
 
                # Regla de dia
                if not night_mode:
                    if sun_count >= 3:
                        final_grid[r][c] = lanzaguizantes()
 
                # Regla de noche, probabilidades de aparicion
                else:
                    if 1 <= sun_count <= 2:
                        p = self.rng.random()
 
                        if p < 0.20:
                            final_grid[r][c] = hongo_noche()
                        elif p < 0.40:
                            final_grid[r][c] = zombie()
                        # 60% restante queda vacía
 
        return final_grid
 
    ### Simulacion
 
    def simulate_step(self):
        old_grid = self.clone_grid(self.grid)
        new_grid = self.clone_grid(self.grid)
 
        soles_consumidos = set()
        night_now = self.is_night()
        self.current_phase_text = "Noche" if night_now else "Día"
 
        ### los soles desaparecen en 5 turnos
        
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                cell = new_grid[r][c]
                if cell is not None and cell.kind == "sol":
                    cell.age += 1
                    if cell.age >= 5:
                        new_grid[r][c] = None
 
        ### Plantas reciben daño, ganan energia por soles y evolucionan

        plantas_debilitadas = []
 
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                old_cell = old_grid[r][c]
 
                if old_cell is None or old_cell.kind != "planta":
                    continue
 
                vecinos = self.posicion_vecinos(r, c)
 
                posicion_zombies = []
                posicion_soles = []
 
                for nr, nc in vecinos:
                    vecino = old_grid[nr][nc]
                    if vecino is None:
                        continue
                    if vecino.kind == "zombie":
                        posicion_zombies.append((nr, nc))
                    elif vecino.kind == "sol":
                        posicion_soles.append((nr, nc))
 
                planta_actual = new_grid[r][c]
                if planta_actual is None or planta_actual.kind != "planta":
                    continue
 
                cantidad_zombies = len(posicion_zombies)
                daño_zombies = 15 if cantidad_zombies >= 3 else 10
                planta_actual.health -= cantidad_zombies * daño_zombies
 
                if planta_actual.health <= 0:
                    new_grid[r][c] = None
                    plantas_debilitadas.append((r, c, posicion_zombies))
                    continue
 
                for sr, sc in posicion_soles:
                    if (sr, sc) in soles_consumidos:
                        continue
 
                    sun_cell = new_grid[sr][sc]
                    if sun_cell is None or sun_cell.kind != "sol":
                        continue
 
                    if planta_actual.energy < planta_actual.max_energy:
                        planta_actual.energy += 1
                        soles_consumidos.add((sr, sc))
 
                if planta_actual.subtype == "lanzaguisantes" and planta_actual.energy >= planta_actual.max_energy:
                    new_grid[r][c] = metralladora()
 
                elif planta_actual.subtype == "seta desesporada" and planta_actual.energy >= planta_actual.max_energy:
                    new_grid[r][c] = gasoseta()
 
        
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                old_cell = old_grid[r][c]
 
                if old_cell is None or old_cell.kind != "zombie":
                    continue
 
                vecinos = self.posicion_vecinos(r, c)
 
                posicion_plantas = []
                for nr, nc in vecinos:
                    vecino = old_grid[nr][nc]
                    if vecino is not None and vecino.kind == "planta":
                        posicion_plantas.append((nr, nc))
 
                zombie_actual = new_grid[r][c]
                if zombie_actual is None or zombie_actual.kind != "zombie":
                    continue
 
                contador_planta = len(posicion_plantas)
                damage_per_plant = 10 if contador_planta >= 3 else 5
                zombie_actual.health -= contador_planta * damage_per_plant
 
                if zombie_actual.health <= 0:
                    new_grid[r][c] = None
 
        ### zombies ganan energia para evolucionar

        energia_zombies = {}
 
        for _, _, posicion_zombies in plantas_debilitadas:
            valid_zombies = []
            for zr, zc in posicion_zombies:
                zombie = new_grid[zr][zc]
                if zombie is not None and zombie.kind == "zombie":
                    valid_zombies.append((zr, zc))
 
            if valid_zombies:
                killer_index = self.rng.integers(0, len(valid_zombies))
                killer_pos = valid_zombies[killer_index]
                energia_zombies[killer_pos] = energia_zombies.get(killer_pos, 0) + 1
 
        for (zr, zc), gain in energia_zombies.items():
            zombie = new_grid[zr][zc]
            if zombie is None or zombie.kind != "zombie":
                continue
 
            zombie.energy = min(zombie.max_energy, zombie.energy + gain)
 
            if zombie.subtype == "zombie normal" and zombie.energy >= zombie.max_energy:
                new_grid[zr][zc] = zombistein()
 
        ### guisantemetralleta y gasoseta

        daño_extra_zombies = {}
 
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                cell = new_grid[r][c]
 
                if cell is None or cell.kind != "planta":
                    continue
 
                if cell.subtype not in ("guisantralladora", "gasoseta"):
                    continue
 
                vecinos = self.posicion_vecinos(r, c)
                posicion_zombies = []
 
                for nr, nc in vecinos:
                    objetivo = new_grid[nr][nc]
                    if objetivo is not None and objetivo.kind == "zombie":
                        posicion_zombies.append((nr, nc))
 
                self.rng.shuffle(posicion_zombies)
 
                for zr, zc in posicion_zombies[:3]:
                    daño_extra_zombies[(zr, zc)] = daño_extra_zombies.get((zr, zc), 0) + 20
 
        for (zr, zc), daño in daño_extra_zombies.items():
            zombie = new_grid[zr][zc]
            if zombie is None or zombie.kind != "zombie":
                continue
 
            zombie.health -= daño
            if zombie.health <= 0:
                new_grid[zr][zc] = None
 
        ### zombistein daño a plantas

        daño_extra_plantas = {}
        ataques_zombies = {}
 
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                cell = new_grid[r][c]
 
                if cell is None or cell.kind != "zombie" or cell.subtype != "zombistein":
                    continue
 
                vecinos = self.posicion_vecinos(r, c)
 
                for nr, nc in vecinos:
                    objetivo = new_grid[nr][nc]
                    if objetivo is not None and objetivo.kind == "planta":
                        daño_extra_plantas[(nr, nc)] = daño_extra_plantas.get((nr, nc), 0) + 30
                        ataques_zombies.setdefault((nr, nc), []).append((r, c))
 
        zombistein_energy_gain = {}
 
        for (pr, pc), daño in daño_extra_plantas.items():
            planta = new_grid[pr][pc]
            if planta is None or planta.kind != "planta":
                continue
 
            planta.health -= daño
            if planta.health <= 0:
                new_grid[pr][pc] = None
 
                valid_attackers = []
                for zr, zc in ataques_zombies.get((pr, pc), []):
                    zombie = new_grid[zr][zc]
                    if zombie is not None and zombie.kind == "zombie":
                        valid_attackers.append((zr, zc))
 
                if valid_attackers:
                    killer_index = self.rng.integers(0, len(valid_attackers))
                    killer_pos = valid_attackers[killer_index]
                    zombistein_energy_gain[killer_pos] = zombistein_energy_gain.get(killer_pos, 0) + 1
 
        for (zr, zc), gain in zombistein_energy_gain.items():
            zombie = new_grid[zr][zc]
            if zombie is not None and zombie.kind == "zombie":
                zombie.energy = min(zombie.max_energy, zombie.energy + gain)
 
        ### se consumen los soles
        
        for sr, sc in soles_consumidos:
            if new_grid[sr][sc] is not None and new_grid[sr][sc].kind == "sol":
                new_grid[sr][sc] = None
 
        ### aparciciones final del turno

        new_grid = self.apply_end_of_turn_spawns(new_grid, night_now)
 
        self.grid = new_grid
        self.turn += 1
 
    ### controles
    
    def update_simulation(self):
        if self.game_over:
            return

        self.simulate_step()
        self.draw_grid()
        self.update_info()
        self.send_state_to_arduino()
        self.check_game_over()
 
    def toggle_simulation(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.play_button.setText("Reanudar")
        else:
            self.timer.start(self.timer_interval)
            self.is_running = True
            self.play_button.setText("Pausar")
 
    def reset_random_board(self):
        self.timer.stop()
        self.is_running = False
        self.play_button.setText("Iniciar")

        self.grid_size = self.size_slider.value()
        self.turn = 0
        self.current_phase_text = "Día"
        self.grid = self.create_random_board(self.grid_size)

        self.game_over = False
        self.winner_label.setText("")

        self.draw_grid()
        self.update_info()
        self.send_state_to_arduino()
        self.check_game_over()

    def clear_board(self):
        self.timer.stop()
        self.is_running = False
        self.play_button.setText("Iniciar")

        self.grid_size = self.size_slider.value()
        self.turn = 0
        self.current_phase_text = "Día"
        self.grid = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]

        self.game_over = False
        self.winner_label.setText("")

        self.draw_grid()
        self.update_info()
        self.send_state_to_arduino()
        self.check_game_over()
        
    def change_speed(self, value):
        self.timer_interval = value
        self.speed_label.setText(f"Velocidad: {value} ms")
 
        if self.is_running:
            self.timer.start(self.timer_interval)
    
    def on_canvas_click(self, event):
        if self.is_running:
            return

        if event.inaxes != self.ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        col = int(event.xdata)
        row = int(event.ydata)

        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return

        cell = self.grid[row][col]

        if cell is None:
            self.grid[row][col] = lanzaguizantes()
        elif cell.kind == "planta":
            self.grid[row][col] = zombie()
        elif cell.kind == "zombie":
            self.grid[row][col] = soles()
        elif cell.kind == "sol":
            self.grid[row][col] = None

        self.draw_grid()
        self.update_info()
        self.send_state_to_arduino()
        self.check_game_over()
    
    def connect_arduino(self):
        
        try:
            self.arduino = serial.Serial(self.serial_port_name, self.serial_baudrate, timeout=0.01)
        except Exception as e:
            self.arduino = None
            print(f"No se pudo conectar con Arduino: {e}")

    ### Contar datos y mandarlos al arduino
    
    def contar_bandos(self):
        plantas = 0
        zombies = 0

        for row in self.grid:
            for cell in row:
                if cell is None:
                    continue
                if cell.kind == "planta":
                    plantas += 1
                elif cell.kind == "zombie":
                    zombies += 1
        return plantas, zombies
        
    ### Manda el estado actual al arduino
    
    def send_state_to_arduino(self):
        if self.arduino is None or not self.arduino.is_open:
            return

        plantas, zombies = self.contar_bandos()

        plantas = min(plantas, 999)
        zombies = min(zombies, 999)

        mensaje = f"A-P{plantas:03d}-Z{zombies:03d}\n"

        try:
            self.arduino.write(mensaje.encode("utf-8"))
        except Exception as e:
            print(f"Error enviando a Arduino: {e}")    
 
    ### Lee la informacion desde el arduino
    
    def read_arduino_messages(self):
        if self.arduino is None or not self.arduino.is_open:
            return

        try:
            while self.arduino.in_waiting:
                line = self.arduino.readline().decode("utf-8", errors="ignore").strip()

                if line == "B-1":
                    self.bomba_solar()

                elif line == "B-2":
                    self.venganza_dr_zombie()

        except Exception as e:
            print(f"Error leyendo desde Arduino: {e}")    
            
    ### Zona 21x21
    
    def obtener_zona_aleatoria(self, lado=21):
        if self.grid_size <= lado:
            return 0, self.grid_size - 1, 0, self.grid_size - 1

        max_fila = self.grid_size - lado
        max_col = self.grid_size - lado

        fila_inicio = int(self.rng.integers(0, max_fila + 1))
        col_inicio = int(self.rng.integers(0, max_col + 1))

        fila_fin = fila_inicio + lado - 1
        col_fin = col_inicio + lado - 1

        return fila_inicio, fila_fin, col_inicio, col_fin


    ### Bomba solar
    
    def bomba_solar(self):
        if self.game_over:
            return

        soles_consumidos = set()

        for _ in range(3):
            f0, f1, c0, c1 = self.obtener_zona_aleatoria(21)

            for r in range(f0, f1 + 1):
                for c in range(c0, c1 + 1):
                    cell = self.grid[r][c]

                    if cell is None or cell.kind != "planta":
                        continue

                    vecinos = self.posicion_vecinos(r, c)

                    for nr, nc in vecinos:
                        if not (f0 <= nr <= f1 and c0 <= nc <= c1):
                            continue

                        vecino = self.grid[nr][nc]

                        if vecino is None or vecino.kind != "sol":
                            continue

                        if (nr, nc) in soles_consumidos:
                            continue

                        cell.energy = min(cell.max_energy, cell.energy + 3)
                        soles_consumidos.add((nr, nc))

                    if cell.subtype == "lanzaguisantes" and cell.energy >= cell.max_energy:
                        self.grid[r][c] = metralladora()

                    elif cell.subtype == "seta desesporada" and cell.energy >= cell.max_energy:
                        self.grid[r][c] = gasoseta()

        for sr, sc in soles_consumidos:
            if self.grid[sr][sc] is not None and self.grid[sr][sc].kind == "sol":
                self.grid[sr][sc] = None

        self.draw_grid()
        self.update_info()
        self.send_state_to_arduino()
        self.check_game_over()    

    ### Venganza doc Z

    def venganza_dr_zombie(self):
        if self.game_over:
            return

        f0, f1, c0, c1 = self.obtener_zona_aleatoria(21)

        for r in range(f0, f1 + 1):
            for c in range(c0, c1 + 1):
                self.grid[r][c] = None

        self.draw_grid()
        self.update_info()
        self.send_state_to_arduino()
        self.check_game_over()    


    ### Condiciones de victoria
    
    def check_game_over(self):
        plantas, zombies = self.contar_bandos()

        ganador = None

        if plantas > 0 and zombies == 0:
            ganador = "Plantas"
        elif zombies > 0 and plantas == 0:
            ganador = "Zombies"

        if ganador is None:
            self.game_over = False
            self.winner_label.setText("")
            return

        self.game_over = True
        self.timer.stop()
        self.is_running = False
        self.play_button.setText("Iniciar")

        QApplication.beep()
        self.winner_label.setText(f"Fin del juego: ganan los {ganador}")
        QMessageBox.information(self, "Fin del juego", f"Fin del juego: ganan los {ganador}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlantasvsZombies()
    window.show()
    sys.exit(app.exec())