import numpy as np
import pandas as pd


def validation(result, ground, mz_tol, rt_tol):
    matchsum = 0
    match_mz = []
    result_val = pd.read_csv(result)
    ground_truth = pd.read_csv(ground)
    result_mz = result_val['mz'].unique()
    truth_mz = ground_truth['mz'].unique()
    for i in np.arange(len(truth_mz)):
        ind_test = np.where(
            (result_mz >= truth_mz[i] - truth_mz[i] * mz_tol) & (result_mz <= truth_mz[i] + truth_mz[i] * mz_tol))
        if np.size(ind_test) > 0:
            matchsum += 1
            match_mz.append(truth_mz[i])

    print('finding parent ion mz:', matchsum)
    print(match_mz)
    match = (matchsum, match_mz)

    return match
