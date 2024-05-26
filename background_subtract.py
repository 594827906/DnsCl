#!/usr/bin/python
# -*- coding: gbk -*-
"""
1、增加一个函数，将匹配的mz导出为list形式。每一行存储一个mz，intensity和rt
2、解决csv存储时，数据截厨问题
"""
import pandas as pd
import numpy as np


def denoise_bg(blank, sample, tol_mass=10e-6, tol_rt=30/60, inten_ratio=10):
    blk_df = pd.read_csv(blank)
    sam_df = pd.read_csv(sample)

    mass_blk = np.array(blk_df['mz'])
    mass_blk_uni = np.unique(mass_blk)  # list of mz in blank
    rt_blk = np.array(blk_df['RT'])
    peaklab_blk = np.array(blk_df['peakLabel'])
    intensity_blk = np.array(blk_df['intensity'])

    mass_sam = np.array(sam_df['mz'])
    mass_sam_uni = np.unique(mass_sam)  # list of mz in sample
    rt_sam = np.array(sam_df['RT'])
    peaklab_sam = np.array(sam_df['peakLabel'])
    intensity_sam = np.array(sam_df['intensity'])
    scan_sam = np.array(sam_df['scan'], dtype=np.int32)

    record_mass1 = []
    record_mass2 = []
    rt_max = []
    rt_min = []
    area_sam = []
    area_blk = []
    area_ratio = []
    rt_list = []
    intensity_matched_sam = []
    intensity_matched_blk = []
    plab_matched = []
    scan_list = []
    num_peak = 0

    for i in np.arange(len(mass_sam_uni)):

        ind_of_sample = np.where(mass_sam == mass_sam_uni[i])[0]  # index of a unique mz on sample
        lower_bound = mass_sam_uni[i] - mass_sam_uni[i] * tol_mass
        upper_bound = mass_sam_uni[i] + mass_sam_uni[i] * tol_mass
        is_in_range = np.any((mass_blk_uni >= lower_bound) & (mass_blk_uni <= upper_bound))
        plab_sample = peaklab_sam[ind_of_sample]
        # print('peaklabel of sample:', np.unique(plab_sample))

        if not is_in_range:  # if unmatch

            for p in np.unique(plab_sample):
                num_peak += 1
                record_mass1.append(np.median(mass_sam[ind_of_sample][plab_sample == p]))
                record_mass2.append(np.median(mass_sam[ind_of_sample][plab_sample == p]))
                rt_max.append(np.max(rt_sam[ind_of_sample][plab_sample == p]))
                rt_min.append(np.min(rt_sam[ind_of_sample][plab_sample == p]))
                area_sam.append(np.sum(intensity_sam[ind_of_sample][plab_sample == p]))
                area_blk.append(1)
                area_ratio.append(np.sum(intensity_sam[ind_of_sample][plab_sample == p]))
                rt_list.append(list(rt_sam[ind_of_sample][plab_sample == p]))
                intensity_matched_sam.append(list(intensity_sam[ind_of_sample][plab_sample == p]))
                intensity_matched_blk.append(1)
                scan_list.append(list(scan_sam[ind_of_sample][plab_sample == p]))
                plab_matched.append(num_peak)

        else:  # if match
            # ind possibly exist 2 values
            ind_all = np.where((mass_blk_uni >= lower_bound) & (mass_blk_uni <= upper_bound))[0]
            for j in range(len(mass_blk_uni[ind_all])):

                ind_of_blank = np.where(mass_blk == mass_blk_uni[ind_all][j])
                plab_blank = peaklab_blk[ind_of_blank]
                # print('peaklabel of blank:',np.unique(plab_blank))

                for p in np.unique(plab_sample):
                    sum_area_blk = 0
                    temp_intense = []
                    temp_rt = []
                    for m in np.unique(plab_blank):
                        max_ind_sample = np.argmax(intensity_sam[ind_of_sample][plab_sample == p])
                        max_ind_blank = np.argmax(intensity_blk[ind_of_blank][plab_blank == m])

                        condition = np.abs(rt_blk[ind_of_blank][plab_blank == m][max_ind_blank] -
                                           rt_sam[ind_of_sample][plab_sample == p][max_ind_sample])  # peak deviation

                        if condition <= tol_rt:
                            sum_area_blk = sum_area_blk + np.sum(intensity_blk[ind_of_blank][plab_blank == m])  # 面积求和
                            temp_rt.extend(rt_blk[ind_of_blank][plab_blank == m])
                            temp_intense.extend(intensity_blk[ind_of_blank][plab_blank == m])

                    if sum_area_blk != 0:
                        SB_ratio = np.sum(
                            intensity_sam[ind_of_sample][plab_sample == p]) / sum_area_blk  # ratio of area

                        if SB_ratio >= inten_ratio:
                            # print('matched mz in sample:',
                            #       np.round(np.median(mass_sam[ind_of_sample][plab_sample == p]), 5),
                            #       '||matched mz in blank:', np.round(np.median(mass_blk[ind_of_blank]), 5))
                            record_mass1.append(np.median(mass_sam[ind_of_sample][plab_sample == p]))
                            rt_max.append(np.max(rt_sam[ind_of_sample][plab_sample == p]))
                            rt_min.append(np.min(rt_sam[ind_of_sample][plab_sample == p]))
                            area_sam.append(np.sum(intensity_sam[ind_of_sample][plab_sample == p]))
                            area_blk.append(sum_area_blk)
                            area_ratio.append(SB_ratio)

                    if np.sum(temp_intense) > 0 and np.sum(intensity_sam[ind_of_sample][plab_sample == p]) / np.sum(
                            temp_intense) > inten_ratio:
                        # print('matched mz in sample:',
                        #       np.round(np.median(mass_sam[ind_of_sample][plab_sample == p]), 5),
                        #       '|| matched mz in blank:',
                        #       np.round(np.median(mass_blk[ind_of_blank][plab_blank == m]), 5))
                        num_peak += 1
                        record_mass2.append(np.median(mass_sam[ind_of_sample][plab_sample == p]))
                        rt_list.append(list(rt_sam[ind_of_sample][plab_sample == p]))
                        scan_list.append(list(scan_sam[ind_of_sample][plab_sample == p]))
                        intensity_matched_sam.append(list(intensity_sam[ind_of_sample][plab_sample == p]))
                        intensity_matched_blk.append(temp_intense)
                        plab_matched.append(num_peak)

    output1 = pd.DataFrame({
        'RT_min': np.round(np.array(rt_min), 3),
        'RT_max': np.round(np.array(rt_max), 3),
        'mz': np.round(np.array(record_mass1), 5),
        'Area (Blank)': area_blk,
        'Area (Sample)': area_sam,
        'Area Ratio': area_ratio
    })
    output1.to_csv('denoise_final_list.csv', index=False)

    output2 = pd.DataFrame({
        'Label_peak': plab_matched,
        'mz': np.round(np.array(record_mass2), 5),
        'intensity (Sample)': intensity_matched_sam,
        'intensity (Blank)': intensity_matched_blk,
        'RT': rt_list,
        'scan': scan_list,
    })
    output2.to_csv('denoise_intermediate.csv', index=False)  # 用于后续处理的中间文件
    return output2

