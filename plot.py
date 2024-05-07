import functools
from functools import partial
from PyQt5 import QtWidgets, QtCore, QtGui
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from utils.threading import Worker
from df_process_test import construct_df
import pymzml
import pyteomics.mzxml as mzxml
from preprocess import defect_process, obtain_MS1, RT_screening, mz_screening, intens_screening, mass_def, bin_peaks, check_rep_var
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
        return plotted, filename

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


class ParameterWindow1(QtWidgets.QDialog):
    def __init__(self, sample, blank, parent: PlotWindow):
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
            lower_rt = float(self.lower_rt.text())
            upper_rt = float(self.upper_rt.text())
            lower_mz = float(self.lower_mz.text())
            upper_mz = float(self.upper_mz.text())
            lower_mass = float(self.lower_mass.text())
            upper_mass = float(self.upper_mass.text())
            mass_tolerance = float(self.mass_tolerance.text())
            intensity_thd = float(self.intensity_thd.text())
            self.close()

            # pd = QtWidgets.QProgressDialog(self)
            # pd.setWindowTitle("Please wait...")
            # pd.setLabelText('Processing...')
            # pd.setCancelButton(None)
            # pd.setRange(0, 0)
            # pd.show()

            worker1 = Worker('processing sample...', defect_process, self.sample, lower_rt, upper_rt,
                             lower_mz, upper_mz, intensity_thd, lower_mass, upper_mass)
            worker1.signals.result.connect(partial(self.result_to_csv, 'sample_pre.csv'))
            worker1.signals.close_signal.connect(worker1.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker1)

            worker2 = Worker('processing blank...', defect_process, self.blank, lower_rt, upper_rt,
                             lower_mz, upper_mz, intensity_thd, lower_mass, upper_mass)
            worker2.signals.result.connect(partial(self.result_to_csv, 'blank_pre.csv'))
            worker2.signals.close_signal.connect(worker2.progress_dialog.close)  # 连接关闭信号到关闭进度条窗口函数
            self._thread_pool.start(worker2)

            # TODO:处理完成，导出CSV并添加到processed_list
            # obj_sample = construct_df(sample_pre, label='Sample Processed')
            print('end')
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()

    def result_to_csv(self, name, df):
        df.to_csv(name)
        self.parent.list_of_processed.addFile(name)


class ParameterWindow2(QtWidgets.QDialog):
    def __init__(self, sample, blank, parent: PlotWindow):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowTitle('Background denoise option')
        self.sample = sample
        self.blank = blank

        # 字体设置
        font = QtGui.QFont()
        font.setFamily('Arial')
        font.setBold(True)
        font.setPixelSize(15)
        font.setWeight(75)

        range_setting = QtWidgets.QFormLayout()

        rt_label = QtWidgets.QLabel("RT window")
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

        mz_label = QtWidgets.QLabel("m/z window")
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

        ratio_setting = QtWidgets.QFormLayout()
        ratio_setting.alignment()

        ratio_label = QtWidgets.QLabel("Sample/Blank Ratio")
        ratio_label.setFont(font)
        self.ratio = QtWidgets.QLineEdit()
        self.ratio.setText('10')
        self.ratio.setFixedSize(60, 30)
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

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(range_setting)
        layout.addLayout(ratio_setting)
        layout.addWidget(ok_button)
        self.setLayout(layout)

    def denoise(self):
        try:
            lower_rt = float(self.lower_rt.text())
            upper_rt = float(self.upper_rt.text())
            lower_mz = float(self.lower_mz.text())
            upper_mz = float(self.upper_mz.text())
            ratio = float(self.ratio.text())
            self.close()
            pass
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Check parameters, something is wrong!")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.exec_()


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
