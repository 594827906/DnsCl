from PyQt5 import QtCore, QtWidgets


class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.

    Attributes
    ----------
    finished : QtCore.pyqtSignal
        No data
    error : QtCore.pyqtSignal
        `tuple` (exc type, value, traceback.format_exc() )
    result : QtCore.pyqtSignal
        `object` data returned from processing, anything
    progress : QtCore.pyqtSignal
        `int` indicating % progress
    download_progress : QtCore.pyqtSignal
        `int`, `int`, `int` used to show a count of blocks transferred,
        a block size in bytes, the total size of the file
    """
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)  # 定义一个信号，用于发送结果
    close_signal = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int)
    operation = QtCore.pyqtSignal(str)
    download_progress = QtCore.pyqtSignal(int, int, int)


class Worker(QtCore.QRunnable):
    """
    Worker thread

    Parameters
    ----------
    function : callable
        Any callable object

    Attributes
    ----------
    mode : str
        A one of two 'all in one' of 'sequential'

    """
    def __init__(self, mode, function, *args, multiple_process=False, **kwargs):
        super(Worker, self).__init__()

        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.mode = mode
        self.progress_dialog = QtWidgets.QProgressDialog()
        self.progress_dialog.setRange(0, 0)  # 设置进度条范围为0到0，表示一个不确定的进度条
        self.progress_dialog.setLabelText(self.mode)  # 设置进度条文本
        self.progress_dialog.show()

        # Add the callback to our kwargs
        # self.kwargs['progress_callback'] = self.signals.progress

        if multiple_process:
            self.kwargs['operation_callback'] = self.signals.operation

    @QtCore.pyqtSlot()
    def run(self):
        result = self.function(*self.args, **self.kwargs)
        self.signals.result.emit(result)  # return results
        # self.signals.finished.emit()  # done
        # self.progress_dialog.close()
        self.signals.close_signal.emit()
