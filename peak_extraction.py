#!/usr/bin/python
# -*- coding: gbk -*-

import pandas as pd
import numpy as np
import pyteomics.mzxml as mzxml

'''
1、Neutral Loss
2、MS/MS
3、d6
'''


# ------------function for checking neutral loss----------------------- #
def neut_loss(file, NL=63.96135, rt_tol=30/60, mz_tol=10e-6):
    input_df = pd.read_csv(file)

    mass = np.array(input_df['mz'])
    rt = np.array(input_df['RT'])
    intensity = np.array(input_df['intensity'])

    nlmass = mass-NL
    matchmz = []
    num_peak = 0
    rows_to_add = []
    for i in np.unique(nlmass[nlmass > 150]):
        ind_nl = np.where(nlmass == i)[0]
        ind_matched = np.where(np.abs(mass-i)/i <= mz_tol)[0]
        # print('matched mass:', np.unique(mass[ind_matched]))
        
        # if >2 matched
        if np.size(ind_matched) > 0:
            # print(len(mass[ind_matched]))
            for p in np.unique(mass[ind_matched]):
                rt_matched = rt[mass == p]  # 找到符合mz差值的所有rt
                intensity_matched = intensity[mass == p]
                for m in np.unique(mass[ind_nl]):  # m=p+NL
                    rt_nl = rt[mass == m]  # m的rt
                    intensity_nl = intensity[mass == m]
                    # 判断条件：m与p的rt差
                    condition = np.abs(rt_nl[np.argmax(intensity_nl)]-rt_matched[np.argmax(intensity_matched)])
                            
                    if condition <= rt_tol:
                        num_peak += 1
                        # 修改：符合条件的，获得母离子索引ind_nl
                        matchmz.append(m)
                        rows_to_add.extend(ind_nl)
    nl_df = input_df.loc[rows_to_add]
    # print('num of peaks be found by neutral loss:', num_peak)
    # print('matched mass:', matchmz)
    return nl_df  # matchmz用于验证


# -------------------prepare for plot MS/MS----------------------- #
def obtain_MS2(mzXML_file):
    run = mzxml.read(mzXML_file)
    RT = []
    MS2intensity_array = []
    MS2precusormz = []
    precursorScans = []
    MS2mz_array = []

    for spec in run:
        if spec['msLevel'] == 2:   # 二级谱信息

            precursorScans.append(spec['precursorMz'][0]['precursorScanNum'])  # 记录y一级谱图id
            RT.append(spec['retentionTime'])  # 记录保留时间
            MS2intensity_array.append(list(spec['intensity array']))  # 离子强度
            MS2mz_array.append(list(spec['m/z array']))  # 质量数
            MS2precusormz.append(spec['precursorMz'][0]['precursorMz'])
        
    # 构造dataframe数组
    output = pd.DataFrame({
        'MS1scan': precursorScans,
        'RT': RT,
        'intensity': MS2intensity_array,
        'MS2mz': MS2mz_array,
        'precusormz': MS2precusormz
    })
    return output


# ----------------------  function for  MS/MS matching----------------------- #
def match_all_MS2(rawdata, ms2_df, fragments, tol_mz=10e-6, tol_rt=30/60):  # 与逻辑
    values_str = fragments.split(',')  # 输入是字符串，按英文逗号分隔
    values = [float(num) for num in values_str]  # 转为浮点
    mz_tar_list = []
    mz_tar_tensor = []
    rt_tar_list = []
    rt_tar_tensor = []
    mz_list = []
    rt_list = []
    rows_to_add = []
    input_df = pd.read_csv(rawdata)
    new_left = ms2_df[['RT', 'intensity']].explode('intensity').reset_index(drop=True)
    new_right = ms2_df[['MS2mz', 'precusormz']].explode('MS2mz').reset_index(drop=True)
    new_ms2 = pd.concat([new_left, new_right], axis=1)
    new_ms2.columns = ['RT', 'intensity', 'MS2mz', 'precusormz']

    ms2mz = np.array(new_ms2['MS2mz'])

    # 对传入的所有目标值，查找容差内的 mz 值并记录
    for target in values:
        index = np.where(np.abs(ms2mz-target)/target < tol_mz)[0]  # 提取包含 target1 的 index list
        for ind in index:  # 将index list 中的 index 对应的 mz 和 rt 添加到数组中
            mz_tar_list.append(new_ms2.loc[ind, 'precusormz'])
            rt_tar_list.append(new_ms2.loc[ind, 'RT'])
        mz_tar_tensor.append(mz_tar_list)  # 将 target1 获得的mz和rt写到tensor的第一行
        rt_tar_tensor.append(rt_tar_list)
        mz_tar_list = []  # 清空数组，继续记录 target2 对应的mz和rt，然后添加到tensor的第二行，以此类推
        rt_list = []

    num_rows = len(mz_tar_tensor)  # 获取tensor中的行数（即目标值个数）
    len_first_row = len(mz_tar_tensor[0])  # 获取第一行的长度

    # 遍历 mz_tar_tensor 第一行中的元素，并检查其余行是否都有这个值
    for ind in range(len_first_row):  # 对于 mz_tar_tensor 第一行中的索引
        element = mz_tar_tensor[0][ind]  # 获取 mz 值
        if all(element in mz_tar_tensor[row] for row in range(1, num_rows)):  # 该值是否在所有其余行中都存在
            mz_list.append(element)  # 将该值添加到 mz_list
            rt_list.append(rt_tar_tensor[0][ind])  # 将对应的rt添加到rt_list

    # 获得 input_df 中的 mz, RT 和 intensity
    mz_den = np.array(input_df['mz'])
    rt_den = np.array(input_df['RT'])
    intensity_den = np.array(input_df['intensity'])
    match_mz = []
    for i in np.arange(len(mz_list)):
        ind = np.where(np.abs(mz_den - mz_list[i])/mz_list[i] < tol_mz)[0]
        if np.size(ind) >= 1:
            # for p in np.arange(len(ind)):
            #     temp_inten = np.array(intensity_den[ind][p][1:-1].split(','), dtype=np.float64)
            #     max_rt = np.array(rt_den[ind][p][1:-1].split(','), dtype=np.float64)[np.argmax(temp_inten)]
            inten = intensity_den[ind]
            max_rt = rt_den[ind][np.argmax(inten)]
            if np.abs(max_rt - rt_list[i]) <= tol_rt:
                match_mz.extend(mz_den[ind])
                rows_to_add.extend(ind)
    nl_df = input_df.loc[rows_to_add]
    return nl_df  # np.unique(match_mz)用于验证


