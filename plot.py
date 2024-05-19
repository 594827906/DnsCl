import functools
from functools import partial
from PyQt5 import QtWidgets, QtCore, QtGui
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from utils.threading import Worker
from background_subtract import denoise_bg
from peak_extraction import neut_loss, obtain_MS2, match_MS2
import pymzml
import pyteomics.mzxml as mzxml
import numpy as np
import os


class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self._thread_pool = QtCore.QThreadPool()
        self._pb_list = ProgressBarsList(self)
        self.sample_plotted_list = []
        self.blank_plotted_list = []
        self._plotted_list = []

        self._feature_parameters = None

        self._figure = plt.figure()
        self.fig_blank = self._figure.add_subplot(211)  # plot sample
        self.fig_blank.ticklabel_format(axis='y', scilimits=(0, 0))
        self.fig_sample = self._figure.add_subplot(212)  # plot blank
        self.fig_sample.ticklabel_format(axis='y', scilimits=(0, 0))
        self.fig_sample.set_xlabel('Retention time [min]')
        self._figure.tight_layout()
        self._label2line = dict()  # a label (aka line name) to plotted line
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)

    def _threads_finisher(self, text=None, icon=None, pb=None):
        if pb is not None:
            self._pb_list.removeItem(pb)
            pb.setParent(None)
        if text is not None:
            msg = QtWidgets.QMessageBox(self)
            msg.setText(text)
            msg.setIcon(icon)
            msg.exec_()

    def set_features(self, obj):
        features, parameters = obj
        self._list_of_features.clear()
        for feature in sorted(features, key=lambda x: x.mz):
            self._list_of_features.add_feature(feature)
        self._feature_parameters = parameters

    # def scroll_event(self, event):  # 滚轮缩放
    #     x_min, x_max = event.inaxes.get_xlim()
    #     x_range = (x_max - x_min) / 10
    #     if event.button == 'up':
    #         event.inaxes.set(xlim=(x_min + x_range, x_max - x_range))
    #         print('up')
    #     elif event.button == 'down':
    #         event.inaxes.set(xlim=(x_min - x_range, x_max + x_range))
    #         print('down')
    #     self._canvas.draw_idle()

    def plotter(self, obj):
        # if not self._label2line:  # in case if 'feature' was plotted
        if obj['mode'] == 'blank':
            self._figure.delaxes(self.fig_blank)
            self.fig_blank = self._figure.add_subplot(211)
            self.fig_blank.set_title('Blank')
            # self.fig_blank.set_xlabel('Retention time [min]')
            self.fig_blank.set_ylabel('Intensity')
            self.fig_blank.ticklabel_format(axis='y', scilimits=(0, 0))  # 使用科学计数法
            line = self.fig_blank.plot(obj['x'], obj['y'], label=obj['label'])
            self.fig_blank.legend(loc='best')
            self.fig_blank.grid(alpha=0.8)
        if obj['mode'] == 'sample':
            self._figure.delaxes(self.fig_sample)
            self.fig_sample = self._figure.add_subplot(212)
            self.fig_sample.set_title('Sample')
            self.fig_sample.set_xlabel('Retention time [min]')
            self.fig_sample.set_ylabel('Intensity')
            self.fig_sample.ticklabel_format(axis='y', scilimits=(0, 0))  # 使用科学计数法
            line = self.fig_sample.plot(obj['x'], obj['y'], label=obj['label'])
            self.fig_sample.legend(loc='best')
            self.fig_sample.grid(alpha=0.8)

        self._label2line[obj['label']] = line[0]  # save line
        self._figure.tight_layout()
        # self._figure.canvas.mpl_connect('scroll_event', self.scroll_event)  # 鼠标滚轮缩放画布
        # self._figure.canvas.mpl_connect('button_press_event', self.button_press)  # 右键清空画布
        self._canvas.draw()

    def get_selected_features(self):
        return self._list_of_features.selectedItems()

    def get_plotted_lines(self):
        return list(self._label2line.keys())

    def plot_feature(self, item, shifted=True):
        feature = self._list_of_features.get_feature(item)
        self._label2line = dict()  # empty plotted TIC and EIC
        self._figure.clear()
        self.fig_sample = self._figure.add_subplot(111)
        feature.plot(self.fig_sample, shifted=shifted)
        self.fig_sample.set_title(item.text())
        self.fig_sample.set_xlabel('Retention time')
        self.fig_sample.set_ylabel('Intensity')
        self.fig_sample.ticklabel_format(axis='y', scilimits=(0, 0))
        self._figure.tight_layout()
        self._canvas.draw()  # refresh canvas

    def plot_tic(self, path, mode):
        filename = os.path.basename(path)
        label = f'{filename}'
        plotted = False
        # if mode == 'blank':
        #     path = self.blank_file.file2path[file]
        # elif mode == 'sample':
        #     path = self.sample_file.file2path[file]
        if label not in self._label2line:
            worker = Worker('plotting TIC...', construct_mzxml, path, label, mode)
            worker.signals.result.connect(self.plotter)
            worker.signals.close_signal.connect(worker.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker)
            self._plotted_list.append(label)

            plotted = True
        return plotted, filename  # TODO: filename还有什么用

    def delete_line(self, label):
        self.fig_sample.cla()
        self._label2line.clear()
        self._plotted_list.remove(label)  # delete item from list
        self._canvas.draw_idle()

    def refresh_canvas(self):
        if self._label2line:
            self.fig_blank.legend(loc='best')
            self.fig_blank.relim()  # recompute the ax.dataLim
            self.fig_blank.autoscale_view()  # update ax.viewLim using the new dataLim
            self.fig_sample.legend(loc='best')
            self.fig_sample.relim()  # recompute the ax.dataLim
            self.fig_sample.autoscale_view()  # update ax.viewLim using the new dataLim
        else:
            self._figure.clear()
            self.fig_blank = self._figure.add_subplot(211)
            self.fig_blank.set_xlabel('Retention time [min]')
            # self.fig_blank.set_ylabel('Intensity')
            self.fig_blank.ticklabel_format(axis='y', scilimits=(0, 0))
            self.fig_sample = self._figure.add_subplot(212)
            self.fig_sample.set_xlabel('Retention time [min]')
            # self.fig_sample.set_ylabel('Intensity')
            self.fig_sample.ticklabel_format(axis='y', scilimits=(0, 0))
        self._canvas.draw()


