import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5 import QtWidgets, QtGui, QtCore


class eic_window(QtWidgets.QDialog):
    def __init__(self, parent, df):
        super().__init__(parent)
        self.setWindowTitle('EIC view window')
        self.df = df
        self.plotted_eic = None
        self.plotted_path = None
        self.item = None
        self.current_flag = False

        self.figure = plt.figure()  # a figure instance to plot on
        self.canvas = FigureCanvas(self.figure)

        self.feature_list = ClickableListWidget()
        self.feature_list = QtWidgets.QTableWidget(self)
        self.feature_list.setRowCount(len(self.df) + 1)  # 包括列名行
        self.feature_list.setColumnCount(len(self.df.columns))
        self.feature_list.setHorizontalHeaderLabels(self.df.columns)
        self.add_dataframe_to_listwidget(df)

        # self.feature_list.connectRightClick(self.file_right_click)
        # self.feature_list.connectDoubleClick(self.file_double_click)
        self._init_ui()  # initialize user interface

        # self.plot_current()  # initial plot

    def _init_ui(self):
        """
        Initialize all buttons and layouts.
        """
        # 字体设置
        font = QtGui.QFont()
        font.setFamily('Arial')
        font.setBold(True)
        font.setPixelSize(15)
        font.setWeight(75)

        # 显示最大化按钮
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMaximizeButtonHint)

        # canvas layout
        widget_canvas = QtWidgets.QWidget()
        toolbar = NavigationToolbar(self.canvas, self)
        canvas_layout = QtWidgets.QVBoxLayout(widget_canvas)
        canvas_layout.addWidget(toolbar)
        canvas_layout.addWidget(self.canvas)

        # feature list layout
        widget_feature = QtWidgets.QWidget()
        feature_label = QtWidgets.QLabel('Feature list：')
        feature_label.setFont(font)
        feature_list_layout = QtWidgets.QVBoxLayout(widget_feature)
        feature_list_layout.addWidget(feature_label)
        feature_list_layout.addWidget(self.feature_list)
        self.feature_list.cellClicked.connect(self.plot_chosen)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(widget_canvas)
        splitter.addWidget(widget_feature)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setStyleSheet(
            """
                QSplitter::handle {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0 black, stop: 0.3 white, stop: 0.5 black, stop: 0.7 white, stop: 1 black
                    );
                }
            """)

        # main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def add_dataframe_to_listwidget(self, dataframe):
        if not isinstance(dataframe, pd.DataFrame):
            raise ValueError("The provided object is not a pandas DataFrame")

        # 设置字体和字体度量
        font = QtGui.QFont("Courier New", 10)  # 使用等宽字体
        self.feature_list.setFont(font)
        font_metrics = QtGui.QFontMetrics(font)

        # 计算每列的最大宽度
        col_widths = []
        for col in dataframe.columns:
            max_width = font_metrics.width(col)
            for item in dataframe[col].astype(str):
                item_width = font_metrics.width(item)
                if item_width > max_width:
                    max_width = item_width
            col_widths.append(max_width)

        # 添加 DataFrame 列名到 QTableWidget 的第一行
        # for col_index, col_name in enumerate(self.df.columns):
        #     item = QtWidgets.QTableWidgetItem(col_name)
        #     item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsSelectable)  # 设为不可编辑和选择
        #     self.feature_list.setItem(0, col_index, item)

        # 将 DataFrame 的每一行添加到 QTableWidget
        for row_index, row in self.df.iterrows():
            for col_index, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)  # 设为不可编辑
                self.feature_list.setItem(row_index, col_index, item)

    def get_chosen(self):
        chosen_item = None
        for item in self.feature_list.selectedItems():
            chosen_item = item
        return chosen_item

    def plot_chosen(self, row, column):
        # 获取对应的 DataFrame 行数据
        row_data = self.df.iloc[row]

        mz = row_data['mz']
        inten_sam = row_data['intensity (Sample)']
        inten_blk = row_data['intensity (Blank)']
        RT = row_data['RT']
        RT_min = RT[0]
        RT_max = RT[-1]
        scan = row_data['scan']
        eic_len = len(scan)
        ext_blk = []
        if isinstance(inten_blk, int):
            for _ in range(eic_len):
                ext_blk.append(0)
        elif len(inten_blk) < eic_len:
            max_pos_eic = np.argmax(inten_sam)
            max_pos_blk = np.argmax(inten_blk)

            # 计算位置偏移量
            offset = max_pos_blk - max_pos_eic

            # 创建新的数组，并初始化为零
            ext_blk = np.zeros(eic_len, dtype=max_pos_blk.dtype)

            if offset >= 0:
                if len(inten_blk) + abs(offset) <= eic_len:
                    ext_blk[:len(inten_blk)] = inten_blk
                else:
                    if max_pos_eic >= eic_len // 2:
                        ext_blk[eic_len - len(inten_blk):] = inten_blk
                    else:
                        ext_blk[:eic_len - len(inten_blk)] = inten_blk
            else:
                if len(inten_blk) + abs(offset) <= eic_len:
                    ext_blk[-offset:-offset + len(inten_blk)] = inten_blk
                else:
                    if max_pos_eic >= eic_len // 2:
                        ext_blk[eic_len - len(inten_blk):] = inten_blk
                    else:
                        ext_blk[:eic_len - len(inten_blk)] = inten_blk
        else:
            ext_blk = inten_blk
        # print(ext_blk)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_ylabel('Intensity')
        ax.ticklabel_format(axis='y', scilimits=(0, 0))  # 使用科学计数法
        ax.plot(scan, inten_sam, color='darkorange', label='sample')
        ax.plot(scan, ext_blk, color='royalblue', label='blank')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))  # x轴只显示整数
        title = f'mz = {mz:.3f}, rt = {RT_min:.1f} - {RT_max:.1f}'
        ax.set_title(title)
        ax.legend(loc='best')
        ax.grid(alpha=0.8)
        self.canvas.draw()
        self.current_flag = False


