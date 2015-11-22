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


funcs = {
    'minLength': (lambda r, v: len(v) >= int(r),
                  'Length should be greater than {rvalue}'),

    'length': (lambda r, v: len(v) == int(r),
               'Length should be equal to {rvalue}'),

    'maxLength': (lambda r, v: len(v) <= int(r),
                  'Length should be lesst than {rvalue}'),

    'pattern': (lambda r, v: re.match(r, str(v)),
                'Value should match {rvalue}'),

    'enumeration': (lambda r, v: v in r,
                    'Should be one of {rvalue}'),

    'maxInclusive': (lambda r, v: v <= int(r),
                     'Should be less than or equal to {rvalue}'),

    'maxExclusive': (lambda r, v: v < int(r),
                     'Should be less than {rvalue}'),

    'minInclusive': (lambda r, v: v >= int(r),
                     'Should be greater than or equal to {rvalue}'),

    'minExclusive': (lambda r, v: v > int(r),
                     'Should be greater than {rvalue}'),

    'totalDigits': (lambda r, v: len(re.sub('[,.L]', '', str(v))) < int(r),
                    'Total digits count should be less than {rvalue}'),

    'fractionDigits': (lambda r, v: len(str(v).split('.')[-1]) < int(r),
                       'Fraction digits count should be less than {rvalue}'),

    'whiteSpace': (lambda r, v: True, 'Error message'),
    'Assertions': (lambda r, v: True, 'Error message'),
    'explicitTimezone': (lambda r, v: True, 'Error message'),
}


class Validator:

    def __init__(self, rname, rvalue):
        self.test_func, self.error_message = funcs[rname]
        self.rvalue = rvalue

    def __call__(self, value):
        result = False
        result = self.test_func(self.rvalue, value)
        if not result:
            return self.error_message.format(rvalue=self.rvalue, value=value)
