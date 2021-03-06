from __future__ import division
import pandas as pd
import sys
from os import listdir
from random import shuffle
from sklearn.tree import DecisionTreeRegressor
from policies import policy1, policy2
import numpy as np
import time
import matplotlib.pyplot as plt



class solution_holder:
    def __init__(self, id, decisions, objective, rank):
        self.id = id
        self.decision = decisions
        self.objective = objective
        self.rank = rank


def split_data(filename):
    pdcontent = pd.read_csv(filename)
    indepcolumns = [col for col in pdcontent.columns if "$<" not in col]
    depcolumns = [col for col in pdcontent.columns if "$<" in col]
    sortpdcontent = pdcontent.sort_values(by=depcolumns[-1])
    content = list()
    ranks = {}
    for i, item in enumerate(sorted(set(sortpdcontent[depcolumns[-1]].tolist()))):
        ranks[item] = i
    for c in xrange(len(sortpdcontent)):
        content.append(solution_holder(
                                       c,
                                       sortpdcontent.iloc[c][indepcolumns].tolist(),
                                       sortpdcontent.iloc[c][depcolumns].tolist(),
                                       ranks[sortpdcontent.iloc[c][depcolumns].tolist()[-1]]
                                       )
                       )

    shuffle(content)
    indexes = range(len(content))
    train_indexes, validation_indexes, test_indexes = indexes[:int(0.4*len(indexes))], indexes[int(.4*len(indexes)):int(.6*len(indexes))],  indexes[int(.6*len(indexes)):]
    assert(len(train_indexes) + len(validation_indexes) + len(test_indexes) == len(indexes)), "Something is wrong"
    train_set = [content[i] for i in train_indexes]
    validation_set = [content[i] for i in validation_indexes]
    test_set = [content[i] for i in test_indexes]

    return [train_set, validation_set, test_set]


def mre_progressive(train, test, threshold=0.1):
    train_independent = [t.decision for t in train]
    train_dependent = [t.objective[-1] for t in train]

    test_independent = [t.decision for t in test]
    test_dependent = [t.objective[-1] for t in test]

    model = DecisionTreeRegressor()
    model.fit(train_independent, train_dependent)
    predicted = model.predict(test_independent)

    mre = []
    for org, pred in zip(test_dependent, predicted):
        mre.append(abs(org - pred)/ abs(org))
    return np.mean(mre)


def rank_progressive(train, test, threshold=4):
    train_independent = [t.decision for t in train]
    train_dependent = [t.objective[-1] for t in train]

    sorted_test = sorted(test, key=lambda x: x.objective[-1])
    for r,st in enumerate(sorted_test): st.rank = r
    test_independent = [t.decision for t in sorted_test]
    test_dependent = [t.objective[-1] for t in sorted_test]

    model = DecisionTreeRegressor()
    model.fit(train_independent, train_dependent)
    predicted = model.predict(test_independent)
    predicted_id = [[i,p] for i,p in enumerate(predicted)]
    predicted_sorted = sorted(predicted_id, key=lambda x: x[-1])
    # assigning predicted ranks
    predicted_rank_sorted = [[p[0], p[-1], i] for i,p in enumerate(predicted_sorted)]
    rank_diffs = [abs(p[0] - p[-1]) for p in predicted_rank_sorted]
    return np.mean(rank_diffs)


def wrapper_rank_progressive(train_set, validation_set):
    initial_size = 10
    training_indexes = range(len(train_set))
    shuffle(training_indexes)
    sub_train_set = [train_set[i] for i in training_indexes[:initial_size]]
    steps = 0
    rank_diffs = []
    while (initial_size+steps) < len(train_set) - 1:
        rank_diffs.append(rank_progressive(sub_train_set, validation_set))
        policy_result = policy1(rank_diffs)
        if policy_result != -1: break
        steps += 1
        sub_train_set.append(train_set[initial_size+steps])

    return sub_train_set


def wrapper_mre_progressive(train_set, validation_set, threshold=0.1):
    initial_size = 10
    training_indexes = range(len(train_set))
    shuffle(training_indexes)
    sub_train_set = [train_set[i] for i in training_indexes[:initial_size]]
    steps = 0
    while (initial_size+steps) < len(train_set) - 1:
        mre_returned = mre_progressive(sub_train_set, validation_set)
        if mre_returned < threshold: break
        steps += 1
        sub_train_set.append(train_set[initial_size+steps])

    return sub_train_set


def find_lowest_rank(train, test, bracket=10):
    # Test data
    train_independent = [t.decision for t in train]
    train_dependent = [t.objective[-1] for t in train]

    sorted_test = sorted(test, key=lambda x: x.objective[-1])
    for r, st in enumerate(sorted_test): st.rank = r
    test_independent = [t.decision for t in sorted_test]
    test_dependent = [t.objective[-1] for t in sorted_test]

    model = DecisionTreeRegressor()
    model.fit(train_independent, train_dependent)
    predicted = model.predict(test_independent)

    predicted_id = [[i, p] for i, p in enumerate(predicted)]
    predicted_sorted = sorted(predicted_id, key=lambda x: x[-1])
    # assigning predicted ranks
    predicted_rank_sorted = [[p[0], p[-1], i] for i,p in enumerate(predicted_sorted)]
    select_few = predicted_rank_sorted[:10]
    return [sf[0] for sf in select_few]



if __name__ == "__main__":
    datafolder = "./Data/"
    evals_dict = {}
    rank_diffs_dict = {}
    stats_dict = {}
    files = [datafolder + f for f in listdir(datafolder)]
    for file in files:
        print file
        evals_dict[file] = []
        rank_diffs_dict[file] = []
        stats_dict[file] = {}
        rank_rank_diffs = []
        rank_evals = []
        for _ in xrange(20):
            print "+ ",
            datasets = split_data(file)
            train_set = datasets[0]
            validation_set = datasets[1]
            test_set = datasets[2]
            sub_train_set_rank = wrapper_rank_progressive(train_set, validation_set)
            lowest_rank = find_lowest_rank(sub_train_set_rank, test_set)
            len_rank_train_set =  len(sub_train_set_rank)
            min_rank_prog = min(lowest_rank)
            rank_rank_diffs.append(min_rank_prog)
            rank_evals.append(len_rank_train_set + len(validation_set) + 10)

        evals_dict[file] = rank_evals
        rank_diffs_dict[file] = rank_rank_diffs
        stats_dict[file]["mean_rank_diff"] = np.mean(rank_rank_diffs)
        stats_dict[file]["std_rank_diff"] = np.std(rank_rank_diffs)
        stats_dict[file]["mean_evals"] = np.mean(rank_evals)
        stats_dict[file]["std_evals"] = np.std(rank_evals)


    import pickle
    pickle.dump(evals_dict, open("./PickleLocker/Progressive_Rank_Evals.p", "w"))
    pickle.dump(rank_diffs_dict, open("./PickleLocker/Progressive_Rank_Rank_Diff.p", "w"))
    pickle.dump(stats_dict, open("./PickleLocker/Progressive_Rank_Stats.p", "w"))