class FileContextMenu(QtWidgets.QMenu):
    def __init__(self, parent: eic_window):
        super().__init__(parent)

        self.parent = parent
        self.menu = QtWidgets.QMenu(parent)

        self.close = QtWidgets.QAction('Close', parent)
        self.delete = QtWidgets.QAction('Delete', parent)

        self.menu.addAction(self.close)
        self.menu.addAction(self.delete)

        action = self.menu.exec_(QtGui.QCursor.pos())

        if action == self.close:
            self.close_file()
        elif action == self.delete:
            self.delete_file()

    def close_file(self):
        item = self.parent.get_chosen()
        self.parent.close_file(item)

    def delete_file(self):
        item = self.parent.get_chosen()
        self.parent.delete_file(item)


class ClickableListWidget(QtWidgets.QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.double_click = None
        self.right_click = None

    def mousePressEvent(self, QMouseEvent):
        super(QtWidgets.QListWidget, self).mousePressEvent(QMouseEvent)
        if QMouseEvent.button() == QtCore.Qt.RightButton and self.right_click is not None:
            self.right_click()

    def mouseDoubleClickEvent(self, QMouseEvent):
        if self.double_click is not None:
            if QMouseEvent.button() == QtCore.Qt.LeftButton:
                item = self.itemAt(QMouseEvent.pos())
                if item is not None:
                    self.double_click(item)

    def connectDoubleClick(self, method):
        """
        Set a callable object which should be called when a user double-clicks on item
        Parameters
        ----------
        method : callable
            any callable object
        Returns
        -------
        - : None
        """
        self.double_click = method

    def connectRightClick(self, method):
        """
        Set a callable object which should be called when a user double-clicks on item
        Parameters
        ----------
        method : callable
            any callable object
        Returns
        -------
        - : None
        """
        self.right_click = method
