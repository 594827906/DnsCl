import pandas as pd
import matplotlib.pyplot as plt
from preprocess import obtain_MS1, RT_screening, mz_screening, intens_screening, mass_def, bin_peaks, check_rep_var

# file_path = r'D:\Bionet\DnsCl\软件设计数据验证-20240403\STD+BP+DNS.mzXML'
# sample = obtain_MS1(file_path)
# sample_rt = RT_screening(sample, lower_rt=2.5, upper_rt=30.0)
# sample_mz = mz_screening(sample_rt, lower_mz=150.0, upper_mz=1000.0)
# sample_intensity = intens_screening(sample_mz, lower_inten=10000)
# sample_mdl = mass_def(sample_intensity)
# sample_bin = bin_peaks(sample_mdl)
# sample_pre = check_rep_var(sample_bin)

# print(sample_pre.loc[0])

path = r'D:\Bionet\DnsCl\sample_pre.csv'


def construct_df(file):
    time = []
    tic = []
    sample_pre = pd.read_csv(file)
    df = sample_pre.sort_values(['scan', 'mz'])  # 按指定列排序
    # scan_column = df['scan']
    max_scan = df.iloc[-1]['scan']  # 获取最大scan数
    max_scan = max_scan.astype(int)
    for scan in range(1, max_scan):
        print('scan = ', scan)
        if (df['scan'] == scan).any():
            tot_intensity = df.loc[df['scan'] == scan, 'intensity'].sum()
            print('intensity = ', tot_intensity)
            tic.append(tot_intensity)  # get total ion of scan
            t = df.loc[df['scan'] == scan, 'RT'].values[0]  # get scan time
            time.append(t)
            print('time = ', t)
        else:
            tic.append(0)  # get total ion of scan
            time.append(0)
        # if progress_callback is not None and not i % 10:
        #     progress_callback.emit(int(i * 100 / spectrum_count))
    return {'x': time, 'y': tic, 'label': file}


obj = construct_df(path)
print(obj)

# TODO: debugging
fig = plt.figure()
fig.delaxes(fig)
fig.ticklabel_format(axis='y', scilimits=(0, 0))  # 使用科学计数法
fig = plt.figure(obj['x'], obj['y'], label=obj['label'])
fig.legend(loc='best')
fig.grid(alpha=0.8)
