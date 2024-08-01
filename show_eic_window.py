import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5 import QtWidgets, QtGui, QtCore
from cnn.peak_evaluate import peak_eval
import ast
import csv
import os


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

        # 设置表头可点击，并连接到排序功能
        self.feature_list.setSortingEnabled(True)
        header = self.feature_list.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)  # 可以手动调整列宽
        header.sectionClicked.connect(self.sort_by_column)

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
        feature_list_layout = QtWidgets.QVBoxLayout(widget_feature)
        button_layout = QtWidgets.QHBoxLayout()
        # 创建查找输入框和按钮
        search_widget = QtWidgets.QWidget()
        search_layout = QtWidgets.QHBoxLayout(search_widget)

        self.column_combo_box = QtWidgets.QComboBox()
        self.column_names = ["mz", "RT"]
        self.column_combo_box.addItems(self.column_names)

        self.search_bar = QtWidgets.QLineEdit(self)
        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.clicked.connect(self.search)
        search_layout.addWidget(self.column_combo_box)
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_button)

        feature_label = QtWidgets.QLabel('Feature list：')
        feature_label.setFont(font)
        feature_eval = QtWidgets.QPushButton("Evaluate the peak shape")
        feature_eval.clicked.connect(self.evaluate_df)
        save_score = QtWidgets.QPushButton("Save current table as .csv")
        save_score.clicked.connect(self.save_to_csv)
        button_layout.addWidget(feature_eval)
        button_layout.addWidget(save_score)
        feature_list_layout.addWidget(search_widget)
        feature_list_layout.addWidget(feature_label)
        feature_list_layout.addWidget(self.feature_list)
        feature_list_layout.addLayout(button_layout)
        self.feature_list.cellClicked.connect(self.plot_chosen)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(widget_canvas)
        splitter.addWidget(widget_feature)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
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

    def sort_by_column(self, logicalIndex):
        # 获取当前排序顺序
        order = self.feature_list.horizontalHeader().sortIndicatorOrder()
        self.feature_list.sortItems(logicalIndex, order)

    def search(self):
        search_text = self.search_bar.text()
        search_key = self.column_combo_box.currentText()
        for i in range(self.feature_list.columnCount()):
            if self.feature_list.horizontalHeaderItem(i).text() == search_key:
                col = i
        if len(search_text) > 0:
            for row in range(self.feature_list.rowCount()):
                match = False
                item = self.feature_list.item(row, col)
                if item is not None:
                    if search_text in item.text():
                        match = True
                        item.setBackground(QtGui.QColor('yellow'))  # 高亮匹配项
                        self.feature_list.showRow(row)
                    else:
                        item.setBackground(QtGui.QColor('white'))  # 取消高亮
                        self.feature_list.hideRow(row)
        else:
            for row in range(self.feature_list.rowCount()):
                item = self.feature_list.item(row, col)
                if item is not None:
                    item.setBackground(QtGui.QColor('white'))  # 取消高亮
                    self.feature_list.showRow(row)

    def evaluate_table(self):
        row_count = self.feature_list.rowCount()
        col_count = self.feature_list.columnCount()
        self.feature_list.setColumnCount(col_count + 1)
        self.feature_list.setHorizontalHeaderItem(col_count, QtWidgets.QTableWidgetItem("score"))
        for row in range(row_count):
            scan_item = self.feature_list.item(row, 2)
            inten_item = self.feature_list.item(row, 3)
            if scan_item is not None:
                scan_txt = str(scan_item.text())
                scan_arr = ast.literal_eval(scan_txt)

                inten_txt = str(inten_item.text())
                inten_arr = ast.literal_eval(inten_txt)
                # min_val = min(inten_arr)
                # normalized_y = [x - min_val for x in inten_arr]  # 使最小值为0

                # scan_min = scan_arr[0]
                # scan_max = scan_arr[-1]
                diff = np.diff(scan_arr)  # 计算相邻元素的差值
                break_point = np.where(diff != 1)[0] + 1  # 找到差值不为1的索引，即不连续点的位置。+1是因为diff结果的长度比data短1
                missing_point = diff[break_point - 1] - 1
                missing_point = missing_point.astype(int)
                offset = 0
                for index, count in zip(break_point, missing_point):
                    for _ in range(count):
                        # scan_arr = np.insert(scan_arr, index + offset, 0)
                        offset += 1
                        inten_arr = np.insert(inten_arr, index + offset - 1, 0)
                # scan_arr = np.arange(scan_min, scan_max + 1)

                intensity = np.pad(inten_arr, (3, 3), 'constant', constant_values=(0, 0))

                score = peak_eval(orin_inten=intensity)
                self.feature_list.setItem(row, col_count, QtWidgets.QTableWidgetItem(str(score)))

    def evaluate_df(self):
        score_arr = []
        col_count = self.feature_list.columnCount()
        self.feature_list.setColumnCount(col_count + 1)
        self.feature_list.setHorizontalHeaderItem(col_count, QtWidgets.QTableWidgetItem("score"))
        for row_index, row in self.df.iterrows():
            scan = self.df['scan'][row_index]
            inten = self.df['intensity'][row_index]

            # min_val = min(inten_arr)
            # normalized_y = [x - min_val for x in inten_arr]  # 使最小值为0

            # scan_min = scan_arr[0]
            # scan_max = scan_arr[-1]
            diff = np.diff(scan)  # 计算相邻元素的差值
            break_point = np.where(diff != 1)[0] + 1  # 找到差值不为1的索引，即不连续点的位置。+1是因为diff结果的长度比data短1
            missing_point = diff[break_point - 1] - 1
            missing_point = missing_point.astype(int)
            offset = 0
            for index, count in zip(break_point, missing_point):
                for _ in range(count):
                    # scan_arr = np.insert(scan_arr, index + offset, 0)
                    offset += 1
                    inten = np.insert(inten, index + offset - 1, 0)
            # scan_arr = np.arange(scan_min, scan_max + 1)

            intensity = np.pad(inten, (3, 3), 'constant', constant_values=(0, 0))

            score = peak_eval(orin_inten=intensity)
            score_arr.append(score)

        self.df['score'] = score_arr
        for row_index, row in self.df.iterrows():
            for col_index, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)  # 设为不可编辑
                self.feature_list.setItem(row_index, col_index, item)

    def save_to_csv(self):
        suffix_start = 0
        name = 'score'
        while True:
            file_name = f"{name}-{suffix_start:02d}.csv"
            if not os.path.exists(file_name):
                self.df.to_csv(file_name, index=False)
                break
            else:
                suffix_start += 1
        msg = QtWidgets.QMessageBox(self)
        msg.setText("Result has been saved as " + file_name + " !")
        msg.exec_()
        # path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', '', 'CSV(*.csv)')
        # if path:
        #     with open(path, mode='w', newline='') as file:
        #         writer = csv.writer(file)
        #         # Write header
        #         header = [self.feature_list.horizontalHeaderItem(i).text() for i in range(self.feature_list.columnCount())]
        #         writer.writerow(header)
        #         # Write data
        #         for row in range(self.feature_list.rowCount()):
        #             row_data = []
        #             for col in range(self.feature_list.columnCount()):
        #                 item = self.feature_list.item(row, col)
        #                 if item is not None:
        #                     row_data.append(item.text())
        #                 else:
        #                     row_data.append('')
        #             writer.writerow(row_data)

    def get_chosen(self):
        chosen_item = None
        for item in self.feature_list.selectedItems():
            chosen_item = item
        return chosen_item

    def plot_chosen(self, row, column):
        try:
            # 获取对应的 DataFrame 行数据
            label_item = self.feature_list.item(row, 0)
            label_value = label_item.text() if label_item else ''

            row_data = self.df[self.df['label'] == int(label_value)]

            mz = row_data['mz'].iloc[0]
            intensity = row_data['intensity'].iloc[0]
            RT = row_data['RT'].iloc[0]
            RT_min = RT[0]
            RT_max = RT[-1]
            scan = row_data['scan'].iloc[0]
            scan_min = scan[0]
            scan_max = scan[-1]

            diff = np.diff(scan)  # 计算相邻元素的差值
            break_point = np.where(diff != 1)[0] + 1  # 找到差值不为1的索引，即不连续点的位置。+1是因为diff结果的长度比data短1
            missing_point = diff[break_point - 1] - 1
            missing_point = missing_point.astype(int)
            offset = 0
            for index, count in zip(break_point, missing_point):
                for _ in range(count):
                    scan = np.insert(scan, index + offset, 0)
                    offset += 1
                    intensity = np.insert(intensity, index + offset - 1, 0)
            scan = np.arange(scan_min, scan_max + 1)

            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_ylabel('Intensity')
            ax.ticklabel_format(axis='y', scilimits=(0, 0))  # 使用科学计数法
            ax.plot(scan, intensity)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))  # x轴只显示整数
            title = f'mz = {mz:.3f}, rt = {RT_min:.1f} - {RT_max:.1f}'
            ax.set_title(title)
            # ax.legend(loc='best')
            ax.grid(alpha=0.8)
            self.canvas.draw()
            self.current_flag = False
        except Exception:
            pass


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