# read preprocessed data
# pd.set_option('display.max_colwidth',None)  # 无法解决省略号的问题

# blank = pd.read_csv('blank_pre.csv')
# sample = pd.read_csv('sample_pre.csv')

# t0 = time.time()
# denoise_Area = denoise_bg(blank, sample)
# denoise_Area.to_csv('denoise_Area.csv', index=False)
# t1 = time.time()
# print('background subtraction:', t1-t0)
#
#
# denoise_peaklist = denoise_bg_list(blank, sample)
# denoise_peaklist.to_csv('denoise_peaklist.csv', index=False)
# # 保存到csv文件时，列宽受限，数据会被截断，中间出现省略号，将元素数列从ndarray格式转成list，解决这个问题!
# t2 = time.time()
# print('output peaklist of background subtraction:', t2-t1)
#
# # 验证
# truth = pd.read_csv('ground_truth.csv')
# mass = np.array(truth['mz'])
# mass_test = np.array(denoise_Area['mz'])
# tol = 10e-6
# matchsum=0
# match_mz = []
# for i in np.arange(len(mass)):
#      ind_test = np.where((mass_test >= mass[i]-mass[i]*tol) & (mass_test <= mass[i]+mass[i]*tol))
#      if np.size(ind_test) > 0:
#          matchsum += 1
#          match_mz.append(mass[i])
# print('total of match:', matchsum)
