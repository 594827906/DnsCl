#!/usr/bin/python
# -*- coding: gbk -*-
import pandas as pd
import numpy as np
import time


def denoise_bg(blank, sample, tol_mass=10e-6, tol_rt=30/60, inten_ratio=10):
    blk_df = pd.read_csv(blank)
    sam_df = pd.read_csv(sample)
    t0 = time.time()
    mass_blk = np.array(blk_df['mz'])
    mass_blk_uni = np.unique(mass_blk)  # list of mz in blank
    rt_blk = np.array(blk_df['RT'])
    peaklab_blk = np.array(blk_df['peakLabel'])
    intensity_blk = np.array(blk_df['intensity'])
    scan_blk = np.array(blk_df['scan'])

    mass_sam = np.array(sam_df['mz'])
    mass_sam_uni = np.unique(mass_sam)  # list of mz in sample
    rt_sam = np.array(sam_df['RT'])
    label_sam = np.array(sam_df['peakLabel'])
    intensity_sam = np.array(sam_df['intensity'])
    scan_sam = np.array(sam_df['scan'])

    retain_scan = []
    record_mass = []
    record_rt = []
    record_intensity = []

    for i in np.arange(len(mass_sam_uni)):

        ind_of_sample = np.where(mass_sam == mass_sam_uni[i])[0]  # index of a unique mz on sample
        lower_bound = mass_sam_uni[i] - mass_sam_uni[i] * tol_mass
        upper_bound = mass_sam_uni[i] + mass_sam_uni[i] * tol_mass
        is_in_range = np.any((mass_blk_uni >= lower_bound) & (mass_blk_uni <= upper_bound))  # ��mz��blank�д����ݲ��ڵ�ֵ
        # print('peaklabel of sample:', np.unique(plab_sample))

        if not is_in_range:  # ���blankû�У�ֱ�����
            # print('inexistent within blank',scan_sam[ind_of_sample])
            retain_scan.extend(scan_sam[ind_of_sample])
            record_mass.extend(mass_sam[ind_of_sample])
            record_rt.extend(rt_sam[ind_of_sample])
            record_intensity.extend(intensity_sam[ind_of_sample])

        else:
            # ��mz��blank�д����ݲ��ڵ�ֵ���ܲ�ֹһ��
            ind_all = np.where((mass_blk_uni >= lower_bound) & (mass_blk_uni <= upper_bound))[0]
            for j in range(len(mass_blk_uni[ind_all])):

                ind_of_blank = np.where(mass_blk == mass_blk_uni[ind_all][j])

                rtlist_sam = rt_sam[ind_of_sample]
                rtlist_blk = rt_blk[ind_of_blank]
                lowerbound_rtlist = rtlist_sam - tol_rt
                upperbound_rtlist = rtlist_sam + tol_rt

                for m in np.arange(len(ind_of_sample)):
                    matched_sam = np.where((rtlist_sam >= lowerbound_rtlist[m]) & (rtlist_sam <= upperbound_rtlist[m]))[0]
                    matched_blk = np.where((rtlist_blk >= lowerbound_rtlist[m]) & (rtlist_blk <= upperbound_rtlist[m]))[0]

                    if len(matched_blk) > 0:
                        if np.max(intensity_sam[ind_of_sample][matched_sam])/np.max(intensity_blk[ind_of_blank][matched_blk]) >= inten_ratio:
                            # print('match_scan_sample=',scan_sam[ind_of_sample][matched_sam],'match_scan_blank=',scan_blk[ind_of_blank][matched_blk])
                            # print('mass=',np.round(mass_sam_uni[i],5),'scan=',int(scan_sam[ind_of_sample][m]))
                            # print('match_scan_blank=',scan_blk[ind_of_blank][matched_blk])
                            retain_scan.append(scan_sam[ind_of_sample][m])
                            record_mass.append(mass_sam_uni[i])
                            record_rt.append(rt_sam[ind_of_sample][m])
                            record_intensity.append(intensity_sam[ind_of_sample][m])

                    else:  # if unmatched
                        # print('match_scan_blank=',scan_blk[ind_of_blank][matched_blk])
                        retain_scan.append(scan_sam[ind_of_sample][m])
                        record_mass.append(mass_sam_uni[i])
                        record_rt.append(rt_sam[ind_of_sample][m])
                        record_intensity.append(intensity_sam[ind_of_sample][m])

    output = pd.DataFrame({
        'label': 0,
        'scan': retain_scan,
        'RT': np.round(record_rt, 4),
        'mz': np.round(record_mass, 5),
        'intensity': record_intensity
    })

    # output['label'] = 0
    label = 0
    # unique_mz = output['mz'].unique()  # ��ȡΨһ��mzֵ
    t1 = time.time()
    # v1:����ÿһ�У���ʱ155��
    # for i in range(1, len(output)):
    #     if output.loc[i, 'mz'] != output.loc[i - 1, 'mz']:  # �����ǰ�е�mz��ǰһ�в�ͬ��label+1
    #         if (output.loc[i, 'mz'] - output.loc[i - 1, 'mz']) > tol_mass:  # ��һ�����б�Ҫ����
    #             label += 1
    #     elif output.loc[i, 'scan'] - output.loc[i - 1, 'scan'] > 10:  # �����ǰ�е�scan��ǰһ�е�scan��ֵ����n��label+1
    #         label += 1
    #     output.loc[i, 'peakLabel'] = label  # ���µ�ǰ�е�label

    # v2:��mz������������и��Ǳ�ǩ����ʱ126��
    grouped = output.groupby('mz')
    for name, group in grouped:
        output.loc[group.index, 'label'] = label
        # v3:�����ҵ��ϵ���ʣ��labelͳһ���£������������ӷ�����ʱ61��
        for i in range(1, len(group)):
            if group.iloc[i]['scan'] - group.iloc[i - 1]['scan'] > 5:
                label += 1
                output.loc[group.index[i:], 'label'] = label
        label += 1  # ÿ��mz�����������label
    t2 = time.time()
    print('processing:', t1-t0)
    print('peak picking:', t2-t1)
    return output


# read preprocessed data

# blank = pd.read_csv('blank_pre.csv')
# sample = pd.read_csv('sample_pre.csv')

# t0 = time.time()
# denoise_Area = denoise_bg(blank, sample)
# denoise_Area.to_csv('denoise_Area.csv', index=False)
# t1 = time.time()
# print('background subtraction:', t1-t0)
# denoise_peaklist = denoise_bg_list(blank, sample)
# denoise_peaklist.to_csv('denoise_peaklist.csv', index=False)
# # ���浽csv�ļ�ʱ���п����ޣ����ݻᱻ�ضϣ��м����ʡ�Ժţ���Ԫ�����д�ndarray��ʽת��list������������!
# t2 = time.time()
# print('output peaklist of background subtraction:', t2-t1)
#
# # ��֤
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
