import sys
import os
from plot import PlotWindow, ParameterWindow1, ParameterWindow2, ProgressBarsListItem
# from utils.show_list import find_mzML, PeakListWidget, ROIListWidget, ProgressBarsListItem
# from utils.annotation_window import AnnotationParameterWindow, ReAnnotationParameterWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
from utils.threading import Worker
from df_process_test import construct_df
import matplotlib.pyplot as plt


class MainWindow(PlotWindow):
    def __init__(self):
        super().__init__()
        # self.init_data()
        self._create_menu()
        self.resize(1350, 700)
        self.init_ui()
        self.setStyleSheet(style_sheet)
        self.show()

        # self._list_of_files.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)  # https://blog.csdn.net/fjunchao/article/details/117551577
        self._list_of_files.connectRightClick(partial(FileListMenu, self))  # 右键打开菜单
        self._list_of_processed.connectDoubleClick(self.plot_processed)  # 双击绘制TIC图

    def _create_menu(self):
        # menu = QtWidgets.QMenuBar(self)
        menu = self.menuBar()

        # file submenu(step1&5):导入文件、每一步处理后的图谱、最终筛选出的mz、rt、intensity（csv?）
        file = menu.addMenu('File')

        # 导入mzxml文件
        mzxml_import = QtWidgets.QAction('Open *.mzXML', self)
        mzxml_import.triggered.connect(self._open_mzxml)
        file.addAction(mzxml_import)
        # 直接导入处理过的文件(csv)
        csv_import = QtWidgets.QAction('Open processed file (*.csv)', self)
        csv_import.triggered.connect(self._open_csv)
        file.addAction(csv_import)

        file_export = QtWidgets.QMenu('Save', self)
        # 导出当前图谱为图片
        file_export_features_png = QtWidgets.QAction('Save current spectrogram as *.png files', self)
        file_export_features_png.triggered.connect(partial(self._export_features, 'png'))
        file_export.addAction(file_export_features_png)
        # 导出当前图谱为新mzml
        file_export_features_mzml = QtWidgets.QAction('Save current spectrogram as new *.mzxml files', self)
        file_export_features_mzml.triggered.connect(partial(self._export_features, 'mzxml'))
        file_export.addAction(file_export_features_mzml)
        # 导出最终csv
        file_export_features_csv = QtWidgets.QAction('Save current spectrogram as *.csv files', self)
        file_export_features_csv.triggered.connect(partial(self._export_features, 'csv'))
        file_export.addAction(file_export_features_csv)

        # file_clear = QtWidgets.QMenu('Clear', self)
        # file_clear_features = QtWidgets.QAction('Clear panel with detected features', self)
        # file_clear_features.triggered.connect(self._list_of_features.clear)
        # file_clear.addAction(file_clear_features)

        file.addMenu(file_export)
        # file.addMenu(file_clear)

        # background subtraction denoise(step2&3)
        denoise = menu.addMenu('Denoising')

        Mass_defect_limit = QtWidgets.QAction('Mass defect limit', self)
        Mass_defect_limit.triggered.connect(self.mass_defect_limit)
        denoise.addAction(Mass_defect_limit)

        background_subtraction_denoise = QtWidgets.QAction("background subtraction denoise", self)
        background_subtraction_denoise.triggered.connect(self.denoise)
        denoise.addAction(background_subtraction_denoise)

        # peak matching(step4)
        matching = menu.addMenu('Matching')
        peak_matching = QtWidgets.QAction('peak matching', self)
        # peak_matching.triggered.connect(self.matching)
        matching.addAction(peak_matching)

    def init_ui(self):
        self.setWindowTitle('DnsCl')

        # 左侧布局
        file_list_label = QtWidgets.QLabel('File list：')
        self._list_of_files = FileListWidget()
        process_list_label = QtWidgets.QLabel('Processed list：')
        self._list_of_processed = FileListWidget()

        layout_left = QtWidgets.QVBoxLayout()
        layout_left.addWidget(file_list_label)
        layout_left.addWidget(self._list_of_files, 3)
        layout_left.addWidget(process_list_label)
        layout_left.addWidget(self._list_of_processed, 6)

        # 中间布局
        layout_mid = QtWidgets.QHBoxLayout()
        layout_plot = QtWidgets.QVBoxLayout()
        layout_plot.addWidget(self._toolbar)
        layout_plot.addWidget(self._canvas, 9)

        # 进度条布局
        scrollable_pb_list = QtWidgets.QScrollArea()
        scrollable_pb_list.setWidget(self._pb_list)
        scrollable_pb_list.setWidgetResizable(True)
        layout_plot.addWidget(scrollable_pb_list, 1)

        layout_mid.addLayout(layout_plot)

        # 主视窗布局
        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(layout_left, 1)
        layout.addLayout(layout_mid, 9)

        # self.setLayout(layout)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        self.setCentralWidget(widget)

    def _open_mzxml(self):
        files_names = QtWidgets.QFileDialog.getOpenFileNames(None, '', '', 'mzXML (*.mzXML)')[0]
        for name in files_names:
            self._list_of_files.addFile(name)

    def _open_csv(self):
        files_names = QtWidgets.QFileDialog.getOpenFileNames(None, '', '', 'csv (*.csv)')[0]
        for name in files_names:
            self._list_of_processed.addFile(name)

    def _export_features(self, mode):
        if self._list_of_files.count() > 0:
            if mode == 'csv':
                # to do: features should be QTreeWidget (root should keep basic information: files and parameters)
                files = self._feature_parameters['files']
                # table = ResultTable(files, self._list_of_features.features)
                # table.fill_zeros(self._feature_parameters['delta mz'])
                file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export features', '',
                                                                     'csv (*.csv)')
                if file_name:
                    # table.to_csv(file_name)
                    pass
            elif mode == 'mzxml':
                pass
            elif mode == 'png':
                directory = str(QtWidgets.QFileDialog.getExistingDirectory(self, 'Choose a directory where to save'))
                # self.run_thread('Saving features as *.png files:', worker)
                pass
            else:
                assert False, mode
        else:
            msg = QtWidgets.QMessageBox(self)
            msg.setText('Something is wrong')
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def clear_btn(self):
        self._list_of_files.clear()

    def mass_defect_limit(self):  # step 2
        if len(self.sample_plotted_list) > 0 and len(self.blank_plotted_list) > 0:
            sample = self.sample_plotted_list[0]
            blank = self.blank_plotted_list[0]
            subwindow = ParameterWindow1(sample, blank, self)
            subwindow.show()
        else:
            msg = QtWidgets.QMessageBox(self)
            msg.setText('You should import 2 files as sample and blank each, first')
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def denoise(self):  # TODO: step 3
        if len(self.sample_plotted_list) > 0 and len(self.blank_plotted_list) > 0:
            sample = self.sample_plotted_list[0]
            blank = self.blank_plotted_list[0]
            subwindow = ParameterWindow2(sample, blank, self)
            subwindow.show()
        else:
            msg = QtWidgets.QMessageBox(self)
            msg.setText('You should import 2 files as sample and blank each, first')
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def plot_processed(self, item):
        file = item.text()  # 获取文件名
        file_path = self._list_of_processed.getPath(item)
        obj = construct_df(file_path, file)
        x = obj['x']
        y = obj['y']
        label = obj['label']

        fig = plt.figure(dpi=300, figsize=(24, 6))
        # fig = plt.subplot(111)
        plt.title('Processed TIC')
        plt.xlabel('time')
        plt.ylabel('intensity')
        plt.plot(x, y, label=label)
        plt.legend(loc='best')
        plt.grid(alpha=0.8)
        fig.show()


