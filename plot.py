from functools import partial
from PyQt5 import QtWidgets, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from utils.threading import Worker
import pymzml
import numpy as np


class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self._thread_pool = QtCore.QThreadPool()
        self._pb_list = ProgressBarsList(self)
        self._plotted_list = []
        self._plotted_list = []

        self._feature_parameters = None

        self._figure = plt.figure()
        self.fig_sample = self._figure.add_subplot(211)  # plot sample
        self.fig_sample.ticklabel_format(axis='y', scilimits=(0, 0))
        self.fig_blank = self._figure.add_subplot(212)  # plot blank
        self.fig_blank.ticklabel_format(axis='y', scilimits=(0, 0))
        self.fig_blank.set_xlabel('Retention time [min]')
        self._figure.tight_layout()
        self._label2line = dict()  # a label (aka line name) to plotted line
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)

    # def run_thread(self, caption: str, worker: Worker, text=None, icon=None):
    #     # pb = ProgressBarsListItem(caption, parent=self._pb_list)
    #     self._pb_list.addItem(pb)
    #     worker.signals.progress.connect(pb.setValue)
    #     worker.signals.operation.connect(pb.setLabel)
    #     worker.signals.finished.connect(partial(self._threads_finisher,
    #                                             text=text, icon=icon, pb=pb))
    #     self._thread_pool.start(worker)

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

    # def button_press(self, event):  # 右键清空画布
    #     if event.button == 1:
    #         print('1')
    #     if event.button == 2:
    #         print('2')
    #     if event.button == 3:
    #         print('3')
    #         print(self._plotted_list, 'event in')
    #         self.fig_sample.cla()
    #         self._label2line.clear()
    #         self._plotted_list.clear()
    #         print(self._plotted_list, 'event end')
    #         self._canvas.draw_idle()

    def plotter(self, obj):
        # if not self._label2line:  # in case if 'feature' was plotted
        if obj['mode'] == 'sample':
            self._figure.delaxes(self.fig_sample)
            self.fig_sample = self._figure.add_subplot(211)
            self.fig_sample.set_title('Sample')
            # self.fig_sample.set_xlabel('Retention time [min]')
            self.fig_sample.set_ylabel('Intensity')
            self.fig_sample.ticklabel_format(axis='y', scilimits=(0, 0))  # 使用科学计数法
            line = self.fig_sample.plot(obj['x'], obj['y'], label=obj['label'])
            self.fig_sample.legend(loc='best')
            self.fig_sample.grid(alpha=0.8)
        if obj['mode'] == 'blank':
            self._figure.delaxes(self.fig_blank)
            self.fig_blank = self._figure.add_subplot(212)
            self.fig_blank.set_title('Blank')
            self.fig_blank.set_xlabel('Retention time [min]')
            self.fig_blank.set_ylabel('Intensity')
            self.fig_blank.ticklabel_format(axis='y', scilimits=(0, 0))  # 使用科学计数法
            line = self.fig_blank.plot(obj['x'], obj['y'], label=obj['label'])
            self.fig_blank.legend(loc='best')
            self.fig_blank.grid(alpha=0.8)

        self._label2line[obj['label']] = line[0]  # save line
        self._figure.tight_layout()
        # self._figure.canvas.mpl_connect('scroll_event', self.scroll_event)  # 鼠标滚轮缩放画布
        # self._figure.canvas.mpl_connect('button_press_event', self.button_press)  # 右键清空画布
        self._canvas.draw()

    def close_file(self, item):
        self._list_of_files.deleteFile(item)

    def get_selected_files(self):
        return self._list_of_files.selectedItems()

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

    def plot_tic(self, file, mode):
        label = f'{file}'
        plotted = False
        if label not in self._label2line:
            path = self._list_of_files.file2path[file]
            construct_tic(path, label, mode)
            pb = ProgressBarsListItem(f'Plotting: {file}', parent=self._pb_list)
            self._pb_list.addItem(pb)
            worker = Worker(construct_tic, path, label, mode)
            worker.signals.progress.connect(pb.setValue)
            worker.signals.result.connect(self.plotter)
            worker.signals.finished.connect(partial(self._threads_finisher, pb=pb))

            self._thread_pool.start(worker)

            self._plotted_list.append(label)

            plotted = True
        return plotted, label

    def delete_line(self, label):
        self.fig_sample.cla()
        self._label2line.clear()
        # self.sample_plotted_list.clear()
        self._plotted_list.remove(label)  # delete item from list
        self._canvas.draw_idle()

    def refresh_canvas(self):
        if self._label2line:
            self.fig_sample.legend(loc='best')
            self.fig_sample.relim()  # recompute the ax.dataLim
            self.fig_sample.autoscale_view()  # update ax.viewLim using the new dataLim
            self.fig_blank.legend(loc='best')
            self.fig_blank.relim()  # recompute the ax.dataLim
            self.fig_blank.autoscale_view()  # update ax.viewLim using the new dataLim
        else:
            self._figure.clear()
            self.fig_sample = self._figure.add_subplot(211)
            self.fig_sample.set_xlabel('Retention time [min]')
            # self.fig_sample.set_ylabel('Intensity')
            self.fig_sample.ticklabel_format(axis='y', scilimits=(0, 0))
            self.fig_blank = self._figure.add_subplot(212)
            self.fig_blank.set_xlabel('Retention time [min]')
            # self.fig_blank.set_ylabel('Intensity')
            self.fig_blank.ticklabel_format(axis='y', scilimits=(0, 0))
        self._canvas.draw()


class EICParameterWindow(QtWidgets.QDialog):
    def __init__(self, parent: PlotWindow):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowTitle('EIC plot option')

        mz_layout = QtWidgets.QHBoxLayout()
        mz_label = QtWidgets.QLabel(self)
        mz_label.setText('m/z=')
        self.mz_getter = QtWidgets.QLineEdit(self)
        self.mz_getter.setText('100.000')
        mz_layout.addWidget(mz_label)
        mz_layout.addWidget(self.mz_getter)

        delta_layout = QtWidgets.QHBoxLayout()
        delta_label = QtWidgets.QLabel(self)
        delta_label.setText('delta=±')
        self.delta_getter = QtWidgets.QLineEdit(self)
        self.delta_getter.setText('0.005')
        delta_layout.addWidget(delta_label)
        delta_layout.addWidget(self.delta_getter)

        plot_button = QtWidgets.QPushButton('Plot')
        plot_button.clicked.connect(self.plot)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(mz_layout)
        layout.addLayout(delta_layout)
        layout.addWidget(plot_button)
        self.setLayout(layout)

    def plot(self):
        try:
            mz = float(self.mz_getter.text())
            delta = float(self.delta_getter.text())
            for file in self.parent.get_selected_files():
                file = file.text()
                self.parent.plot_eic(file, mz, delta)
            self.close()
        except ValueError:
            # popup window with exception
            msg = QtWidgets.QMessageBox(self)
            msg.setText("'m/z' and 'delta' should be float numbers!")
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
