import sys
import os
from plot import PlotWindow, denoise_parawindow, ProgressBarsListItem
from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
from utils.threading import Worker
from df_process_test import construct_df
from preprocess import defect_process
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

        # self._list_of_files.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.blank_file.connectRightClick(partial(FileListMenu, self))  # 右键打开菜单
        self.sample_file.connectRightClick(partial(FileListMenu, self))  # 右键打开菜单
        self.list_of_processed.connectRightClick(partial(ProcessedListMenu, self))
        # self.list_of_processed.connectDoubleClick(self.plot_processed)  # 双击绘制TIC图

    def _create_menu(self):
        # menu = QtWidgets.QMenuBar(self)
        menu = self.menuBar()

        # file submenu(step1&5):导入文件、每一步处理后的图谱、最终筛选出的mz、rt、intensity（csv?）
        file = menu.addMenu('File')

        # 导入mzxml文件
        blank_mzxml_import = QtWidgets.QAction('Open *.mzXML as blank', self)
        blank_mzxml_import.triggered.connect(partial(self._open_mzxml, 'blank'))
        file.addAction(blank_mzxml_import)
        sample_mzxml_import = QtWidgets.QAction('Open *.mzXML as sample', self)
        sample_mzxml_import.triggered.connect(partial(self._open_mzxml, 'sample'))
        file.addAction(sample_mzxml_import)
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

        background_subtraction_denoise = QtWidgets.QAction("Background subtraction denoise", self)
        background_subtraction_denoise.triggered.connect(self.denoise)
        denoise.addAction(background_subtraction_denoise)

        # peak matching(step4)
        matching = menu.addMenu('Peak matching')
        nl_identify = QtWidgets.QAction('中性丢失识别', self)
        nl_identify.triggered.connect(self.nl)
        fragment_identify = QtWidgets.QAction('特征碎片识别', self)
        fragment_identify.triggered.connect(self.fragment)
        isotope_differential = QtWidgets.QAction('同位素特征m/z差值', self)
        isotope_differential.triggered.connect(self.isotope)
        matching.addAction(nl_identify)
        matching.addAction(fragment_identify)
        matching.addAction(isotope_differential)

    def init_ui(self):
        self.setWindowTitle('DnsCl')

        # 左侧布局
        blank_label = QtWidgets.QLabel('Blank list：')
        self.blank_file = FileListWidget()
        sample_label = QtWidgets.QLabel('Sample list：')
        self.sample_file = FileListWidget()
        process_list_label = QtWidgets.QLabel('Processed list：')
        self.list_of_processed = FileListWidget()

        layout_left = QtWidgets.QVBoxLayout()
        layout_left.addWidget(blank_label)
        layout_left.addWidget(self.blank_file, 2)
        layout_left.addWidget(sample_label)
        layout_left.addWidget(self.sample_file, 2)
        layout_left.addWidget(process_list_label)
        layout_left.addWidget(self.list_of_processed, 6)

        # 中间布局
        layout_mid = QtWidgets.QHBoxLayout()
        layout_plot = QtWidgets.QVBoxLayout()
        layout_plot.addWidget(self._toolbar)
        layout_plot.addWidget(self._canvas, 9)

        # 进度条布局
        scrollable_pb_list = QtWidgets.QScrollArea()
        scrollable_pb_list.setWidget(self._pb_list)
        scrollable_pb_list.setWidgetResizable(True)
        # layout_plot.addWidget(scrollable_pb_list, 1)

        layout_mid.addLayout(layout_plot)

        # 主视窗布局
        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(layout_left, 1)
        layout.addLayout(layout_mid, 9)

        # self.setLayout(layout)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        self.setCentralWidget(widget)

    def _open_mzxml(self, mode):
        if mode == 'blank':
            path = QtWidgets.QFileDialog.getOpenFileName(None, 'select a file as blank', '', 'mzXML (*.mzXML)')[0]
            file_name = os.path.basename(path)
            self.blank_file.addFile(file_name)
            plotted, _ = self.plot_tic(path, mode='blank')
            if plotted:
                self.blank_plotted_list.append(path)
        elif mode == 'sample':
            path = QtWidgets.QFileDialog.getOpenFileName(None, 'select a file as sample', '', 'mzXML (*.mzXML)')[0]
            file_name = os.path.basename(path)
            self.sample_file.addFile(file_name)
            plotted, _ = self.plot_tic(path, mode='sample')
            if plotted:
                self.sample_plotted_list.append(path)

    def _open_csv(self):
        files_names = QtWidgets.QFileDialog.getOpenFileNames(None, '', '', 'csv (*.csv)')[0]
        for name in files_names:
            self.list_of_processed.addFile(name)

    def _export_features(self, mode):
        if self.blank_file.count() > 0:
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

    def mass_defect_limit(self):  # step 2
        if len(self.sample_plotted_list) > 0 and len(self.blank_plotted_list) > 0:
            sample = self.sample_plotted_list[0]
            blank = self.blank_plotted_list[0]
            subwindow = defect_parawindow(sample, blank, self)
            subwindow.show()
        else:
            msg = QtWidgets.QMessageBox(self)
            msg.setText('You should import 2 files as sample and blank each, first')
            msg.setWindowTitle("Warning")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def denoise(self):  # TODO: step 3
        try:
            subwindow = denoise_parawindow(self)
            subwindow.show()
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def nl(self):
        pass

    def fragment(self):
        pass

    def isotope(self):
        pass

    def plot_processed(self, item):
        file = item.text()  # 获取文件名
        file_path = self.list_of_processed.getPath(item)
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


