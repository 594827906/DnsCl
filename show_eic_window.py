import os
import json
import pymzml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5 import QtWidgets, QtGui, QtCore
from utils.threading import Worker
from view_from_processed import eic_from_csv


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
        self.add_dataframe_to_listwidget(df)

        # self.feature_list.connectRightClick(self.file_right_click)
        self.feature_list.connectDoubleClick(self.file_double_click)
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
        next_button = QtWidgets.QPushButton('Next')
        next_button.setFont(font)
        next_button.clicked.connect(self.next)
        feature_list_layout = QtWidgets.QVBoxLayout(widget_feature)
        feature_list_layout.addWidget(feature_label)
        feature_list_layout.addWidget(self.feature_list)
        feature_list_layout.addWidget(next_button)

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

        # 将 DataFrame 的每一行添加到 QListWidget
        for index, row in dataframe.iterrows():
            item_texts = []
            for i, item in enumerate(row):
                item_text = str(item).ljust(col_widths[i] // font_metrics.averageCharWidth() + 2)
                item_texts.append(item_text)
            item_text = ', '.join(item_texts)
            # list_item = QtWidgets.QListWidgetItem(item_text)
            self.feature_list.addItem(f"{index}: {item_text}")

    # Auxiliary methods
    def file_right_click(self):
        FileContextMenu(self)

    def file_double_click(self, item):
        self.item = item
        self.plot_chosen()

    def get_chosen(self):
        chosen_item = None
        for item in self.feature_list.selectedItems():
            chosen_item = item
        return chosen_item

    def next(self):
        if self.current_flag:
            self.current_flag = False
            self.plot_current()
        else:
            self.item.setSelected(False)
            index = min(self.feature_list.row(self.item) + 1, self.feature_list.count() - 1)
            self.item = self.feature_list.item(index)
            self.item.setSelected(True)
            self.plot_chosen()

    # def press_plot_chosen(self):
    #     try:
    #         self.plotted_item = self.get_chosen()
    #         if self.plotted_item is None:
    #             raise ValueError
    #         self.plot_chosen()
    #     except ValueError:
    #         # popup window with exception
    #         msg = QtWidgets.QMessageBox(self)
    #         msg.setText('Choose a ROI to plot from the list!')
    #         msg.setIcon(QtWidgets.QMessageBox.Warning)
    #         msg.exec_()

    # Visualization
    # def plot_current(self):
    #     try:
    #         if not self.current_flag:
    #             self.current_flag = True
    #             self.current_description = self.description
    #             self.plotted_roi = self.ROIs[self.file_suffix]
    #             filename = f'{self.file_prefix}_{self.file_suffix}.json'
    #             self.plotted_path = os.path.join(self.folder, filename)
    #
    #             self.figure.clear()
    #             ax = self.figure.add_subplot(111)
    #             ax.plot(self.plotted_roi.i, label=filename)
    #             title = f'mz = {self.plotted_roi.mzmean:.3f}, ' \
    #                     f'rt = {self.plotted_roi.rt[0]:.1f} - {self.plotted_roi.rt[1]:.1f}'
    #             ax.legend(loc='best')
    #             ax.set_title(title)
    #             self.canvas.draw()  # refresh canvas
    #     except IndexError:
    #         msg = QtWidgets.QMessageBox(self)
    #         msg.setText('已标注完所有ROI')
    #         msg.setIcon(QtWidgets.QMessageBox.Warning)
    #         msg.exec_()

    def plot_chosen(self):  # TODO: debugging...
        item_text = self.item.text()
        row_index = int(item_text.split(':')[0])
        row_data = self.df.iloc[row_index]
        if not row_data.empty:
            row_str = '\n'.join([f'{col}: {row_data[col]}' for col in row_data.index])
            print(row_str)
        else:
            print('empty')

        # self.plotted_eic = eic_from_csv(filename, filename, 'plotting EIC...')
        # self.figure.clear()
        # ax = self.figure.add_subplot(111)
        # ax.plot(self.plotted_eic.i, label=filename)
        # title = f'mz = {self.plotted_eic.mzmean:.3f}, ' \
        #         f'rt = {self.plotted_eic.rt[0]:.1f} - {self.plotted_eic.rt[1]:.1f}'
        #
        # ax.set_title(title)
        # ax.legend(loc='best')
        # self.canvas.draw()
        # self.current_flag = False

    # def plot_preview(self, borders):
    #     filename = os.path.basename(self.plotted_path)
    #     self.figure.clear()
    #     ax = self.figure.add_subplot(111)
    #     ax.plot(self.plotted_roi.i, label=filename)
    #     title = f'mz = {self.plotted_roi.mzmean:.3f}, ' \
    #             f'rt = {self.plotted_roi.rt[0]:.1f} - {self.plotted_roi.rt[1]:.1f}'
    #
    #     for border in borders:
    #         begin, end = border
    #         ax.fill_between(range(begin, end + 1), self.plotted_roi.i[begin:end + 1], alpha=0.5)
    #     ax.set_title(title)
    #     ax.legend(loc='best')
    #     self.canvas.draw()  # refresh canvas


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
