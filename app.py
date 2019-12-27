import sys
import random
import logging
import numpy as np

__version__ = '1.0.0'

LOG_FILENAME = './logs/game-of-life.log'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILENAME),
        logging.StreamHandler()
    ]
)

from PySide2 import QtCore, QtWidgets, QtGui

WINDOW_SIZE = 500, 500
WINDOW_POS = 450, 100

class Cell(QtWidgets.QWidget):
    WIDTH = 15
    HEIGHT = 15
    onChangeState = QtCore.Signal(int, int, int)

    def __init__(self, x, y, *args, **kwargs):
        super(Cell, self).__init__(*args, **kwargs)
        self.setFixedSize(QtCore.QSize(self.WIDTH, self.HEIGHT))
        self.setContentsMargins(0, 0, 0, 0)
        self.alive = 0
        self.x = x
        self.y = y

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        r = event.rect()
        if self.alive:
            border, fill = QtCore.Qt.GlobalColor.yellow, QtCore.Qt.GlobalColor.yellow
        else:
            border, fill =  QtCore.Qt.GlobalColor.gray, QtCore.Qt.GlobalColor.lightGray

        p.fillRect(r, QtGui.QBrush(fill))
        pen = QtGui.QPen(border)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawRect(r)

    def changeState(self):
        self.alive = 1 - self.alive
        self.onChangeState.emit(self.x, self.y, self.alive)
        self.update()

    def setState(self, alive):
        self.alive = alive
        self.update()

    def click(self):
        self.changeState()
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.click()

class GameOfLife(object):
    DIM = 35

    def __init__(self):
        self.iteration = 0
        self.population = 0
        self.initState()

    def __repr__(self):
        return repr(self.state)

    def initState(self):
        self.state = np.zeros((self.DIM, self.DIM))

    def setState(self, x, y, v):
        self.state[x,y] = v

    def getNeighborsCount(self):
        left = np.roll(self.state, -1, axis=1)
        top = np.roll(self.state, -1, axis=0)
        right = np.roll(self.state, 1, axis=1)
        bottom = np.roll(self.state, 1, axis=0)
        
        # Adding up all the np arrays to count number of neighbors
        neighbors = left + top + right + bottom + \
            np.roll(right, -1, axis=0) + np.roll(right, 1, axis=0) + \
            np.roll(left, -1, axis=0) + np.roll(left, 1, axis=0)
        return neighbors

    def getNextGeneration(self):
        neighbors = self.getNeighborsCount()
        # Cell becomes alive if it has 3 neighbors and stays alive if it has 2-3 neighbors.
        result = (neighbors == 3) | (self.state.astype(bool) & (neighbors == 2))
        return result.astype(int)

    def evolve(self):
        self.state = self.getNextGeneration()
        self.iteration += 1
        self.population = np.count_nonzero(self.state, (0, 1))

class MainThread(QtCore.QThread):
    evolve = QtCore.Signal()

    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            self.evolve.emit()
            self.sleep(1)