class ProcessedListMenu(QtWidgets.QMenu):
    def __init__(self, parent: MainWindow):
        self.parent = parent
        super().__init__(parent)
        self._thread_pool = QtCore.QThreadPool()

        menu = QtWidgets.QMenu(parent)

        plot = QtWidgets.QAction('show TIC', parent)
        close = QtWidgets.QAction('Close', parent)

        menu.addAction(plot)
        menu.addAction(close)

        action = menu.exec_(QtGui.QCursor.pos())

        if action == plot:
            self.plot()
        elif action == close:
            self.close_files()

    def plot(self):
        for item in self.get_selected_files():
            worker = Worker('Plotting TIC from csv ...', self.parent.plot_processed, item)
            worker.signals.close_signal.connect(worker.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker)

            # self.parent.plot_processed(item)

    def close_files(self):
        for item in self.get_selected_files():
            self.parent.list_of_processed.deleteFile(item)

    def get_selected_files(self):
        return self.parent.list_of_processed.selectedItems()


class FileListMenu(QtWidgets.QMenu):
    def __init__(self, parent: MainWindow):
        self.parent = parent
        super().__init__(parent)

        menu = QtWidgets.QMenu(parent)

        # sample = QtWidgets.QAction('Plot as sample', parent)
        # blank = QtWidgets.QAction('Plot as blank', parent)
        clear = QtWidgets.QAction('Clear plot', parent)
        close = QtWidgets.QAction('Close', parent)

        # menu.addAction(sample)
        # menu.addAction(blank)
        menu.addAction(clear)
        menu.addAction(close)

        action = menu.exec_(QtGui.QCursor.pos())

        # for file in self.get_selected_files():
        #     file = file.text()
        #     if action == sample:
        #         plotted, path = self.parent.plot_tic(file, mode='sample')
        #         if plotted:
        #             self.parent.sample_plotted_list.append(path)
        #     elif action == blank:
        #         plotted, path = self.parent.plot_tic(file, mode='blank')
        #         if plotted:
        #             self.parent.blank_plotted_list.append(path)

        if action == close:
            self.close_files()
        elif action == clear:
            self.delete_tic()

    def delete_tic(self):  # TODO:新版本待调试
        for item in self.get_selected_files():
            self.parent.delete_line(item.text())
        self.parent.refresh_canvas()

    def close_files(self):  # TODO: 将sample和blank的list管理分开
        for item in self.get_selected_files():
            self.parent.blank_file.deleteFile(item)

    def get_selected_files(self):
        return self.parent.blank_file.selectedItems()


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
        self.open_files = set()

    def addFile(self, path: str):
        filename = os.path.basename(path)
        if filename not in self.open_files:  # 避免在列表中重复添加文件
            self.file2path[filename] = path
            self.addItem(filename)
            self.open_files.add(filename)
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText("File already open!")
            msg.setWindowTitle("Warning")
            msg.exec_()

    def deleteFile(self, item: QtWidgets.QListWidgetItem):
        del self.file2path[item.text()]
        self.takeItem(self.row(item))
        self.open_files.remove(item.text())

    def getPath(self, item: QtWidgets.QListWidgetItem):
        return self.file2path[item.text()]


