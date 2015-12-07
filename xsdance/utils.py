# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division, absolute_import  # NOQA
from pprint import pprint  # NOQA

from collections import defaultdict
import re
import json

from lxml import etree

from xsdance.parse_inputs import parse_inputs  # NOQA


tree = lambda: defaultdict(tree)
tree_to_dict = lambda t: json.loads(json.dumps(t))

re_inline_parent_name = re.compile(r'([a-zA-Z0-9]+)_#\{\1:([0-9]+)\}')


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
    'minLength': (lambda r, v: len(unicode(v)) >= int(r),
                  'Length should be greater than {rvalue}'),

    'length': (lambda r, v: len(unicode(v)) == int(r),
               'Length should be equal to {rvalue}'),

    'maxLength': (lambda r, v: len(unicode(v)) <= int(r),
                  'Length should be less than {rvalue}'),

    'pattern': (lambda r, v: re.match(unicode(r), unicode(v)),
                'Value should match {rvalue}'),

    'enumeration': (lambda r, v: v in r + ['', None],
                    'Should be one of {rvalue}'),

    'maxInclusive': (lambda r, v: int(v) <= int(r),
                     'Should be less than or equal to {rvalue}'),

    'maxExclusive': (lambda r, v: int(v) < int(r),
                     'Should be less than {rvalue}'),

    'minInclusive': (lambda r, v: int(v) >= int(r),
                     'Should be greater than or equal to {rvalue}'),

    'minExclusive': (lambda r, v: int(v) > int(r),
                     'Should be greater than {rvalue}'),

    'totalDigits': (lambda r, v: len(re.sub('[,.L]', '', unicode(v))) < int(r),
                    'Total digits count should be less than {rvalue}'),

    'fractionDigits': (lambda r, v: len(unicode(v).split('.')[-1]) if '.' in unicode(v) else 0 <= int(r),
                       'Fraction digits count should be less than {rvalue}'),

    'whiteSpace': (lambda r, v: True, 'Error message'),
    'Assertions': (lambda r, v: True, 'Error message'),
    'explicitTimezone': (lambda r, v: True, 'Error message'),
}


class Validator:

    general_error_messages = {
        'incorrect_value': 'Incorrect value'
    }

    def __init__(self, rname, rvalue):
        self.test_func, self.error_message = funcs[rname]
        self.rvalue = rvalue

    def __call__(self, value):
        result = False
        try:
            result = self.test_func(self.rvalue, value)
        except:
            return self.general_error_messages['incorrect_value']

        if not result:
            return self.error_message.format(rvalue=unicode(self.rvalue), value=unicode(value))
