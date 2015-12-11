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

    'pattern': (lambda r, v: bool(re.match(unicode(r), unicode(v))),
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


regex_messages = {
    '[\-+]?[0-9]+':
        'Value should be integer',

    '([A-Za-z\-] ?)*[A-Za-z\-]':
        'Value should contain letters only',

    '[0-9]{9}':
        'Value should contain 9 digits of SSN or EIN',

    '[A-Z][A-Z\- ]{0,3}':
        'Value should contain up to 3 big letters',

    '[1-9][0-9]{3}\-.*':
        'Value should be date',

    '[1-9][0-9]{3}\-.*':
        'Value should be date',

    '[A-Za-z0-9\-]+':
        'Value should be Bank Account Number - 17 alphanumeric characters with hyphens',

    '(([A-Za-z0-9#\-\(\)]|&#x26;|&#x27;) ?)*([A-Za-z0-9#\-\(\)]|&#x26;|&#x27;)':
        'Value should be valid business name',

    '(([A-Za-z0-9#/%\-\(\)]|&#x26;|&#x27;) ?)*([A-Za-z0-9#/%\-\(\)]|&#x26;|&#x27;)':
        'Value should be valid business name',

    '(% )(([A-Za-z0-9#/%\-\(\)]|&#x26;|&#x27;) ?)*([A-Za-z0-9#/%\-\(\)]|&#x26;|&#x27;)':
        'Value should be valid name of business or individual',

    '[A-Za-z]( |&lt;)?(([A-Za-z#\-]|&#x26;)( |&#x3c;)?)*([A-Za-z#\-]|&#x26;)':
        'Valud should be valid name',

    '([A-Za-z0-9\'\-] ?)*[A-Za-z0-9\'\-]':
        'Value should be valid person name',

    '([&#x0021;-&#x007E;] ?)*[&#x0021;-&#x007E;]':
        'Value should be valid person title',

    '[A-Za-z0-9]( ?[A-Za-z0-9\-/])*':
        'Value should be valid street name',

    '([A-Za-z] ?)*[A-Za-z]':
        'Value should be valid city name',

    '[0-9]{5}(([0-9]{4})|([0-9]{7}))?':
        'Value should be zip code',

    '[0-9]{10}':
        'Value should be telephone number',

    '[0-9]{1,30}':
        'Value should be telephone number',

    '([&#x0021;-&#x007E;&#x00A3;&#x00A7;&#xC1;&#xC9;&#xCD;&#xD1;&#xD3;&#xD7;&#xDA;&#xDC;&#xE1;&#xE9;&#xED;&#xF1;&#xF3;&#xFA;&#xFC;] ?)*[&#x0021;-&#x007E;&#x00A3;&#x00A7;&#xC1;&#xC9;&#xCD;&#xD1;&#xD3;&#xD7;&#xDA;&#xDC;&#xE1;&#xE9;&#xED;&#xF1;&#xF3;&#xFA;&#xFC;]':  # NOQA
        'Value should be valid printable characters',

    '[0-9]*':
        'Value should be valid numeric type',

    '[A-Za-z0-9]*':
        'Value should consist of letters and digits',

    '[A-Za-z0-9\(\)]*':
        'Value should contain letters, digits and parentheses',

    '[A-HJ-NPR-Z0-9]{1,17}':
        'Value should contain vehicle identification number',

    '[A-HJ-NPR-Z0-9]{19}':
        'Value should contain vehicle identification number',

    '([A-Za-z\-] ?)*[A-Za-z\-]':
        'Value should contain A-Z, a-z, hyphen and single space',

    '[0-9]{2}:[0-9]{2}:[0-9]{2}':
        'Value should be valid ISO-8601 time',
}


class Validator:

    general_error_messages = {
        'incorrect_value': 'Incorrect value'
    }

    def __init__(self, rname, rvalue):
        self.rvalue = rvalue
        self.test_func, self.error_message = funcs[rname]

        if rname == 'pattern':
            self.error_message = regex_messages.get(rvalue, 'Invalid value')

    def __call__(self, value):
        result = False
        try:
            result = self.test_func(self.rvalue, value)
        except:
            return self.general_error_messages['incorrect_value']

        if not result:
            return self.error_message.format(rvalue=unicode(self.rvalue), value=unicode(value))
