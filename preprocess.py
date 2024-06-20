#!/usr/bin/python
# -*- coding: gbk -*-

import pandas as pd
import numpy as np
import pyteomics.mzxml as mzxml
import math
import time


# -----------output MS1 spectra-------------- #
def obtain_MS1(mzXML_file):
    run = mzxml.read(mzXML_file)
    RT = []
    intensity = []
    mz = []
    scans = []
    scan = 0

    # 读一级谱，output RT, intensity, scans
    for spec in run:
        # print("Spectrum {0}, MS level {ms_level} @ RT {scan_time:1.2f}".format(
        #     spec['num'], ms_level=spec['msLevel'], scan_time=spec['retentionTime']))
        if spec['msLevel'] == 1:  # 一级谱信息
            scan = scan + 1
            scans.extend(np.tile(scan, len(spec['m/z array'])))  # 记录谱图id
            RT.extend(np.tile(spec['retentionTime'], len(spec['m/z array'])))  # 记录保留时间
            intensity.extend(spec['intensity array'])  # 离子强度
            mz.extend(spec['m/z array'])  # 质量数

    # 构造dataframe数组
    output = pd.DataFrame({
        'scan': scans,
        'RT': RT,
        'intensity': intensity,
        'mz': mz
    })
    print("Parsed MS1 spectra from file {0}".format(mzXML_file))
    return output


# ------------RT screening---------- #
def RT_screening(input_df, lower_rt, upper_rt):
    # 设置RT筛选条件
    condition = (input_df['RT'] >= lower_rt) & (input_df['RT'] <= upper_rt)
    filtered_df = input_df[condition]
    df = filtered_df.reset_index(drop=True)
    return df


# ------------mz screening--------------- #
def mz_screening(input_df, lower_mz, upper_mz):
    # 设置mz筛选条件
    condition = (input_df['mz'] >= lower_mz) & (input_df['mz'] <= upper_mz)
    filtered_df = input_df[condition]
    df = filtered_df.reset_index(drop=True)
    return df


# -----------intensity screening---------- #
def intens_screening(input_df, lower_inten):
    # 设置mz筛选条件
    condition = input_df['intensity'] >= lower_inten

    filtered_df = input_df[condition]
    df = filtered_df.reset_index(drop=True)
    return df


# -------------mass defect limit --------- #
def mass_def(input_df, lower_mass=600, upper_mass=1000):
    # 设置mass defect 筛选条件
    condition = ((input_df['mz'] * 1000) % 1000 >= lower_mass) & ((input_df['mz'] * 1000) % 1000 < upper_mass)

    indexes_to_drop = input_df[condition].index
    filtered_df = input_df.drop(indexes_to_drop)
    df = filtered_df.reset_index(drop=True)
    return df


# ---------repeatability and variability----------- #
# ----------binning first------ #
def bin_peaks(input_df, tol=10e-6):
    data = input_df.sort_values(by='mz')  # 排序
    RT = np.array(data['RT'])
    mass = np.array(data['mz'])
    intensity = np.array(data['intensity'])
    scan = np.array(data['scan'])

    # bin peak
    n = len(mass)
    # calculate difference
    d_mass = np.diff(mass)
    # dev = d_mass/mass[:-1]  # deviation from previous mass

    # Initialization
    n_boundaries = max(1000, np.floor(3 * np.log(n)))
    boundary_left = [0] * int(n_boundaries)
    boundary_right = [0] * int(n_boundaries)
    current_boundary = 0
    boundary_left[current_boundary] = 0
    boundary_right[current_boundary] = n - 1

    while current_boundary >= 0:
        # find largest gap
        left = boundary_left[current_boundary]
        right = boundary_right[current_boundary]
        current_boundary = current_boundary - 1
        gaps = d_mass[left:right]
        gap_idx = np.argmax(gaps) + left

        # left side
        l_mass = mass[left:(gap_idx + 1)]
        l_mean_mass = np.mean(l_mass)
        # further splitting needed？
        if any(abs(l_mass - l_mean_mass) / l_mean_mass) > tol:
            current_boundary = current_boundary + 1
            boundary_left[current_boundary] = left
            boundary_right[current_boundary] = gap_idx
        else:
            mass[left:(gap_idx + 1)] = np.mean(l_mass)

        # right side
        r_mass = mass[(gap_idx + 1):(right + 1)]
        r_mean_mass = np.mean(r_mass)
        # further splitting needed?
        if any(abs(r_mass - r_mean_mass) / r_mean_mass > tol):
            current_boundary = current_boundary + 1
            boundary_left[current_boundary] = gap_idx + 1
            boundary_right[current_boundary] = right
        else:
            mass[(gap_idx + 1):(right + 1)] = r_mean_mass

    output = pd.DataFrame({
        'scan': scan,
        'RT': RT,
        'intensity': intensity,
        'mz': mass
    })
    return output


