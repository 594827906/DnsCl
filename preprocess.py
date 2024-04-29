#!/usr/bin/python
# -*- coding: gbk -*-

import os
import glob
import pandas as pd
import numpy as np
import pyteomics.mzxml as mzxml

# file_path = r'C:\坚果云\02-研究课题\0000-CODE\Python\myproject\DnsCl设计\软件设计数据验证-20240403'
# file_path = r'C:\John\DnsCl\软件设计数据验证-20240403'
# mzXML_list=glob.glob(os.path.join(file_path,'*.mzXML'))

# run = mzxml.read(mzXML_list[0])
# spect1=next(run)  # 查看第一个质谱
# print(spect1.keys()) # 查看一个质谱中的信息
# print(spect1['num'])
# print(spect1['m/z array'])
# print(spect1['intensity array'])
# print(spect1['totIonCurrent'])
#

##-----------output MS1 spectra--------------#
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
        if spec['msLevel'] == 1:   # 一级谱信息
            scan = scan + 1
            scans.extend(np.tile(scan, len(spec['m/z array'])))  # 记录谱图id
            RT.extend(np.tile(spec['retentionTime'],len(spec['m/z array'])))   # 记录保留时间
            intensity.extend(spec['intensity array'])           # 离子强度
            mz.extend(spec['m/z array'])                # 质量数
 
    # 构造dataframe数组
    output = pd.DataFrame({
        'scan': scans,
        'RT': RT,
        'intensity': intensity,
        'mz': mz
    })
    print("Parsed MS1 spectra from file {0}".format(mzXML_file))
    return output


##------------RT screening----------#
def RT_screening(input_df, lower_rt, upper_rt):
    # 设置RT筛选条件
    condition = (input_df['RT'] >= lower_rt) & (input_df['RT'] <= upper_rt)
    filtered_df = input_df[condition]
    df = filtered_df.reset_index(drop=True)
    return df

##------------mz screening---------------#
def mz_screening(input_df,lower_mz,upper_mz):
    # 设置mz筛选条件
    condition = (input_df['mz'] >= lower_mz) & (input_df['mz'] <= upper_mz)
    filtered_df = input_df[condition]
    df = filtered_df.reset_index(drop=True)
    return df

##-----------intensity screening----------#
def intens_screening(input_df, lower_inten):
    # 设置mz筛选条件
    condition = input_df['intensity'] >= lower_inten

    filtered_df = input_df[condition]
    df = filtered_df.reset_index(drop=True)
    return df

##-------------mass defect limit ---------#
def mass_def(input_df, lower_mass = 600, upper_mass=1000):
    # 设置mass defect 筛选条件
    condition = ((input_df['mz'] * 1000) % 1000 >= lower_mass) & ((input_df['mz'] * 1000) % 1000 < upper_mass)
    
    indexes_to_drop = input_df[condition].index
    filtered_df = input_df.drop(indexes_to_drop)
    df = filtered_df.reset_index(drop=True)
    return df


#---------repeatability and variability-----------#
## ----------binning first------##
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
    # dev = d_mass/mass[:-1]  # devation from previous mass

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
        l_mass = mass[left:(gap_idx+1)]
        l_mean_mass = np.mean(l_mass)
        # further splitting needed？
        if any(abs(l_mass - l_mean_mass)/l_mean_mass) > tol:
            current_boundary = current_boundary + 1
            boundary_left[current_boundary] = left
            boundary_right[current_boundary] = gap_idx
        else:
            mass[left:(gap_idx+1)] = np.mean(l_mass)

        # right side
        r_mass = mass[(gap_idx+1):(right+1)]
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


##--------------check repeatability and variability--------------#
def check_rep_var(input_df, n_scans=10, rep_ratio=0.7, var_ratio=0.1):
    # grouping mass
    grouped_data = input_df.groupby('mz')
    merge_df = pd.DataFrame()
    for name, group in grouped_data:
        # each name is a bin of mass, each group is a dataframe of a bin
        data = group.sort_values(by='scan')  # 对scan排序
        intensity = np.array(data['intensity'])
        scan = np.array(data['scan'])
        # if this mass existed beyond 70% of n_scans
        if len(scan) > n_scans:
            d_scan = np.diff(scan)
            one_locations = np.where(d_scan == 1)[0]
            consecutive_lengths = np.split(one_locations, np.where(np.diff(one_locations) != 1)[0]+1)
            length_one = [len(length) for length in consecutive_lengths]
            if np.any(np.array(length_one) >= n_scans * rep_ratio) & ((max(intensity)-min(intensity))/min(intensity) > var_ratio):
                # print('mz', name)
                # print(data.head(3))
                merge_df = pd.concat([merge_df, data], axis=0)
    return merge_df


##-------------import ----------------#
# blank = obtain_MS1(mzXML_list[0])
# sample = obtain_MS1(mzXML_list[2])
#
# #step-1: rt
# print("Start to RT screening...")
# sample_rt = RT_screening(sample,lower_rt=2.5,upper_rt=30.0)
# blank_rt = RT_screening(blank,lower_rt=2.5,upper_rt=30.0)
#
# #step-2: mz
# print(" mass screening...")
# sample_mz = mz_screening(sample_rt,lower_mz=150.0,upper_mz=1000.0)
# blank_mz = mz_screening(blank_rt,lower_mz=150.0,upper_mz=1000.0)
#
# # step-3: intensity
# print("set the intensity threshold...")
# sample_intensity = intens_screening(sample_mz, lower_inten=10000)
# blank_intensity = intens_screening(blank_mz,lower_inten=10000)
#
# # step-4: mass defect limit
# print('perform mass defect limit....')
# sample_mdl = mass_def(sample_intensity)
# blank_mdl = mass_def(blank_intensity)
#
# # step-5: binning
# print('mass binning.....')
# sample_bin = bin_peaks(sample_mdl)
# blank_bin = bin_peaks(blank_mdl)
#
# # step-6: repeatability and variability checking
# print('check the repeatability and variablity....')
# sample_pre = check_rep_var(sample_bin)
# blank_pre = check_rep_var(blank_bin)
#
# sample_pre.to_csv('sample_pre.csv')
# blank_pre.to_csv('blank_pre.csv')
#
# print('Preprocess completed!')
# def preprocess(input):
#     # input file should be a DataFrame
#     s1 = RT_screening(input, lower_rt=2.5, upper_rt=30.0)
#     s2 = mz_screening(s1, lower_mz=150.0, upper_mz=1000.0)
#     s3 = intens_screening(s2, lower_inten=10000)
#     s4 = mass_def(s3)
#     s5 = bin_peaks(s4)
#     s6 = check_rep_var(s5)

#     return s6

# sample_pre = preprocess(sample)
# blank_pre = preprocess(blank)

def defect_process(file, lower_rt, upper_rt, lower_mz, upper_mz, intensity_thd, lower_mass, upper_mass):
    df = obtain_MS1(file)
    df = RT_screening(df, lower_rt=lower_rt, upper_rt=upper_rt)
    df = mz_screening(df, lower_mz=lower_mz, upper_mz=upper_mz)
    df = intens_screening(df, lower_inten=intensity_thd)
    df = mass_def(df, lower_mass=lower_mass, upper_mass=upper_mass)
    df = bin_peaks(df)
    df = check_rep_var(df)
    return df
