import sys
import numpy as np
from scipy.signal import convolve2d

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QGridLayout
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class GameOfLifeApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Conway Game of Life")
        self.setGeometry(100, 100, 1000, 700)

        # Parámetros iniciales
        self.grid_size = 50
        self.density = 0.20
        self.timer_interval = 200 
        self.is_running = False

        # Tablero inicial
        self.grid = self.create_random_grid(self.grid_size, self.density)

        # Timer para actualizar el juego
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)

        # Interfaz
        self.init_ui()

        # Dibujo inicial
        self.draw_grid()
        self.update_info()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        #Canvas de matplotlib
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.image = None

        # Permitir edición manual del tablero 
        self.canvas.mpl_connect("button_press_event", self.on_canvas_click)

        main_layout.addWidget(self.canvas)

        # Controles
        controls_layout = QGridLayout()

        # Slider tamaño
        self.size_label = QLabel(f"Tamaño grilla: {self.grid_size}")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(10, 100)
        self.size_slider.setValue(self.grid_size)
        self.size_slider.valueChanged.connect(
            lambda value: self.size_label.setText(f"Tamaño grilla: {value}")
        )
        self.size_slider.sliderReleased.connect(self.apply_board_settings)

        # Slider densidad
        self.density_label = QLabel(f"Densidad inicial: {int(self.density * 100)}%")
        self.density_slider = QSlider(Qt.Orientation.Horizontal)
        self.density_slider.setRange(5, 80)
        self.density_slider.setValue(int(self.density * 100))
        self.density_slider.valueChanged.connect(
            lambda value: self.density_label.setText(f"Densidad inicial: {value}%")
        )
        self.density_slider.sliderReleased.connect(self.apply_board_settings)

        # Slider velocidad
        self.speed_label = QLabel(f"Velocidad: {self.timer_interval} ms")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 1000)
        self.speed_slider.setValue(self.timer_interval)
        self.speed_slider.valueChanged.connect(self.change_speed)

        controls_layout.addWidget(self.size_label, 0, 0)
        controls_layout.addWidget(self.size_slider, 0, 1)

        controls_layout.addWidget(self.density_label, 1, 0)
        controls_layout.addWidget(self.density_slider, 1, 1)

        controls_layout.addWidget(self.speed_label, 2, 0)
        controls_layout.addWidget(self.speed_slider, 2, 1)

        main_layout.addLayout(controls_layout)

        # Botones
        buttons_layout = QHBoxLayout()

        self.play_button = QPushButton("Iniciar")
        self.play_button.clicked.connect(self.toggle_simulation)

        self.reset_button = QPushButton("Reinicio aleatorio")
        self.reset_button.clicked.connect(self.reset_random_board)

        self.clear_button = QPushButton("Limpiar tablero")
        self.clear_button.clicked.connect(self.clear_board)

        buttons_layout.addWidget(self.play_button)
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.clear_button)

        main_layout.addLayout(buttons_layout)

        # Información en tiempo real
        info_layout = QHBoxLayout()

        self.live_count_label = QLabel("Células vivas: 0")

        info_layout.addWidget(self.live_count_label)
        info_layout.addStretch()

        main_layout.addLayout(info_layout)

    def create_random_grid(self, size, density):
        return np.random.choice(
            [0, 1],
            size=(size, size),
            p=[1 - density, density]
        ).astype(int)

    def count_neighbors(self, grid):
        kernel = np.array([
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1]
        ])
        return convolve2d(grid, kernel, mode='same', boundary='fill', fillvalue=0)

    def next_generation(self, grid):
        neighbors = self.count_neighbors(grid)

        birth = (neighbors == 3) & (grid == 0)
        survive = ((neighbors == 2) | (neighbors == 3)) & (grid == 1)

        new_grid = np.zeros_like(grid)
        new_grid[birth | survive] = 1

        return new_grid

    def draw_grid(self):
        if self.image is None or self.image.get_array().shape != self.grid.shape:
            self.ax.clear()
            self.image = self.ax.imshow(
                self.grid,
                cmap="Greens",
                interpolation="nearest",
                vmin=0,
                vmax=1
            )
            self.ax.set_title("Conway's Game of Life")
            self.ax.set_xticks([])
            self.ax.set_yticks([])
        else:
            self.image.set_data(self.grid)

        self.canvas.draw_idle()

    def update_simulation(self):
        self.grid = self.next_generation(self.grid)
        self.draw_grid()
        self.update_info()

    def update_info(self):
        live_count = int(np.sum(self.grid))
        self.live_count_label.setText(f"Células vivas: {live_count}")

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
        self.grid_size = self.size_slider.value()
        self.density = self.density_slider.value() / 100
        self.grid = self.create_random_grid(self.grid_size, self.density)
        self.draw_grid()
        self.update_info()

    def clear_board(self):
        self.timer.stop()
        self.is_running = False
        self.play_button.setText("Iniciar")

        self.grid_size = self.size_slider.value()
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=int)

        self.draw_grid()
        self.update_info()

    def apply_board_settings(self):
        self.grid_size = self.size_slider.value()
        self.density = self.density_slider.value() / 100
        self.grid = self.create_random_grid(self.grid_size, self.density)
        self.draw_grid()
        self.update_info()

    def change_speed(self, value):
        self.timer_interval = value
        self.speed_label.setText(f"Velocidad: {value} ms")

        if self.is_running:
            self.timer.start(self.timer_interval)

    def on_canvas_click(self, event):
        # Solo permitir edición manual cuando esté pausado
        if self.is_running:
            return

        if event.inaxes != self.ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        col = int(event.xdata)
        row = int(event.ydata)

        if 0 <= row < self.grid.shape[0] and 0 <= col < self.grid.shape[1]:
            self.grid[row, col] = 1 - self.grid[row, col]
            self.draw_grid()
            self.update_info()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameOfLifeApp()
    window.show()
    sys.exit(app.exec())