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

    mass = input_df['mz'].unique()
    rt = np.array(input_df['RT'])
    intensity = np.array(input_df['intensity'])

    matchmz = []
    indices_to_record = []
    num_peak = 0

    for mz in mass:
        mass_nl = mz - NL

        # �ҵ����� mz=mass_nl��mz_tol �������в���ȡlabel��mz_tol�ǰٷֱȣ���
        condition_nl = (input_df['mz'] >= mass_nl - mass_nl*mz_tol) & (input_df['mz'] <= mass_nl + mass_nl*mz_tol)
        labels_nl = input_df[condition_nl]['label'].unique()

        # �ҵ����� mz=mass �������в���ȡlabel
        condition_mass = input_df['mz'] == mz
        labels_mass = input_df[condition_mass]['label'].unique()

        if len(labels_nl) > 0:  # ����������Զ�ʧֵ������RT�ж�
            # ����ÿ��label�飬�ҵ�intensity���ֵ����RT
            max_intensity_rt_nl = {}
            for label in labels_nl:
                sub_df = input_df[input_df['label'] == label]
                max_intensity_row = sub_df.loc[sub_df['intensity'].idxmax()]
                max_intensity_rt_nl[label] = max_intensity_row['RT']

            max_intensity_rt_mass = {}
            for label in labels_mass:
                sub_df = input_df[input_df['label'] == label]
                max_intensity_row = sub_df.loc[sub_df['intensity'].idxmax()]
                max_intensity_rt_mass[label] = max_intensity_row['RT']

            # �Ա� RT ��ֵ�������ֵС�� rt_tol�����¼��һmz��label�������е� index
            for l_mass in labels_mass:
                for l_nl in labels_nl:
                    rt_diff = abs(max_intensity_rt_mass[l_mass] - max_intensity_rt_nl[l_nl])
                    if rt_diff < rt_tol:
                        indices_to_record.extend(input_df[input_df['label'] == l_mass].index.tolist())

    nl_df = input_df.loc[indices_to_record]
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
def match_all_MS2(rawdata, ms2_df, fragments, mz_tol=10e-6, tol_rt=30/60):  # ���߼�
    values_str = fragments.split(',')  # �������ַ�������Ӣ�Ķ��ŷָ�
    values = [float(num) for num in values_str]  # תΪ����
    mz_tar_list = []
    mz_tar_tensor = []
    rt_tar_list = []
    rt_tar_tensor = []
    mz_list = []
    rt_list = []
    rows_to_add = set()
    input_df = pd.read_csv(rawdata)
    new_left = ms2_df[['RT', 'intensity']].explode('intensity').reset_index(drop=True)
    new_right = ms2_df[['MS2mz', 'precusormz']].explode('MS2mz').reset_index(drop=True)
    new_ms2 = pd.concat([new_left, new_right], axis=1)
    new_ms2.columns = ['RT', 'intensity', 'MS2mz', 'precusormz']

    ms2mz = np.array(new_ms2['MS2mz'])

    # �Դ��������Ŀ��ֵ�������ݲ��ڵ� mz ֵ����¼
    for target in values:
        index = np.where(np.abs(ms2mz-target)/target < mz_tol)[0]  # ��ȡ���� target1 �� index list
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

    match_mz = []
    for i in np.arange(len(mz_list)):
        condition = ((input_df['mz'] >= mz_list[i] - mz_list[i] * mz_tol) &
                     (input_df['mz'] <= mz_list[i] + mz_list[i] * mz_tol))
        matched_label = input_df[condition]['label'].unique()
        # ind = np.where(np.abs(mass - mz_list[i])/mz_list[i] < mz_tol)[0]
        if np.size(matched_label) > 0:
            for labels in matched_label:
                sub_df = input_df[input_df['label'] == labels]
                max_intensity_row = sub_df.loc[sub_df['intensity'].idxmax()]
                max_rt = max_intensity_row['RT']
                if np.abs(max_rt - rt_list[i]) <= tol_rt:
                    mz = sub_df['mz'].unique()
                    match_mz.extend(mz)
                    rows_to_add.update(input_df[input_df['label'] == labels].index.tolist())
    indices_to_record = list(rows_to_add)
    fragment_df = input_df.loc[indices_to_record]
    fragment_df = fragment_df.sort_values(by=['mz', 'scan']).reset_index(drop=True)
    return fragment_df  # np.unique(match_mz)������֤


def match_one_MS2(rawdata, ms2_df, fragments, mz_tol=10e-6, tol_rt=30/60):  # ���߼�
    values_str = fragments.split(',')
    values = [float(num) for num in values_str]
    ind_list = []
    rows_to_add = set()
    all_tar = set()  # ����һ�������������������������mzֵ
    input_df = pd.read_csv(rawdata)
    new_left = ms2_df[['RT', 'intensity']].explode('intensity').reset_index(drop=True)
    new_right = ms2_df[['MS2mz', 'precusormz']].explode('MS2mz').reset_index(drop=True)
    new_ms2 = pd.concat([new_left, new_right], axis=1)
    new_ms2.columns = ['RT', 'intensity', 'MS2mz', 'precusormz']

    ms2mz = np.array(new_ms2['MS2mz'])
    precusormz = np.array(new_ms2['precusormz'])

    for target in values:  # ������ target ֵ���ҵ��������ݲΧ�ڵ�ֵ����ȡ����
        index = np.where(np.abs(ms2mz-target)/target < mz_tol)[0]
        ind_list.append(index)

    for ind in ind_list:  # ������������������������mzֵ��ӵ������У��γɲ���
        all_tar.update(precusormz[ind])

    exist_precmz = list(all_tar)  # �����ϸ�ʽת��Ϊlist
    mz_list = np.array(ms2_df[ms2_df['precusormz'].isin(exist_precmz)]['precusormz'])
    rt_list = np.array(ms2_df[ms2_df['precusormz'].isin(exist_precmz)]['RT'])

    match_mz = []
    for i in np.arange(len(mz_list)):
        condition = ((input_df['mz'] >= mz_list[i] - mz_list[i] * mz_tol) &
                     (input_df['mz'] <= mz_list[i] + mz_list[i] * mz_tol))
        matched_label = input_df[condition]['label'].unique()
        # ind = np.where(np.abs(mass - mz_list[i])/mz_list[i] < mz_tol)[0]
        if np.size(matched_label) > 0:
            for labels in matched_label:
                sub_df = input_df[input_df['label'] == labels]
                max_intensity_row = sub_df.loc[sub_df['intensity'].idxmax()]
                max_rt = max_intensity_row['RT']
                if np.abs(max_rt - rt_list[i]) <= tol_rt:
                    mz = sub_df['mz'].unique()
                    match_mz.extend(mz)
                    rows_to_add.update(input_df[input_df['label'] == labels].index.tolist())
    indices_to_record = list(rows_to_add)
    fragment_df = input_df.loc[indices_to_record]
    fragment_df = fragment_df.sort_values(by=['mz', 'scan']).reset_index(drop=True)
    return fragment_df  # np.unique(match_mz)������֤

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
