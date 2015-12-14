from collections import defaultdict
import re


tree = lambda: defaultdict(tree)


def all_int(xs):
    result = False
    try:
        [isinstance(a, int) or int(a) for a in xs]
        result = True
    except Exception:
        result = False
    return result


def get_by_path(d, *path):
    for k in path:
        d = d[k]
    return d


def create_by_path(d, value, *path):
    for i, k in enumerate(path):
        is_last_element = (i + 1 == len(path))
        normalized_key = k
        try:
            normalized_key = int(k)
        except ValueError:
            pass
        if is_last_element:
            d[normalized_key] = value
        else:
            d = d[normalized_key]
    return d


def default_to_regular(d):
    if isinstance(d, defaultdict):
        d = {k: default_to_regular(v) for k, v in d.items()}
    return d


def to_dict_with_lists(d):
    result = d
    if isinstance(d, dict):
        if all_int(d.keys()):
            result = [to_dict_with_lists(v) for v in d.values()]
        else:
            result = {k: to_dict_with_lists(v) for k, v in d.items()}
    return result


def transform_name(name):
    name = re.sub(r'_#{[a-zA-Z0-9]+:(\d+)}', r'__\1', name)
    name = re.sub(r':choice_\d+:_', r'', name)
    return name


def parse_inputs(inputs, name_split_sym='__'):
    d = tree()
    for name, value in inputs.items():
        path = transform_name(name).split(name_split_sym)
        create_by_path(d, value, *path)
    return to_dict_with_lists(d)