class ProcessListMenu(QtWidgets.QMenu):
    def __init__(self, parent: MainWindow):
        self.parent = parent
        super().__init__(parent)

        menu = QtWidgets.QMenu(parent)

        clear = QtWidgets.QAction('Clear plot', parent)
        close = QtWidgets.QAction('Close', parent)

        menu.addAction(clear)
        menu.addAction(close)

        action = menu.exec_(QtGui.QCursor.pos())

        if action == close:
            self.close_files()
        elif action == clear:
            self.delete_tic()

    def delete_tic(self):  # TODO:暂时只能全部清空，能否选中清除
        for item in self.parent.get_selected_files():
            self.parent.delete_line(item.text())
        self.parent.refresh_canvas()

    def close_files(self):
        for item in self.parent.get_selected_files():
            self.parent.close_file(item)


class FileListMenu(QtWidgets.QMenu):
    def __init__(self, parent: MainWindow):
        self.parent = parent
        super().__init__(parent)

        menu = QtWidgets.QMenu(parent)

        sample = QtWidgets.QAction('Plot as sample', parent)
        blank = QtWidgets.QAction('Plot as blank', parent)
        clear = QtWidgets.QAction('Clear plot', parent)
        close = QtWidgets.QAction('Close', parent)

        menu.addAction(sample)
        menu.addAction(blank)
        menu.addAction(clear)
        menu.addAction(close)

        action = menu.exec_(QtGui.QCursor.pos())

        for file in self.parent.get_selected_files():
            file = file.text()
            if action == sample:
                plotted, path = self.parent.plot_tic(file, mode='sample')
                if plotted:
                    self.parent.sample_plotted_list.append(path)
            elif action == blank:
                plotted, path = self.parent.plot_tic(file, mode='blank')
                if plotted:
                    self.parent.blank_plotted_list.append(path)

        if action == close:
            self.close_files()
        elif action == clear:
            self.delete_tic()

    def delete_tic(self):  # TODO:暂时只能全部清空，能否选中清除
        for item in self.parent.get_selected_files():
            self.parent.delete_line(item.text())
        self.parent.refresh_canvas()

    def close_files(self):
        for item in self.parent.get_selected_files():
            self.parent.close_file(item)


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


class FileListWidget(ClickableListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file2path = {}

    def addFile(self, path: str):
        filename = os.path.basename(path)
        self.file2path[filename] = path
        self.addItem(filename)

    def deleteFile(self, item: QtWidgets.QListWidgetItem):
        del self.file2path[item.text()]
        self.takeItem(self.row(item))

    def getPath(self, item: QtWidgets.QListWidgetItem):
        return self.file2path[item.text()]


style_sheet = """
QMenuBar{
    background-color: #E9EDF2;
    font-size: 17px;
    font-weight: bold;
    color: #52404D;
    font-family: Times New Roman
}
QMenuBar::item::selected{
    background-color: #84B6C0
}
QMenu{
    background-color: #CAE0E4;
    font-size: 17px;
    color: #52404D;
    font-family: Times New Roman
}
QMenu::item::selected{
    background-color: #84B6C0
}
QMainWindow{
    background-color: qlineargradient(spread:pad, x1:1, y1:1, x2:1, y2:0, stop:0 #84B6C0, stop:1 #E9EDF2)   
}
"""

if __name__ == '__main__':
    # QtCore.QCoreApplication.setAttribute(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(style_sheet)
    window = MainWindow()
    # main_window.show()
    # main_window.showMaximized()  # 屏幕最大化显示窗口
    # sys.exit(app.exec_())
    app.exec()