# --------------check repeatability and variability-------------- #
# -------function for each group------ #
def refine_group(onegroup, n_scan=10, n_rep=7, var_ratio=0.1):
    # each name is a bin of mass, each group is a dataframe of a bin
    data = onegroup.sort_values(by='scan')  # 对scan排序
    intensity = np.array(data['intensity'])
    scan = np.array(data['scan'])
    rt = np.array(data['RT'])
    mass = np.array(data['mz'])
    # feat_labels = np.array(data['label'])
    update_data = pd.DataFrame()
    # if this mass existed on 7 scans of range 10
    reset_scan = scan - np.min(scan)
    tag = np.array([False] * (np.max(scan) - np.min(scan) + 1))
    tag[reset_scan] = True
    neigh = math.ceil(n_scan / 2)
    #  retain_ind = []  # the scan index satisfied the repeatability
    if len(scan) >= n_scan:
        # 以n_scan+1的窗口长度对tag求和，再挑出 >n_rep的位置
        tag = np.concatenate([np.array([False] * neigh), tag, np.array([False] * neigh)])
        cumulative_sum = np.cumsum(tag)
        window_size = n_scan + 1
        sliding_sums = cumulative_sum[window_size - 1:] - np.concatenate([[0], cumulative_sum[:-window_size]])
        intersection = np.intersect1d(np.where(sliding_sums > n_rep)[0], reset_scan)
        retain_ind = np.where(np.isin(reset_scan, intersection))[0]

        # check variability
        if np.size(retain_ind) > 0:
            scan4var = scan[retain_ind]
            intensity4var = intensity[retain_ind]
            rt4var = rt[retain_ind]
            mass4var = mass[retain_ind]
            # feat_labels = feat_labels[retain_ind]
            # print('mass to be retained:', np.unique(mass[retain_ind]))

            # labeling each features[0 0 0 0 0 1 1 1 1 2 2 2 2 2...]
            mask = np.zeros(len(scan4var), dtype=bool)
            ind2reset = np.where(np.diff(scan4var) > n_scan)[0] + 1  # distance of two peaks are beyond 10 scans
            mask[ind2reset] = True
            feat_labels = np.cumsum(mask)

            for i in np.unique(feat_labels):
                test_intensity = intensity4var[feat_labels == i]

                if (np.max(test_intensity) - np.min(test_intensity)) / np.min(test_intensity) > var_ratio:
                    temp = pd.DataFrame({
                        'label': np.array(feat_labels[feat_labels == i]),
                        'scan': scan4var[feat_labels == i],
                        'RT': rt4var[feat_labels == i],
                        'mz': mass4var[feat_labels == i],
                        'intensity': test_intensity
                    })
                    update_data = pd.concat([update_data, temp], ignore_index=True)

        return update_data


def check_rep_var(input_df):
    # initial peak label
    input_df['label'] = np.array([0] * len(input_df))
    t0 = time.time()
    # grouping mass
    grouped_data = input_df.groupby('mz').apply(refine_group)
    t1 = time.time()
    print("mz group", t1 - t0)
    return grouped_data


def defect_process(file, lower_rt, upper_rt, lower_mz, upper_mz, intensity_thd, lower_mass, upper_mass, mass_tol):
    df = obtain_MS1(file)
    df = RT_screening(df, lower_rt=lower_rt, upper_rt=upper_rt)
    df = mz_screening(df, lower_mz=lower_mz, upper_mz=upper_mz)
    df = intens_screening(df, lower_inten=intensity_thd)
    df = mass_def(df, lower_mass=lower_mass, upper_mass=upper_mass)
    df = bin_peaks(df, tol=mass_tol)
    df = check_rep_var(df)
    return df
