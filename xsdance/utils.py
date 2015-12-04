# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division, absolute_import  # NOQA
from pprint import pprint  # NOQA

from collections import defaultdict
import re
import json

from lxml import etree


tree = lambda: defaultdict(tree)
tree_to_dict = lambda t: json.loads(json.dumps(t))

re_inline_parent_name = re.compile(r'([a-zA-Z0-9]+)_#\{\1:([0-9]+)\}')


def add(d, keys, value, process_input=lambda v, _: v):

    for i, key in enumerate(keys):
        # check if current key looks like inline parent
        # if true, switch `process_input` function to support lists
        m = re_inline_parent_name.match(key)
        if m:
            key = m.group(1)
            index = m.group(2)

            process_input = lambda v, content: dict({index: v}, **(content or {}))
        # create empty dict for given key if not last element
        # or add value, if element is last
        last_element = (i == len(keys) - 1)
        if last_element:
            d[key] = process_input(value, d[key]) or None
        else:
            # assign existent tree or create new tree - d is `tree` instance
            d = d[key]


def _assign_value(tr, key, v):
    tr[key] = v


def add1(d, keys, value, assign_value=_assign_value):

    for i, key in enumerate(keys):
        # check if current key looks like inline parent
        # if true, switch `process_input` function to support lists
        m = re_inline_parent_name.match(key)
        if m:
            key = m.group(1)
            index = m.group(2)

            def func(tr, key, v):
                tr[index] = dict((tr[index] or {}), **{key: v})

            assign_value = func
        # create empty dict for given key if not last element
        # or add value, if element is last
        last_element = (i == len(keys) - 1)
        if last_element:
            assign_value(d, key, value)
        else:
            # assign existent tree or create new tree - d is `tree` instance
            d = d[key]


def parse_inputs(inputs, divider='__', add_func=add1):
    d = tree()
    for name, value in inputs.items():
        add1(d, name.split(divider), value)
    result = tree_to_dict(d)
    return result


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


class Renderer(object):

    class widget_type:
        text = 'text'
        checkbox = 'checkbox'
        select = 'select'

    html_input = {
        widget_type.text:
            '<input type="text" id="{name}" name="{name}" value="{value}" {disabled}/>',
        widget_type.checkbox:
            '<input type="checkbox" name="{{name}}" id="{{name}}" value="{value}" {{disabled}} {{checked}}/>',
        widget_type.select:
            '<select {multiple} name="{name}" {disabled}> {options} </select>',
    }

    html_input_wrapper = '''
        <div class="fieldset">
            <label for="" class=""> {label_text} </label>
            <p class="help"> {help_text} </p>
            {html_input}
            <div class="error" id="name"></div>
        </div>
    '''

    html_sequence_wrapper = '''
        <div class="admin-irs-grid grid-stack">
            {sequence}
        </div>
    '''

    html_element_wrapper = '''
        <div class="grid-stack-item">
            <div class="grid-stack-item-content">
                <input id="ch_hide_{name}" name="ch_hide_{name}" type="checkbox" {hide_checkbox_checked}/>
                {content}
            </div>
        </div>
    '''

    html_option = '<option value="{value}" {checked}>{text}</option>'

    def render_html(self, edit_mode=False, hidden_fields=None):
        return self.html_element_wrapper.format(
            content=self.render_sequence() or self.render_input(),
            name=self.get_prefixed_name(),
            hide_checkbox_checked=self.get_hide_checkbox_checked(),
        )

    def render_sequence(self):
        return self.html_sequence_wrapper.format(
            sequence=''.join([el.render_html() or '' for el in self.subelements])
        )

    def render_input(self):
        return self.html_input_wrapper.format(
            label_text=self.get_label_text(),
            help_text=self.get_help_text(),
            html_input=self.render_html_input(),
        )

    def render_html_input(self):
        return self.html_input[self.get_widget_type()].format(
            name=self.get_prefixed_name(),
            value=self.get_value(),
            disabled=self.get_disabled(),
            **self.get_widget_format_arguments()
        )

    def get_hide_checkbox_checked(self):
        return False

    def get_widget_type(self):
        return 'text'

    def get_widget_format_arguments(self):
        return {}

    def get_label_text(self):
        return ''

    def get_help_text(self):
        return ''