class defect_parawindow(QtWidgets.QDialog):
    def __init__(self, sample, blank, parent: MainWindow):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowTitle('Mass defect limit option')
        self.sample = sample
        self.blank = blank
        self._thread_pool = QtCore.QThreadPool()

        # 字体设置
        font = QtGui.QFont()
        font.setFamily('Arial')
        font.setBold(True)
        font.setPixelSize(15)
        font.setWeight(75)

        range_setting = QtWidgets.QFormLayout()

        rt_label = QtWidgets.QLabel("RT range")
        rt_label.setFont(font)
        self.lower_rt = QtWidgets.QLineEdit()
        self.lower_rt.setText('2.5')
        self.lower_rt.setFixedSize(60, 30)
        self.lower_rt.setFont(font)
        self.upper_rt = QtWidgets.QLineEdit()
        self.upper_rt.setText('30.0')
        self.upper_rt.setFixedSize(60, 30)
        self.upper_rt.setFont(font)
        rt_layout = QtWidgets.QHBoxLayout()
        rt_text1 = QtWidgets.QLabel(self)
        rt_text1.setText('to')
        rt_text1.setFont(font)
        rt_text2 = QtWidgets.QLabel(self)
        rt_text2.setText('min.')
        rt_text2.setFont(font)
        rt_layout.addWidget(self.lower_rt)
        rt_layout.addWidget(rt_text1)
        rt_layout.addWidget(self.upper_rt)
        rt_layout.addWidget(rt_text2)

        mz_label = QtWidgets.QLabel("m/z range")
        mz_label.setFont(font)
        self.lower_mz = QtWidgets.QLineEdit()
        self.lower_mz.setText('150.0')
        self.lower_mz.setFixedSize(60, 30)
        self.lower_mz.setFont(font)
        self.upper_mz = QtWidgets.QLineEdit()
        self.upper_mz.setText('1000.0')
        self.upper_mz.setFixedSize(60, 30)
        self.upper_mz.setFont(font)
        mz_layout = QtWidgets.QHBoxLayout()
        mz_text1 = QtWidgets.QLabel(self)
        mz_text1.setText('to')
        mz_text1.setFont(font)
        mz_text2 = QtWidgets.QLabel(self)
        mz_text2.setText('Da')
        mz_text2.setFont(font)
        mz_layout.addWidget(self.lower_mz)
        mz_layout.addWidget(mz_text1)
        mz_layout.addWidget(self.upper_mz)
        mz_layout.addWidget(mz_text2)

        defect_label = QtWidgets.QLabel("mass defect")
        defect_label.setFont(font)
        self.lower_mass = QtWidgets.QLineEdit()
        self.lower_mass.setText('600')
        self.lower_mass.setFixedSize(60, 30)
        self.lower_mass.setFont(font)
        self.upper_mass = QtWidgets.QLineEdit()
        self.upper_mass.setText('1000')
        self.upper_mass.setFixedSize(60, 30)
        self.upper_mass.setFont(font)
        defect_layout = QtWidgets.QHBoxLayout()
        defect_text1 = QtWidgets.QLabel(self)
        defect_text1.setText('to')
        defect_text1.setFont(font)
        defect_text2 = QtWidgets.QLabel(self)
        defect_text2.setText('mD')
        defect_text2.setFont(font)
        defect_layout.addWidget(self.lower_mass)
        defect_layout.addWidget(defect_text1)
        defect_layout.addWidget(self.upper_mass)
        defect_layout.addWidget(defect_text2)

        para_setting = QtWidgets.QFormLayout()
        para_setting.alignment()

        tolerance_label = QtWidgets.QLabel("Mass tolerance")
        tolerance_label.setFont(font)
        self.mass_tolerance = QtWidgets.QLineEdit()
        self.mass_tolerance.setText('10')
        self.mass_tolerance.setFixedSize(60, 30)
        self.mass_tolerance.setFont(font)
        tolerance_layout = QtWidgets.QHBoxLayout()
        tolerance_text = QtWidgets.QLabel(self)
        tolerance_text.setText('ppm')
        tolerance_text.setFont(font)
        tolerance_layout.addWidget(self.mass_tolerance)
        tolerance_layout.addWidget(tolerance_text)
        tolerance_layout.addStretch()  # 什么用处？

        thd_label = QtWidgets.QLabel("Intensity Threshold")
        thd_label.setFont(font)
        self.intensity_thd = QtWidgets.QLineEdit()
        self.intensity_thd.setText('10000')
        self.intensity_thd.setFixedSize(60, 30)
        self.intensity_thd.setFont(font)
        thd_layout = QtWidgets.QHBoxLayout()
        thd_text = QtWidgets.QLabel(self)
        thd_text.setText('a.u.')
        thd_text.setFont(font)
        thd_layout.addWidget(self.intensity_thd)
        thd_layout.addWidget(thd_text)
        # thd_layout.addStretch()

        range_setting.addRow(rt_label, rt_layout)
        range_setting.addRow(mz_label, mz_layout)
        range_setting.addRow(defect_label, defect_layout)
        # range_setting.setLabelAlignment(Q)

        para_setting.addRow(tolerance_label, tolerance_layout)
        para_setting.addRow(thd_label, thd_layout)

        ok_button = QtWidgets.QPushButton('OK')
        ok_button.clicked.connect(self.defect)
        ok_button.setFont(font)
        ok_button.resize(80, 80)  # 未生效

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(range_setting)
        layout.addLayout(para_setting)
        layout.addWidget(ok_button)
        self.setLayout(layout)

    def defect(self):
        try:
            self.lower_rt = float(self.lower_rt.text())
            self.upper_rt = float(self.upper_rt.text())
            self.lower_mz = float(self.lower_mz.text())
            self.upper_mz = float(self.upper_mz.text())
            self.lower_mass = float(self.lower_mass.text())
            self.upper_mass = float(self.upper_mass.text())
            self.mass_tolerance = float(self.mass_tolerance.text())
            self.intensity_thd = float(self.intensity_thd.text())
            self.close()

            worker = Worker('processing blank...', defect_process, self.blank, self.lower_rt, self.upper_rt,
                            self.lower_mz, self.upper_mz, self.intensity_thd, self.lower_mass, self.upper_mass)
            worker.signals.result.connect(partial(self.result_to_csv, 'blank_pre.csv'))
            worker.signals.result.connect(self.start_sample)
            worker.signals.close_signal.connect(worker.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker)
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def start_sample(self):
        worker1 = Worker('processing sample...', defect_process, self.sample, self.lower_rt, self.upper_rt,
                         self.lower_mz, self.upper_mz, self.intensity_thd, self.lower_mass, self.upper_mass)
        worker1.signals.result.connect(partial(self.result_to_csv, 'sample_pre.csv'))
        worker1.signals.close_signal.connect(worker1.progress_dialog.close)
        self._thread_pool.start(worker1)

    def result_to_csv(self, name, df):
        df.to_csv(name)
        self.parent.list_of_processed.addFile(name)


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
