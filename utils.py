from collections import defaultdict
import re
import json

from lxml import etree


tree = lambda: defaultdict(tree)

re_inline_parent_name = re.compile(r'([a-zA-Z0-9]+)#\{\1:([0-9]+)\}')


def make_exception(name):
    return type(name, (BaseException,), {})


def add(d, keys, value, process_input=lambda value, _: value):
    for i, key in enumerate(keys):
        # check if current key looks like inline parent
        # if true, switch `process_input` function to support lists
        m = re_inline_parent_name.match(key)
        if m:
            key = m.group(1)
            index = m.group(2)
            process_input =\
                lambda value, content: dict({index: value}, **content)
        # create empty dict for given keyif not last element
        # or add value, if element is last
        last_element = (i == len(keys) - 1)
        if last_element:
            d[key] = process_input(value, d[key])
        else:
            d = d[key]


def parse_inputs(inputs, divider='__'):
    d = tree()
    for name, value in inputs.items():
        add(d, name.split(divider), value)
    return json.loads(json.dumps(d))


def _serialize_xml(d, root=None):
    root = root if isinstance(root, etree._Element) else etree.Element(root)
    for name, value in d.items():
        elem = etree.Element(name)
        if isinstance(value, dict):
            serialize_xml(value, elem)
        else:
            elem.text = value
        root.append(elem)
    return root


def serialize_xml(d, root='xml'):
    return etree.tostring(_serialize_xml(d, root))


def serialize_json(d):
    return json.dumps(d)
