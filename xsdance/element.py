# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division, absolute_import  # NOQA
from cgi import escape

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
        'data-gs-x': 0,
        'data-gs-y': 0,
        'data-gs-width': 12,
        'data-gs-height': 3,
    }
    inlines_suffix_t = '_#{{{name}:{index}}}'
    inlines_emtpy_suffix_t = '_#{{{name}}}'

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
                 html_inline_button_add=None, html_inline_button_remove=None,
                 html_inline_buttons_wrapper=None,
                 html_inline_item_wrapper=None,

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
        self.html_inline_button_add = html_inline_button_add
        self.html_inline_button_remove = html_inline_button_remove
        self.html_inline_buttons_wrapper = html_inline_buttons_wrapper
        self.html_inline_item_wrapper = html_inline_item_wrapper
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

    def render_html(self, edit_mode=False, hidden_fields=None, gridster_settings=None):
        kwargs = {
            'edit_mode': edit_mode,
            'hidden_fields': hidden_fields,
            'gridster_settings': gridster_settings
        }

        if not edit_mode and self.prefixed_name() in hidden_fields:
            return None

        if self.subelements:
            content = self._render_subelements_html(**kwargs)
        else:
            content = self._render_html_input_with_value(**kwargs)

        if self.inlines_needed() is not None:
            inline_content = self._render_inline_content(content)
            empty_item = self._render_empty_item(content, gridster_settings=gridster_settings)
            content = self._wrap_with_inline_block_wrapper(inline_content, empty_item)

        content = self._wrap_with_item_wrapper(content)
        return content

    def _render_subelements_html(self, edit_mode=False, hidden_fields=None, gridster_settings=None):
        name = self.name

        elements = [el.render_html(edit_mode=edit_mode,
                                   hidden_fields=hidden_fields,
                                   gridster_settings=gridster_settings)
                    for el in self.subelements]
        content = ''.join([el for el in elements if el])

        if content:
            content = self.html_parent_element_wrapper.format(
                parent_label=self.label_text or name,
                parent_name=name,
                content=content)
        return content

    def _render_html_input_with_value(self, edit_mode=False, hidden_fields=None, gridster_settings=None):

        name = self.prefixed_name()

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
                name=name,
            )
        return result

    def _wrap_with_html_inline_item_wrapper(self, content, noremove=False, gridster_settings=None):
        result = self.html_inline_item_wrapper.format(
            content=content,
            remove_button='' if noremove else self.get_remove_button(),
            gridster_settings=self.get_gridster_settings_attrs(gridster_settings))
        return result

    def _render_inline_content(self, content, gridster_settings=None):
        inlines_count = self.inlines_needed()
        inlines = ''
        for i in range(1, inlines_count):
            item = content.replace(self._get_name_with_inline_suffix(),
                                   self._get_name_with_inline_suffix(index=i))
            item = self._wrap_with_html_inline_item_wrapper(item, gridster_settings=gridster_settings)
            inlines += item
        content = self._wrap_with_html_inline_item_wrapper(content, noremove=False, gridster_settings=gridster_settings)
        content = content + inlines
        return content

    def _render_empty_item(self, content, gridster_settings=None):
        empty = content.replace(self._get_name_with_inline_suffix(),
                                self._get_name_with_inline_suffix(empty=True))
        empty = self._wrap_with_html_inline_item_wrapper(empty, gridster_settings=gridster_settings)
        return empty

    def _wrap_with_inline_block_wrapper(self, content, empty):
        wrapped = '''
            <div class="grid-stack fieldset-content">
                {content}
                {add_button}
            </div>
        '''.format(content=content, add_button=self.get_add_button(empty))
        return wrapped

    def _wrap_with_item_wrapper(self, content, edit_mode=False,
                                hidden_fields=None, gridster_settings=None):
        prefixed_name = self.prefixed_name()
        gridster_settings_attrs =\
            self.get_gridster_settings_attrs(gridster_settings)
        edit_checkbox = self.get_edit_checkbox_input(edit_mode, hidden_fields)

        result = self.html_wrapper.format(
            gridster_settings=gridster_settings_attrs,
            edit_checkbox=edit_checkbox,
            prefixed_name=prefixed_name,
            name=self.name,
            content=content,
            inline_buttons='')
        return result

    def prefixed_name(self):
        name = self.name
        if self.inlines_needed() is not None:
            name = self._get_name_with_inline_suffix()
        if self.parent:
            name = '{prefix}{connector}{name}'.format(
                prefix=self._get_full_prefix(),
                connector=self.nesting_connector,
                name=name)
        return name

    def _get_full_prefix(self):
        parents = []
        el = self
        # el.parent should evaluate to True, if exists
        while getattr(el, 'parent', None):
            name = el.parent.name
            if el.parent.inlines_needed() is not None:
                name = el.parent._get_name_with_inline_suffix()
            parents.append(name)
            el = el.parent
        return self.nesting_connector.join(reversed(parents))

    def _get_name_with_inline_suffix(self, empty=False, index=0):
        templ = self.inlines_emtpy_suffix_t if empty else self.inlines_suffix_t
        return self.name + templ.format(name=self.name, index=index)

    def inlines_needed(self):
        return (self.min_occurs or 1) if self.max_occurs > 1 else None

    def get_remove_button(self):
        btn = ''
        if self.inlines_needed() is not None:
            btn = self.html_inline_button_remove.format(
                name=self.name,
                min_count=self.min_occurs)
        return self.html_inline_buttons_wrapper.format(content=btn)

    def get_add_button(self, empty):
        btn = ''
        if self.inlines_needed() is not None:
            btn = self.html_inline_button_add.format(
                name=self.name,
                max_count=self.max_occurs,
                empty=escape(empty, quote=True))
        return self.html_inline_buttons_wrapper.format(content=btn)

    def get_edit_checkbox_input(self, edit_mode, hidden_fields):
        edit_checkbox = ''
        if edit_mode:
            edit_checkbox = self.html_edit_checkbox.format(
                name=self.prefixed_name(),
                checked='',
            )
            if self.prefixed_name() in hidden_fields:
                edit_checkbox = self.html_edit_checkbox.format(
                    name=self.prefixed_name(),
                    checked='checked',
                )
        return edit_checkbox

    def get_gridster_settings_attrs(self, gridster_settings):
        gridster_settings = gridster_settings or []
        settings = [s for s in gridster_settings if s.get('prefixed_name', None) == self.prefixed_name()]
        settings = settings[0] if settings else self.gridster_default_settings
        return ' '.join('='.join([k, '"{}"'.format(v)]) for k, v in settings.items()
                        if k.startswith('data-gs-'))

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
