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


##------------function for checking neutral loss-----------------------#
def neut_loss(file, NL=63.96135, rt_tol=30/60, mz_tol=10e-6):
    input_df = pd.read_csv(file)

    mass = np.array(input_df['mz'])
    rt = np.array(input_df['RT'])
    intensity = np.array(input_df['intensity (Sample)'])

    nlmass = mass-NL
    matchmz = []
    num_peak = 0
    for i in np.unique(nlmass[nlmass > 150]):
        ind_nl = np.where(nlmass == i)[0]
        ind_matched = np.where(np.abs(i-mass)/i <= mz_tol)[0]       
        # print('matched mass:',np.unique(mass[ind_matched]))
        
        # if >2 matched
        if np.size(ind_matched) > 0:
            # print(len(mass[ind_matched]))
            for p in np.unique(mass[ind_matched]):
                rt_matched = rt[mass == p]
                intensity_matched = intensity[mass == p]

                # 字符串列表转为数值
                for l in np.arange(len(rt_matched)):
                    f_rt_matched = np.array(rt_matched[l][1:-1].split(','), dtype=np.float64)
                    f_intensity_matched = np.array(intensity_matched[l][1:-1].split(','), dtype=np.float64)

                    for m in mass[ind_nl]:
                        rt_nl = rt[mass == m]
                        intensity_nl = intensity[mass == m]

                        for n in np.arange(len(rt_nl)):
                                
                            # 字符串列表转为数值
                            f_rt_nl = np.array(rt_nl[n][1:-1].split(','), dtype=np.float64)
                            f_intensity_nl = np.array(intensity_nl[n][1:-1].split(','), dtype=np.float64)

                            # 判断条件
                            condition = np.abs(f_rt_nl[np.argmax(f_intensity_nl)]-f_rt_matched[np.argmax(f_intensity_matched)])
                            
                            if condition <= rt_tol:
                                num_peak += 1
                                matchmz.append(p)
    print('num of peaks be found by neutral loss:', num_peak)
    print('matched mass:', matchmz)
    return matchmz


##-------------------prepare for plot MS/MS-----------------------#
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


##----------------------  function for  MS/MS matching-----------------------#
def match_MS2(rawdata, ms2_df, tol_mz=10e-6, tol_rt=30/60, tar1=171.10425, tar2=156.08153):
    input_df = pd.read_csv(rawdata)
    new_left = ms2_df[['RT', 'intensity']].explode('intensity').reset_index(drop=True)
    new_right = ms2_df[['MS2mz', 'precusormz']].explode('MS2mz').reset_index(drop=True)
    new_ms2 = pd.concat([new_left, new_right], axis=1)
    new_ms2.columns = ['RT', 'intensity', 'MS2mz', 'precusormz']

    ms2mz = np.array(new_ms2['MS2mz'])
    precusormz = np.array(new_ms2['precusormz'])

    ind1 = np.where(np.abs(ms2mz-tar1)/tar1 < tol_mz)[0]
    ind2 = np.where(np.abs(ms2mz-tar2)/tar2 < tol_mz)[0]

    exist_precmz = np.unique(np.union1d(precusormz[ind1], precusormz[ind2]))
    mz_list = np.array(ms2_df[ms2_df['precusormz'].isin(exist_precmz)]['precusormz'])
    rt_list = np.array(ms2_df[ms2_df['precusormz'].isin(exist_precmz)]['RT'])

    mz_den = np.array(input_df['mz'])
    rt_den = np.array(input_df['RT'])
    intensity_den = np.array(input_df['intensity (Sample)'])
    match_mz = []
    for i in np.arange(len(mz_list)):

        ind = np.where(np.abs(mz_den - mz_list[i])/mz_list[i] < tol_mz)
        if np.size(ind) >= 1:
            # print(ind)
            for p in np.arange(len(ind)):
                temp_inten = np.array(intensity_den[ind][p][1:-1].split(','), dtype=np.float64)
                max_rt = np.array(rt_den[ind][p][1:-1].split(','), dtype=np.float64)[np.argmax(temp_inten)]

                if np.abs(max_rt-rt_list[i]) <= tol_rt:
                    match_mz.append(mz_den[ind][p])

    return match_mz


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


    