class denoise_parawindow(QtWidgets.QDialog):
    def __init__(self, parent: PlotWindow):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowTitle('Background denoise option')
        self._thread_pool = QtCore.QThreadPool()

        # 字体设置
        font = QtGui.QFont()
        font.setFamily('Arial')
        font.setBold(True)
        font.setPixelSize(15)
        font.setWeight(75)

        files_layout = QtWidgets.QVBoxLayout()
        blank_choose_layout = QtWidgets.QHBoxLayout()
        sample_choose_layout = QtWidgets.QHBoxLayout()
        # 选择经过第二步处理的csv
        choose_blank_label = QtWidgets.QLabel()
        choose_blank_label.setText('Choose a .csv as blank:')
        choose_blank_label.setFont(font)
        self.blank_edit = QtWidgets.QLineEdit()
        blank_button = QtWidgets.QToolButton()
        blank_button.setText('...')
        blank_button.setFont(font)
        blank_button.clicked.connect(self.set_blank)

        choose_sample_label = QtWidgets.QLabel()
        choose_sample_label.setText('Choose a .csv as sample:')
        choose_sample_label.setFont(font)
        self.sample_edit = QtWidgets.QLineEdit()
        sample_button = QtWidgets.QToolButton()
        sample_button.setText('...')
        sample_button.setFont(font)
        sample_button.clicked.connect(self.set_sample)

        blank_choose_layout.addWidget(self.blank_edit)
        blank_choose_layout.addWidget(blank_button)
        sample_choose_layout.addWidget(self.sample_edit)
        sample_choose_layout.addWidget(sample_button)
        files_layout.addWidget(choose_blank_label)
        files_layout.addLayout(blank_choose_layout)
        files_layout.addWidget(choose_sample_label)
        files_layout.addLayout(sample_choose_layout)


        range_setting = QtWidgets.QFormLayout()

        rt_label = QtWidgets.QLabel("RT window： ±")
        rt_label.setFont(font)
        self.rt_window = QtWidgets.QLineEdit()
        self.rt_window.setText('5')
        self.rt_window.setFixedSize(50, 30)
        self.rt_window.setFont(font)
        rt_layout = QtWidgets.QHBoxLayout()
        rt_text = QtWidgets.QLabel(self)
        rt_text.setText('s')
        rt_text.setFont(font)
        rt_layout.addWidget(self.rt_window)
        rt_layout.addWidget(rt_text)

        mz_label = QtWidgets.QLabel("m/z window： ±")
        mz_label.setFont(font)
        self.mz_window = QtWidgets.QLineEdit()
        self.mz_window.setText('10')
        self.mz_window.setFixedSize(50, 30)
        self.mz_window.setFont(font)
        mz_layout = QtWidgets.QHBoxLayout()
        mz_text1 = QtWidgets.QLabel(self)
        mz_text1.setText('ppm')
        mz_text1.setFont(font)
        mz_layout.addWidget(self.mz_window)
        mz_layout.addWidget(mz_text1)

        ratio_setting = QtWidgets.QFormLayout()
        ratio_setting.alignment()

        ratio_label = QtWidgets.QLabel("Sample/Blank Ratio： ")
        ratio_label.setFont(font)
        self.ratio = QtWidgets.QLineEdit()
        self.ratio.setText('10')
        self.ratio.setFixedSize(50, 30)
        self.ratio.setFont(font)
        ratio_layout = QtWidgets.QHBoxLayout()
        ratio_text = QtWidgets.QLabel(self)
        ratio_text.setText('%')
        ratio_text.setFont(font)
        ratio_layout.addWidget(self.ratio)
        ratio_layout.addWidget(ratio_text)
        ratio_layout.addStretch()  # 什么用处？

        range_setting.addRow(rt_label, rt_layout)
        range_setting.addRow(mz_label, mz_layout)
        # range_setting.setLabelAlignment(Q)

        ratio_setting.addRow(ratio_label, ratio_layout)

        ok_button = QtWidgets.QPushButton('OK')
        ok_button.clicked.connect(self.denoise)
        ok_button.setFont(font)
        ok_button.resize(80, 80)  # 未生效

        para_layout = QtWidgets.QVBoxLayout()
        para_layout.addLayout(range_setting)
        para_layout.addLayout(ratio_setting)
        para_layout.addWidget(ok_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(files_layout)
        layout.addLayout(para_layout)
        self.setLayout(layout)

    def set_blank(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(None, None, None, 'csv(*.csv)')
        if file:
            self.blank_edit.setText(file)

    def set_sample(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(None, None, None, 'csv(*.csv)')
        if file:
            self.sample_edit.setText(file)

    def denoise(self):
        try:
            blank = self.blank_edit.text()
            sample = self.sample_edit.text()
            rt_win = float(self.rt_window.text())
            mz_win = float(self.mz_window.text())
            ratio = float(self.ratio.text())
            self.close()

            # TODO:确认rt和mz的单位
            worker = Worker('Background subtract denoising...', denoise_bg,
                            blank, sample, mz_win*10e-7, rt_win/60, ratio)
            # worker.signals.result.connect(partial(self.result_to_csv, 'denoise_Area.csv'))
            worker.signals.close_signal.connect(worker.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker)
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def result_to_csv(self, name, df):
        df.to_csv(name, index=False)
        # self.parent.list_of_processed.addFile(name)


class match_parawindow1(QtWidgets.QDialog):
    def __init__(self, mode, parent: PlotWindow):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowTitle('Peak match option')
        self._thread_pool = QtCore.QThreadPool()

        # 字体设置
        font = QtGui.QFont()
        font.setFamily('Arial')
        font.setBold(True)
        font.setPixelSize(15)
        font.setWeight(75)

        files_layout = QtWidgets.QVBoxLayout()
        file_choose_layout = QtWidgets.QHBoxLayout()
        # 选择经过第三步处理的csv
        choose_subtracted_label = QtWidgets.QLabel()
        choose_subtracted_label.setText('Choose a .csv that have been subtracted:')
        choose_subtracted_label.setFont(font)
        self.file_edit = QtWidgets.QLineEdit()
        subtracted_button = QtWidgets.QToolButton()
        subtracted_button.setText('...')
        subtracted_button.setFont(font)
        subtracted_button.clicked.connect(self.set_file)

        file_choose_layout.addWidget(self.file_edit)
        file_choose_layout.addWidget(subtracted_button)
        files_layout.addWidget(choose_subtracted_label)
        files_layout.addLayout(file_choose_layout)

        range_setting = QtWidgets.QFormLayout()

        nl_setting = QtWidgets.QFormLayout()
        nl_setting.alignment()

        if mode == '1':
            self.nl_label = QtWidgets.QLabel("Neutral Loss: ")
        elif mode == '3':
            self.nl_label = QtWidgets.QLabel("Isotope number: ")
        self.nl_label.setFont(font)
        self.nl_set = QtWidgets.QLineEdit()
        if mode == '1':
            self.nl_set.setText('63.96125')
            self.nl_set.setFixedSize(100, 30)
        elif mode == '3':
            self.nl_set.setText('6')
            self.nl_set.setFixedSize(50, 30)
        self.nl_set.setFont(font)
        nl_layout = QtWidgets.QHBoxLayout()
        nl_text = QtWidgets.QLabel(self)
        if mode == '1':
            nl_text.setText('Da')
        nl_text.setFont(font)
        nl_layout.addWidget(self.nl_set)
        nl_layout.addWidget(nl_text)
        nl_layout.addStretch()  # 什么用处？

        rt_label = QtWidgets.QLabel("RT tolerance: ±")
        rt_label.setFont(font)
        self.rt_window = QtWidgets.QLineEdit()
        self.rt_window.setText('30')
        self.rt_window.setFixedSize(50, 30)
        self.rt_window.setFont(font)
        rt_layout = QtWidgets.QHBoxLayout()
        rt_text = QtWidgets.QLabel(self)
        rt_text.setText('s')
        rt_text.setFont(font)
        rt_layout.addWidget(self.rt_window)
        rt_layout.addWidget(rt_text)

        mz_label = QtWidgets.QLabel("m/z tolerance: ±")
        mz_label.setFont(font)
        self.mz_window = QtWidgets.QLineEdit()
        self.mz_window.setText('10')
        self.mz_window.setFixedSize(50, 30)
        self.mz_window.setFont(font)
        mz_layout = QtWidgets.QHBoxLayout()
        mz_text1 = QtWidgets.QLabel(self)
        mz_text1.setText('ppm')
        mz_text1.setFont(font)
        mz_layout.addWidget(self.mz_window)
        mz_layout.addWidget(mz_text1)

        nl_setting.addRow(self.nl_label, nl_layout)
        range_setting.addRow(rt_label, rt_layout)
        range_setting.addRow(mz_label, mz_layout)
        # range_setting.setLabelAlignment(Q)

        ok_button = QtWidgets.QPushButton('OK')
        if mode == '1':
            ok_button.clicked.connect(self.nl)
        elif mode == '3':
            ok_button.clicked.connect(self.isotope)
        ok_button.setFont(font)
        ok_button.resize(80, 80)  # 未生效

        para_layout = QtWidgets.QVBoxLayout()
        para_layout.addLayout(nl_setting)
        para_layout.addLayout(range_setting)
        para_layout.addWidget(ok_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(files_layout)
        layout.addLayout(para_layout)
        self.setLayout(layout)

    def set_file(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(None, None, None, 'csv(*.csv)')
        if file:
            self.file_edit.setText(file)

    def nl(self):
        try:
            path = self.file_edit.text()
            nl = float(self.nl_set.text())
            rt_win = float(self.rt_window.text())
            mz_win = float(self.mz_window.text())
            self.close()

            # TODO:确认rt和mz的单位
            worker = Worker('Neutral loss matching...', neut_loss, path, nl, mz_win*10e-7, rt_win/60)
            worker.signals.result.connect(partial(self.result_to_csv, 'NL.csv'))  # TODO:list转表格？
            worker.signals.close_signal.connect(worker.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker)
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def isotope(self):
        try:
            path = self.file_edit.text()
            nl = float(self.nl_set.text())
            rt_win = float(self.rt_window.text())
            mz_win = float(self.mz_window.text())
            self.close()

            # TODO:确认rt和mz的单位
            worker = Worker('Isotope feature matching...', neut_loss, path, nl, mz_win*10e-7, rt_win/60)
            worker.signals.result.connect(partial(self.result_to_csv, 'isotope.csv'))  # TODO:list转表格？
            worker.signals.close_signal.connect(worker.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker)
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def result_to_csv(self, name, df):
        # df.to_csv(name, index=False)
        # self.parent.list_of_processed.addFile(name)
        pass


class match_parawindow2(QtWidgets.QDialog):
    def __init__(self, parent: PlotWindow):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowTitle('Peak match option')
        self._thread_pool = QtCore.QThreadPool()

        # 字体设置
        font = QtGui.QFont()
        font.setFamily('Arial')
        font.setBold(True)
        font.setPixelSize(15)
        font.setWeight(75)

        files_layout = QtWidgets.QVBoxLayout()
        mzxml_choose_layout = QtWidgets.QHBoxLayout()
        subtracted_choose_layout = QtWidgets.QHBoxLayout()

        # 选择原始mzxml以获得二级谱
        choose_mzxml_label = QtWidgets.QLabel()
        choose_mzxml_label.setText('Choose a .mzxml to obtain MS2 data:')
        choose_mzxml_label.setFont(font)
        self.mzxml_edit = QtWidgets.QLineEdit()
        mzxml_button = QtWidgets.QToolButton()
        mzxml_button.setText('...')
        mzxml_button.setFont(font)
        mzxml_button.clicked.connect(self.set_mzxml)

        # 选择经过第三步处理的csv
        choose_subtracted_label = QtWidgets.QLabel()
        choose_subtracted_label.setText('Choose a .csv that have been subtracted:')
        choose_subtracted_label.setFont(font)
        self.subtracted_edit = QtWidgets.QLineEdit()
        subtracted_button = QtWidgets.QToolButton()
        subtracted_button.setText('...')
        subtracted_button.setFont(font)
        subtracted_button.clicked.connect(self.set_subtracted)

        mzxml_choose_layout.addWidget(self.mzxml_edit)
        mzxml_choose_layout.addWidget(mzxml_button)
        subtracted_choose_layout.addWidget(self.subtracted_edit)
        subtracted_choose_layout.addWidget(subtracted_button)
        files_layout.addWidget(choose_mzxml_label)
        files_layout.addLayout(mzxml_choose_layout)
        files_layout.addWidget(choose_subtracted_label)
        files_layout.addLayout(subtracted_choose_layout)

        range_setting = QtWidgets.QFormLayout()

        fragment_setting = QtWidgets.QFormLayout()
        fragment_setting.alignment()

        fragment_label = QtWidgets.QLabel("Fragment m/z: ±")
        fragment_label.setFont(font)
        self.fragment_set = QtWidgets.QLineEdit()
        self.fragment_set.setText('171.10425')
        self.fragment_set.setFixedSize(150, 30)
        self.fragment_set.setFont(font)
        fragment_layout = QtWidgets.QHBoxLayout()
        fragment_text = QtWidgets.QLabel(self)
        fragment_text.setText('Da')
        fragment_text.setFont(font)
        fragment_layout.addWidget(self.fragment_set)
        fragment_layout.addWidget(fragment_text)
        fragment_layout.addStretch()

        rt_label = QtWidgets.QLabel("RT tolerance: ±")
        rt_label.setFont(font)
        self.rt_window = QtWidgets.QLineEdit()
        self.rt_window.setText('30')
        self.rt_window.setFixedSize(50, 30)
        self.rt_window.setFont(font)
        rt_layout = QtWidgets.QHBoxLayout()
        rt_text = QtWidgets.QLabel(self)
        rt_text.setText('s')
        rt_text.setFont(font)
        rt_layout.addWidget(self.rt_window)
        rt_layout.addWidget(rt_text)

        fragment_setting.addRow(fragment_label, fragment_layout)
        range_setting.addRow(rt_label, rt_layout)
        # range_setting.setLabelAlignment(Q)

        ok_button = QtWidgets.QPushButton('OK')
        ok_button.clicked.connect(self.fragment)
        ok_button.setFont(font)
        ok_button.resize(80, 80)  # 未生效

        para_layout = QtWidgets.QVBoxLayout()
        para_layout.addLayout(fragment_setting)
        para_layout.addLayout(range_setting)
        para_layout.addWidget(ok_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(files_layout)
        layout.addLayout(para_layout)
        self.setLayout(layout)

    def set_mzxml(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(None, None, None, 'mzxml(*.mzxml)')
        if file:
            self.mzxml_edit.setText(file)

    def set_subtracted(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(None, None, None, 'csv(*.csv)')
        if file:
            self.subtracted_edit.setText(file)

    def fragment(self):
        try:
            path1 = self.mzxml_edit.text()
            path2 = self.subtracted_edit.text()
            fragment = float(self.fragment_set.text())
            rt_win = float(self.rt_window.text())
            self.close()

            # TODO:结果为list，如何保存
            worker = Worker('Fragment feature matching...', obtain_MS2, path1)
            worker.signals.result.connect(partial(match_MS2, path2))
            worker.signals.close_signal.connect(worker.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker)
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def result_to_csv(self, name, df):
        # df.to_csv(name, index=False)
        # self.parent.list_of_processed.addFile(name)
        pass


class ProgressBarsListItem(QtWidgets.QWidget):
    def __init__(self, text, pb=None, parent=None):
        super().__init__(parent)
        self.pb = pb
        if self.pb is None:
            self.pb = QtWidgets.QProgressBar()

        self.label = QtWidgets.QLabel(self)
        self.label.setText(text)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self.label, 30)
        main_layout.addWidget(self.pb, 70)

        self.setLayout(main_layout)

    def setValue(self, value):
        self.pb.setValue(value)

    def setLabel(self, text):
        self.pb.setValue(0)
        self.label.setText(text)


class ProgressBarsList(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)

    def removeItem(self, item):
        self.layout().removeWidget(item)

    def addItem(self, item):
        self.layout().addWidget(item)


def construct_tic(path, label, mode, progress_callback=None):
    run = pymzml.run.Reader(path)
    t_measure = None
    time = []
    tic = []
    spectrum_count = run.get_spectrum_count()
    for i, scan in enumerate(run):
        if scan.ms_level == 1:
            tic.append(scan.TIC)  # get total ion of scan
            t, measure = scan.scan_time  # get scan time
            time.append(t)
            if not t_measure:
                t_measure = measure
            if progress_callback is not None and not i % 10:
                progress_callback.emit(int(i * 100 / spectrum_count))
    if t_measure == 'second':
        time = np.array(time) / 60
    return {'x': time, 'y': tic, 'label': label, 'mode': mode}


def construct_mzxml(path, label, mode, progress_callback=None):
    run = mzxml.read(path)
    time = []
    tic = []
    for i, scan in enumerate(run):
        if scan['msLevel'] == 1:
            tic.append(scan['totIonCurrent'])  # get total ion of scan
            t = scan['retentionTime']  # get scan time
            time.append(t)
    return {'x': time, 'y': tic, 'label': label, 'mode': mode}
