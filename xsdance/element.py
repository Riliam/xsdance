# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division, absolute_import  # NOQA

from .utils import serialize_xml, serialize_json


class ValueRequiredError(BaseException):
    pass


class Element(object):

    ValueRequiredError = ValueRequiredError

    nesting_connector = '__'
    error_messages = {
        'required': 'This field is required',
    }

    gridster_default_settings = {
        'data-gs-y': "0",
        'data-gs-x': "0",
        'data-gs-width': "4",
        'data-gs-height': "2",
    }

    def __init__(self, name, initial_data=None,
                 label_text='',
                 help_text='',
                 min_occurs=1,
                 max_occurs=1,
                 parent=None,
                 validators=None,
                 processors=None,

                 html_label=None, html_input=None, html_wrapper=None,
                 html_parent_element_wrapper=None, html_input_wrapper=None,
                 html_help=None, html_edit_checkbox=None,

                 **kwargs):
        self.name = name
        self.initial_data = initial_data or {}
        self.label_text = label_text
        self.help_text = help_text
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.parent = parent
        self.validators = validators or []
        self.processors = processors or []

        # redefining default html templates
        self.html_input = html_input

        self.html_label = html_label
        self.html_help = html_help

        self.html_wrapper = html_wrapper
        self.html_input_wrapper = html_input_wrapper
        self.html_parent_element_wrapper = html_parent_element_wrapper
        self.html_help = html_help
        self.html_edit_checkbox = html_edit_checkbox
        # end

        self.kwargs = kwargs

        self.cleaned_value = None
        self._cleaned_data = {}
        self.errors = {}

        self.subelements = []

        if parent:
            parent.add_subelement(self)
            if parent.initial_value:
                initial_data = parent.initial_value.get(self.name, None)
                self.initial_data[self.name] = initial_data

    def __getitem__(self, index):
        return self.subelements[index]

    def __repr__(self):
        return self.name

    @property
    def cleaned_data(self):
        return self._get_cleaned_data()

    @property
    def initial_value(self):
        return self.initial_data[self.name]

    def prefixed_name(self, inlines=None):
        name = self.name
        if self.parent:
            name = '{prefix}{connector}{name}'.format(
                prefix=self._get_full_prefix(inlines=inlines),
                connector=self.nesting_connector,
                name=name)
        return name

    def get_edit_checkbox_input(self, edit_mode, hidden_fields):
        edit_checkbox = ''
        if edit_mode:
            edit_checkbox = self.html_edit_checkbox.format(
                name=self.prefixed_name(),
                checked='',
            )
            if self.prefixed_name in hidden_fields:
                edit_checkbox = self.html_edit_checkbox.format(
                    name=self.prefixed_name(),
                    checked='checked',
                )
        return edit_checkbox

    def render_html(self, inlines=None, edit_mode=False, hidden_fields=None):

        hidden_fields = hidden_fields or []
        if not edit_mode and self.prefixed_name() in hidden_fields:
            return None

        prefixed_name = self.prefixed_name()

        inlines = None
        if self.max_occurs > 1:
            inlines = ((inlines or []) + [(self.name, self.min_occurs)])

        html_subelements = self._render_subelements_html(
            inlines=inlines,
            edit_mode=edit_mode,
            hidden_fields=hidden_fields,)
        content = ''
        if html_subelements is not None:
            content = html_subelements \
                or self._html_input_with_value(inlines=inlines,
                                               edit_mode=edit_mode,
                                               hidden_fields=hidden_fields)
            html_help = self.html_help.format(
                name=prefixed_name,
                help_text=self.help_text or '')
            content = content + html_help

        return self.html_wrapper.format(
            gridster_settings=self.get_gridster_settings_attrs(),
            edit_checkbox=self.get_edit_checkbox_input(edit_mode, hidden_fields),
            name=prefixed_name,
            content=content)

    def _render_subelements_html(self, inlines=None, edit_mode=False, hidden_fields=None):
        name = self.name

        if inlines is not None:
            name = '{}_#0'.format(name)

        elements = [el.render_html(inlines=inlines,
                                   edit_mode=edit_mode,
                                   hidden_fields=hidden_fields)
                    for el in self.subelements]
        content = ''.join([el for el in elements if el])

        if content:
            content = self.html_parent_element_wrapper.format(
                parent_label=self.label_text or name,
                parent_name=name,
                content=content)
        return content

    def _html_input_with_value(
            self,
            inlines=None,
            edit_mode=False,
            hidden_fields=None):

        name = self.prefixed_name(inlines=inlines)

        result = ''
        if self.html_input:
            html_label = self.html_label.format(
                name=name,
                label_text=self.label_text or name,
                required=self.required(),
            )
            value = self.initial_data.get(self.name) or ''
            checked = ' checked' if self.is_checkbox and value else ''
            html_input = self.html_input.format(
                edit_checkbox=self.get_edit_checkbox_input(edit_mode, hidden_fields),
                disabled=edit_mode and ' disabled' or '',
                name=name,
                value=value,
                checked=checked,
            )
            result = self.html_input_wrapper.format(
                label=html_label,
                html_input=html_input,
                help_text=self.get_help_text_html(),
            )
        return result

    def get_gridster_settings_attrs(self):
        return ' '.join('='.join([k, '"{}"'.format(v)]) for k, v in self.gridster_default_settings.items())

    def get_help_text_html(self):
        result = ''
        if self.help_text:
            result = '<p class="help"> {help_text} </p>'.format(help_text=self.help_text)
        return result

    @property
    def is_checkbox(self):
        return 'type="checkbox"' in self.html_input

    def render_xml(self):
        if not self.initial_data:
            raise Element.ValueRequiredError
        return serialize_xml(self.cleaned_data())

    def render_json(self):
        if not self.initial_data:
            raise Element.ValueRequiredError
        return serialize_json(self.cleaned_data())

    def validate(self, d):
        errors = {}
        value = d.get(self.name, {})
        for sub in self.subelements:
            v = sub.process_value(value.get(sub.name, None))
            if v is None and sub.min_occurs > 0:
                errors[sub.prefixed_name()] = [self.error_messages['required']]
            else:
                suberrors = sub.validate(value)
                if suberrors:
                    errors.update(suberrors)

        processed = self.process_value(value)
        self.cleaned_value = processed

        for validator in self.validators:
            result = validator(processed)
            if result:
                errors[self.prefixed_name()] =\
                    errors.get(self.prefixed_name(), []) + [result]

        self.errors = errors
        return self.errors

    def process_value(self, value):
        processed = value
        for processor in self.processors:
            processed = processor(processed)
        return processed

    def add_subelement(self, el):
        self.subelements.append(el)
        el.set_parent(self)

    def add_validator(self, validator):
        self.validators.append(validator)

    def add_processor(self, processor):
        self.processors.append(processor)

    def set_parent(self, el):
        self.parent = el

    def add_kwargs(self, **kwargs):
        self.kwargs.update(**kwargs)

    def _get_full_prefix(self, inlines=None):
        inlines_suffix = '_#{{{name}:0}}'
        inlines = inlines or []
        parents = []
        el = self
        while getattr(el, 'parent'):
            name = el.parent.name
            if name in inlines:
                name = name + inlines_suffix.format(name)
            parents.append(name)
            el = el.parent
        return self.nesting_connector.join(reversed(parents))

    def _get_cleaned_data(self, top=True):
        if self._cleaned_data:
            return self._cleaned_data

        cleaned_sub = {sub.name: sub._get_cleaned_data(top=False)
                       for sub in self.subelements}
        data = cleaned_sub or self.cleaned_value
        if top:
            data = {self.name: data}
        self._cleaned_data = data

        return data

    def required(self):
        return 'required' if 'choice' not in self.parent.name else ''

    def set_initial_data(self, data):
        self.initial_data = data
        if data:
            for el in self.subelements:
                el.set_initial_data(data.get(self.name))
        return self

    def _print_tree(self, level=0):
        print(level * '--', self.name)
        for el in self.subelements:
            el.print_tree(level+1)