def match_one_MS2(rawdata, ms2_df, fragments, tol_mz=10e-6, tol_rt=30/60):  # 或逻辑
    values_str = fragments.split(',')
    values = [float(num) for num in values_str]
    ind_list = []
    rows_to_add = []
    all_tar = set()  # 创建一个集合来存放所有满足条件的mz值
    input_df = pd.read_csv(rawdata)
    new_left = ms2_df[['RT', 'intensity']].explode('intensity').reset_index(drop=True)
    new_right = ms2_df[['MS2mz', 'precusormz']].explode('MS2mz').reset_index(drop=True)
    new_ms2 = pd.concat([new_left, new_right], axis=1)
    new_ms2.columns = ['RT', 'intensity', 'MS2mz', 'precusormz']

    ms2mz = np.array(new_ms2['MS2mz'])
    precusormz = np.array(new_ms2['precusormz'])

    for target in values:  # 对所有 target 值，找到数据中容差范围内的值，获取索引
        index = np.where(np.abs(ms2mz-target)/target < tol_mz)[0]
        ind_list.append(index)

    for ind in ind_list:  # 对所有满足条件的索引，将mz值添加到数集中，形成并集
        all_tar.update(precusormz[ind])

    exist_precmz = list(all_tar)  # 将集合格式转化为list
    mz_list = np.array(ms2_df[ms2_df['precusormz'].isin(exist_precmz)]['precusormz'])
    rt_list = np.array(ms2_df[ms2_df['precusormz'].isin(exist_precmz)]['RT'])

    mz_den = np.array(input_df['mz'])
    rt_den = np.array(input_df['RT'])
    intensity_den = np.array(input_df['intensity'])
    match_mz = []
    for i in np.arange(len(mz_list)):
        ind = np.where(np.abs(mz_den - mz_list[i])/mz_list[i] < tol_mz)[0]
        if np.size(ind) >= 1:
            # for p in np.arange(len(ind)):
            #     temp_inten = np.array(intensity_den[ind][p][1:-1].split(','), dtype=np.float64)
            #     max_rt = np.array(rt_den[ind][p][1:-1].split(','), dtype=np.float64)[np.argmax(temp_inten)]
            inten = intensity_den[ind]
            max_rt = rt_den[ind][np.argmax(inten)]
            if np.abs(max_rt - rt_list[i]) <= tol_rt:
                match_mz.extend(mz_den[ind])
                rows_to_add.extend(ind)
    nl_df = input_df.loc[rows_to_add]
    return nl_df  # np.unique(match_mz)用于验证


# ------------- main ----------------#
# t0 = time.time()
# matched_mass = neut_loss(data)
# t1 = time.time()
# print('time of checking neutral loss:', t1-t0)
#
# ms2_sample = obtain_MS2(mzXML_list[2])
# t2 = time.time()
# print('time of obtain MS2:', t2-t1)
#
# matched_from_ms2 = match_MS2(data, ms2_sample)
# t3 = time.time()
# print('time of matched ms2:', t3-t2)
#
# truth = pd.read_csv('ground_truth.csv')
# t_mass = np.array(truth['mz'])
#
# tol = 10e-6
# matchsum = 0
# match_mz = []
# for i in np.arange(len(t_mass)):
#      ind_test = np.where((matched_from_ms2 >= t_mass[i]-t_mass[i]*tol)&(matched_from_ms2 <= t_mass[i]+t_mass[i]*tol))
#      if np.size(ind_test) > 0:
#          matchsum += 1
#          match_mz.append(t_mass[i])
# print('total of match:', matchsum)
# print(match_mz)
