import collections
from typing import List, Set, Dict

import pandas as pd

debug = False


class UnequalException(Exception):
    pass


def is_placeholder(val, placeholders: List[str]):
    return isinstance(val, str) and any(val.startswith(i) or i in val for i in placeholders)


def idx_match(t, r, phs: List[str]):
    try:
        if isinstance(t, tuple) and isinstance(r, tuple):
            #  Multi-index
            if len(t) != len(r):
                return False

            return all(is_placeholder(i, phs) or is_placeholder(j, phs) or i == j for i, j in zip(t, r))

        return is_placeholder(t, phs) or is_placeholder(r, phs) or t == r

    except Exception as e:
        import logging
        logging.exception(e)
        exit()
        return False


def get_col_mappings(target: pd.DataFrame, result: pd.DataFrame, phs: List[str]):
    if len(result.columns) < len(target.columns):
        raise UnequalException

    mappings = {}
    for idx, col in enumerate(target.columns):
        mappings[idx] = {r_idx for r_idx, r_val in enumerate(result.columns)
                         if idx_match(col, r_val, phs)}

    if any(len(i) == 0 for i in mappings.values()):
        raise UnequalException

    if len(set.union(*mappings.values())) < len(target.columns):
        raise UnequalException

    return mappings


def get_idx_mappings(target: pd.DataFrame, result: pd.DataFrame, phs: List[str], ignore_row_ordering: bool = False):
    if len(result.index) < len(target.index):
        raise UnequalException

    mappings = {}
    for idx, col in enumerate(target.index):
        mappings[idx] = {r_idx for r_idx, r_val in enumerate(result.index)
                         if idx_match(col, r_val, phs) or ignore_row_ordering}

    if any(len(i) == 0 for i in mappings.values()):
        raise UnequalException

    if len(set.union(*mappings.values())) < len(target.index):
        raise UnequalException

    return mappings


def check_value_mappings(target: pd.DataFrame, result: pd.DataFrame, phs: List[str],
                         col_mappings: Dict[int, Set[int]], idx_mappings: Dict[int, Set[int]]):
    real_col_result = collections.defaultdict(set)
    real_idx_result = collections.defaultdict(set)

    for i in range(result.shape[0]):
        for j in range(result.shape[1]):
            val = result.iloc[i, j]
            if not is_placeholder(val, phs):
                real_idx_result[val].add(i)
                real_col_result[val].add(j)

    for i in range(target.shape[0]):
        for j in range(target.shape[1]):
            val = target.iloc[i, j]
            if not is_placeholder(val, phs):
                orig = set(col_mappings[j])
                col_mappings[j] &= real_col_result[val]
                idx_mappings[i] &= real_idx_result[val]
                if len(col_mappings[j]) == 0 or len(idx_mappings[i]) == 0:
                    if debug:
                        print(i, j, col_mappings, orig, idx_mappings, real_col_result[val], real_idx_result[val])
                    raise UnequalException

    if len(set.union(*idx_mappings.values())) < len(target.index):
        raise UnequalException

    if len(set.union(*col_mappings.values())) < len(target.columns):
        raise UnequalException

    return True


def check_result(target: pd.DataFrame, result: pd.DataFrame, placeholders: List[str] = None,
                 ignore_row_ordering: bool = False) -> bool:
    if placeholders is None:
        placeholders = ["_COL", "_IDX", "_CELL", "MORPH"]

    try:
        col_mappings = get_col_mappings(target, result, placeholders)
        idx_mappings = get_idx_mappings(target, result, placeholders, ignore_row_ordering=ignore_row_ordering)
        return check_value_mappings(target, result, placeholders, col_mappings, idx_mappings)

    except UnequalException:
        return False
