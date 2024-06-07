#!/usr/bin/python
# -*- coding: gbk -*-

import pandas as pd
import numpy as np
import pyteomics.mzxml as mzxml

'''
1��Neutral Loss
2��MS/MS
3��d6
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
                rt_matched = rt[mass == p]  # �ҵ�����mz��ֵ������rt
                intensity_matched = intensity[mass == p]
                for m in np.unique(mass[ind_nl]):  # m=p+NL
                    rt_nl = rt[mass == m]  # m��rt
                    intensity_nl = intensity[mass == m]
                    # �ж�������m��p��rt��
                    condition = np.abs(rt_nl[np.argmax(intensity_nl)]-rt_matched[np.argmax(intensity_matched)])
                            
                    if condition <= rt_tol:
                        num_peak += 1
                        # �޸ģ����������ģ����ĸ��������ind_nl
                        matchmz.append(m)
                        rows_to_add.extend(ind_nl)
    nl_df = input_df.loc[rows_to_add]
    # print('num of peaks be found by neutral loss:', num_peak)
    # print('matched mass:', matchmz)
    return nl_df  # matchmz������֤


# -------------------prepare for plot MS/MS----------------------- #
def obtain_MS2(mzXML_file):
    run = mzxml.read(mzXML_file)
    RT = []
    MS2intensity_array = []
    MS2precusormz = []
    precursorScans = []
    MS2mz_array = []

    for spec in run:
        if spec['msLevel'] == 2:   # ��������Ϣ

            precursorScans.append(spec['precursorMz'][0]['precursorScanNum'])  # ��¼yһ����ͼid
            RT.append(spec['retentionTime'])  # ��¼����ʱ��
            MS2intensity_array.append(list(spec['intensity array']))  # ����ǿ��
            MS2mz_array.append(list(spec['m/z array']))  # ������
            MS2precusormz.append(spec['precursorMz'][0]['precursorMz'])
        
    # ����dataframe����
    output = pd.DataFrame({
        'MS1scan': precursorScans,
        'RT': RT,
        'intensity': MS2intensity_array,
        'MS2mz': MS2mz_array,
        'precusormz': MS2precusormz
    })
    return output


# ----------------------  function for  MS/MS matching----------------------- #
def match_all_MS2(rawdata, ms2_df, fragments, tol_mz=10e-6, tol_rt=30/60):  # ���߼�
    values_str = fragments.split(',')  # �������ַ�������Ӣ�Ķ��ŷָ�
    values = [float(num) for num in values_str]  # תΪ����
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

    # �Դ��������Ŀ��ֵ�������ݲ��ڵ� mz ֵ����¼
    for target in values:
        index = np.where(np.abs(ms2mz-target)/target < tol_mz)[0]  # ��ȡ���� target1 �� index list
        for ind in index:  # ��index list �е� index ��Ӧ�� mz �� rt ��ӵ�������
            mz_tar_list.append(new_ms2.loc[ind, 'precusormz'])
            rt_tar_list.append(new_ms2.loc[ind, 'RT'])
        mz_tar_tensor.append(mz_tar_list)  # �� target1 ��õ�mz��rtд��tensor�ĵ�һ��
        rt_tar_tensor.append(rt_tar_list)
        mz_tar_list = []  # ������飬������¼ target2 ��Ӧ��mz��rt��Ȼ����ӵ�tensor�ĵڶ��У��Դ�����
        rt_list = []

    num_rows = len(mz_tar_tensor)  # ��ȡtensor�е���������Ŀ��ֵ������
    len_first_row = len(mz_tar_tensor[0])  # ��ȡ��һ�еĳ���

    # ���� mz_tar_tensor ��һ���е�Ԫ�أ�������������Ƿ������ֵ
    for ind in range(len_first_row):  # ���� mz_tar_tensor ��һ���е�����
        element = mz_tar_tensor[0][ind]  # ��ȡ mz ֵ
        if all(element in mz_tar_tensor[row] for row in range(1, num_rows)):  # ��ֵ�Ƿ��������������ж�����
            mz_list.append(element)  # ����ֵ��ӵ� mz_list
            rt_list.append(rt_tar_tensor[0][ind])  # ����Ӧ��rt��ӵ�rt_list

    # ��� input_df �е� mz, RT �� intensity
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
    return nl_df  # np.unique(match_mz)������֤


def match_one_MS2(rawdata, ms2_df, fragments, tol_mz=10e-6, tol_rt=30/60):  # ���߼�
    values_str = fragments.split(',')
    values = [float(num) for num in values_str]
    ind_list = []
    rows_to_add = []
    all_tar = set()  # ����һ�������������������������mzֵ
    input_df = pd.read_csv(rawdata)
    new_left = ms2_df[['RT', 'intensity']].explode('intensity').reset_index(drop=True)
    new_right = ms2_df[['MS2mz', 'precusormz']].explode('MS2mz').reset_index(drop=True)
    new_ms2 = pd.concat([new_left, new_right], axis=1)
    new_ms2.columns = ['RT', 'intensity', 'MS2mz', 'precusormz']

    ms2mz = np.array(new_ms2['MS2mz'])
    precusormz = np.array(new_ms2['precusormz'])

    for target in values:  # ������ target ֵ���ҵ��������ݲΧ�ڵ�ֵ����ȡ����
        index = np.where(np.abs(ms2mz-target)/target < tol_mz)[0]
        ind_list.append(index)

    for ind in ind_list:  # ������������������������mzֵ��ӵ������У��γɲ���
        all_tar.update(precusormz[ind])

    exist_precmz = list(all_tar)  # �����ϸ�ʽת��Ϊlist
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
    return nl_df  # np.unique(match_mz)������֤


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