class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.gol = GameOfLife()
        self.gol_thread = MainThread()

        self.initial_state = None
        self.initial_population = 0

        iteration_label = QtWidgets.QLabel('Iteration')
        iteration_label.setAlignment(QtCore.Qt.AlignLeft)
        self.iteration = QtWidgets.QLabel('0')
        self.iteration.setAlignment(QtCore.Qt.AlignRight)

        population_label = QtWidgets.QLabel('Population')
        population_label.setAlignment(QtCore.Qt.AlignLeft)
        self.population = QtWidgets.QLabel('0')
        self.population.setAlignment(QtCore.Qt.AlignRight)

        hb1 = QtWidgets.QHBoxLayout()
        hb1.addWidget(iteration_label)
        hb1.addWidget(self.iteration)
        hb1.setContentsMargins(5, 0, 5, 0)

        hb2 = QtWidgets.QHBoxLayout()
        hb2.addWidget(population_label)
        hb2.addWidget(self.population)
        hb2.setContentsMargins(5, 0, 5, 0)

        self.start_btn = QtWidgets.QPushButton('Start')
        self.stop_btn = QtWidgets.QPushButton('Stop')

        hb3 = QtWidgets.QHBoxLayout()
        hb3.addWidget(self.start_btn)
        hb3.addWidget(self.stop_btn)
        hb3.setContentsMargins(5, 0, 5, 0)
        
        vb = QtWidgets.QVBoxLayout()

        self.grid = QtWidgets.QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(0)
        self.grid.setVerticalSpacing(0)
        self.cells = []

        self.gb = QtWidgets.QGroupBox()
        self.gb.setLayout(self.grid)
        
        vb.addLayout(hb1)
        vb.addLayout(hb2)
        vb.addWidget(self.gb, alignment=QtCore.Qt.AlignCenter)
        vb.addLayout(hb3)
        
        self.gol_thread.evolve.connect(self.iterate)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        
        self.setLayout(vb)
        self._create_cells()

        self.resize(*WINDOW_SIZE)
        self.move(QtCore.QPoint(*WINDOW_POS))
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    
    def _create_cells(self):
        for i in range(0, self.gol.DIM):
            for j in range(0, self.gol.DIM):
                c = Cell(i, j)
                self.grid.addWidget(c, i, j, 1, 1)
                c.onChangeState.connect(self.connOnChangeState)

    def _create_grid(self, content):
        text_box = QtWidgets.QTextEdit(content)
        text_box.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        text_box.setReadOnly(True)
        text_box.setWordWrapMode(QtGui.QTextOption.WordWrap)
        return text_box

    def clear(self):
        self.gol.initState()
        self.gol.iteration = 0
        self.gol.population = 0

        self.redraw()

    def reset(self):
        if self.initial_state is None:
            self.gol.initState()
            self.gol.population = 0
        else:
            self.gol.state = self.initial_state
            self.gol.iteration = 0
            self.gol.population = self.initial_population
        
        self.redraw()
    
    def goto_iteration(self, iteration):
        if self.initial_state is not None:
            self.gol.state = self.initial_state
            self.gol.iteration = 0
            for i in range(0, int(iteration)):
                self.gol.evolve()
        self.redraw()

    def redraw(self):
        state = self.gol.state
        for i in range(0, len(state)):
            for j in range(0, len(state[i])):
                cell = self.grid.itemAtPosition(i, j)
                if cell:
                    cell.widget().setState(state[i,j])
        
        self.iteration.setText(str(self.gol.iteration))
        self.population.setText(str(self.gol.population))

    def iterate(self):
        self.gol.evolve()
        self.redraw()

    def start(self):
        if self.gol.iteration == 0:
            self.initial_state = self.gol.state
            self.initial_population = self.gol.population
        self.gol_thread.start()

    def stop(self):
        self.gol_thread.terminate()

    def connOnChangeState(self, x, y, alive):
        self.gol.setState(x, y, alive)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Game of Life')

        self.widget = MainWidget(self)

        self.menu_bar = QtWidgets.QMenuBar()

        self.game_menu = QtWidgets.QMenu('&Game')
        clear_action = QtWidgets.QAction('&Clear', self)
        clear_action.setShortcut('Ctrl+C')
        clear_action.triggered.connect(self.clear)
        reset_action = QtWidgets.QAction('&Reset', self)
        reset_action.setShortcut('Ctrl+R')
        reset_action.triggered.connect(self.reset)
        goto_iteration = QtWidgets.QAction('&Goto Iteration', self)
        goto_iteration.setShortcut('Ctrl+G')
        goto_iteration.triggered.connect(self.goto_iteration)
        self.game_menu.addAction(clear_action)
        self.game_menu.addAction(reset_action)
        self.game_menu.addAction(goto_iteration)

        self.menu_bar.addMenu(self.game_menu)
        self.setMenuBar(self.menu_bar)

        self.setCentralWidget(self.widget)

    def clear(self):
        self.widget.clear()

    def reset(self):
        self.widget.reset()

    def goto_iteration(self):
        iteration, ok = QtWidgets.QInputDialog().getText(self, 'Goto Iteration', 
            'Goto Iteration:', QtWidgets.QLineEdit.Normal)

        if ok and iteration:
            self.widget.goto_iteration(iteration)

if __name__ == "__main__":
    logging.debug('Start App')
    app = QtWidgets.QApplication([])
    app.setApplicationName('Game of Life')

    window = MainWindow()
    
    window.show()
    window.activateWindow()

    sys.exit(app.exec_())