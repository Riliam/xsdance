# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division, absolute_import  # NOQA
from pprint import pprint  # NOQA
import json
import copy
from cgi import escape
import re
from collections import defaultdict, OrderedDict
from itertools import groupby

from .utils import serialize_xml, serialize_json


class ValueRequiredError(BaseException):
    pass


class Element(object):

    ValueRequiredError = ValueRequiredError

    nesting_connector = '__'
    error_messages = {
        'required': 'This field is required',
        'too_many_choices': 'Too many choices selected',
        'max_occurs_violated': 'Up to {} values allowed',
        'min_occurs_violated': 'No less than {} value allowed',
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

    @staticmethod
    def get_distinct_inlines_count(name, data, count=True,):
        if not data:
            return []

        rx = re.compile('#{' + name + ':(\d+)}')

        def grouping_key(x):
            m = rx.search(x)
            return (m.group(1) if m else None)

        groups = list(groupby(sorted(data), key=grouping_key))
        indeces = [g[0] for g in groups if g[0]]
        if count:
            result = len(indeces)
        else:
            result = indeces

        return result

    def get_flat_fields(self, hidden_fields=None, acc_list=None):
        hidden_fields = hidden_fields or []
        acc_list = acc_list or ['{0}__'.format(self.name)]
        names = []
        for sub in self.subelements:
            if sub.prefixed_name() not in hidden_fields:

                name = sub._get_name_with_inline_suffix() if sub.inlines_needed() is not None else sub.name
                if not sub.subelements:
                    names += ['{0}{1}'.format(p, name) for p in acc_list]
                else:
                    new_acc = ['{0}{1}{2}'.format(p, name, '_' if 'choice' in sub.name else '__') for p in acc_list]
                    if new_acc:
                        names += sub.get_flat_fields(
                            hidden_fields=hidden_fields,
                            acc_list=new_acc)
        return names

    def get_all_checkboxes(self, data, acc_list=None, hidden_fields=None):
        hidden_fields = hidden_fields or []
        acc_list = acc_list or ['{0}__'.format(self.name)]

        names = []
        for sub in self.subelements:
            # following cases are all mutually exclusive, the second and the third
            # are here to eliminate nested if's
            if sub.prefixed_name() not in hidden_fields:

                if sub.is_checkbox:
                    names += ['{0}{1}'.format(p, sub.name) for p in acc_list]

                new_acc = []
                if sub.subelements and sub.inlines_needed() is not None:
                    new_acc = ['{0}{1}__'.format(p, sub._get_name_with_inline_suffix(index=i))
                               for p in acc_list
                               for i in self.get_distinct_inlines_count(sub.name, data.keys(), count=False)]

                if sub.subelements and sub.inlines_needed() is None:
                    new_acc = ['{0}{1}{2}'.format(p, sub.name, '_' if 'choice' in sub.name else '__')
                               for p in acc_list]

                if new_acc:
                    names += sub.get_all_checkboxes(
                        data,
                        new_acc,
                        hidden_fields=hidden_fields)
        return names

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
            inlines_count = self.get_distinct_inlines_count(
                self.name,
                self.initial_data,
                count=True)
            inline_content = self._render_inline_content(
                content,
                inlines_count=inlines_count,
                gridster_settings=gridster_settings)
            empty_item = self._render_empty_item(
                content,
                gridster_settings=gridster_settings)
            content = self._wrap_with_inline_block_wrapper(
                inline_content,
                empty_item,
                inlines_count)

        content = self._wrap_with_item_wrapper(content,
                                               edit_mode=edit_mode,
                                               hidden_fields=hidden_fields,
                                               gridster_settings=gridster_settings)
        if not self.parent:
            for k, v in self.initial_data.items():
                if isinstance(v, list):
                    v = escape(json.dumps(v), quote=True)
                content = re.sub('\[\[{0}\|checkbox\]\]'.format(k), ('checked' if v else ''), content)
                content = re.sub('\[\[{0}\]\]'.format(k), v, content)
            content = re.sub(r'\[\[.*?\]\]', r'', content)
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
                required=self.get_class_required(),
            )
            checkbox_ind = '|checkbox' if self.is_checkbox else ''
            value = '[[{name}{ind}]]'.format(name=name, ind=checkbox_ind) if self.initial_data else ''
            html_input = self.html_input.format(
                edit_checkbox=self.get_edit_checkbox_input(edit_mode, hidden_fields),
                disabled=edit_mode and 'disabled' or '',
                name=name,
                value=value,
                checked=value,
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
            gridster_settings=self.get_gridster_settings_attrs(gridster_settings, inline_wrapper=True),
            prefixed_name=self.prefixed_name())
        return result

    def _render_inline_content(self, content, inlines_count=None, gridster_settings=None):
        min_inlines = 0 if inlines_count else 1
        inlines_count = inlines_count or self.inlines_needed()
        inlines = ''
        for i in range(min_inlines, inlines_count):
            item = content.replace(self._get_name_with_inline_suffix(),
                                   self._get_name_with_inline_suffix(index=i))
            item = self._wrap_with_html_inline_item_wrapper(item, gridster_settings=gridster_settings)
            inlines += item
        if min_inlines:
            content = self._wrap_with_html_inline_item_wrapper(
                content,
                noremove=False,
                gridster_settings=gridster_settings)
            content = content + inlines
        else:
            content = inlines
        return content

    def _render_empty_item(self, content, gridster_settings=None):
        empty = content.replace(self._get_name_with_inline_suffix(),
                                self._get_name_with_inline_suffix(empty=True))
        empty = self._wrap_with_html_inline_item_wrapper(empty, gridster_settings=gridster_settings)
        return empty

    def _wrap_with_inline_block_wrapper(self, content, empty, inlines_count=None):
        wrapped = '''
            <div class="grid-stack fieldset-content">
                {content}
                {add_button}
            </div>
        '''.format(content=content, add_button=self.get_add_button(empty, inlines_count))
        return wrapped

    def _wrap_with_item_wrapper(self, content, edit_mode=False,
                                hidden_fields=None, gridster_settings=None):
        prefixed_name = self.prefixed_name(process_inlines=False)
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

    def prefixed_name(self, prefix=None, index=0, process_inlines=True):
        name = self.name
        if process_inlines and self.inlines_needed() is not None:
            name = self._get_name_with_inline_suffix(index=index)
        if self.parent:
            prefix = prefix or self._get_full_prefix()
            connector = self.nesting_connector
            name = '{prefix}{connector}{name}'.format(
                prefix=prefix,
                connector=connector,
                name=name)

        # so :choice_2: will be separated from its variants by '_' not '__'
        name = re.sub(r'(:choice_[0-9]+:)_', r'\1', name)

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

    def get_add_button(self, empty, max_count=None):
        btn = ''
        if self.inlines_needed() is not None:
            btn = self.html_inline_button_add.format(
                name=self.name,
                current_elements_count=max_count or self.inlines_needed(),
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

    def get_gridster_default_settings(self):
        y = 0
        if self.parent:
            y = self.parent.subelements.index(self)
        settings = copy.deepcopy(self.gridster_default_settings)
        default_h = self.gridster_default_settings['data-gs-height']
        settings['data-gs-y'] = y * default_h
        return settings

    def get_gridster_settings_attrs(self, gridster_settings, inline_wrapper=False):
        assert isinstance(gridster_settings, list), 'gridster_settings should be instance of list'
        gridster_settings = gridster_settings or []
        process_inlines = inline_wrapper
        prefixed_name = self.prefixed_name(process_inlines=process_inlines)
        settings = [s for s in gridster_settings
                    if s.get('prefixed_name', None) == prefixed_name]
        settings = settings[0] if settings else self.get_gridster_default_settings()
        settings_attrs = ' '.join('='.join([k, '"{}"'.format(v)])
                                  for k, v in settings.items()
                                  if k.startswith('data-gs-'))
        return settings_attrs

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

    def validate_inputs(self, source, hidden_fields=None):
        hidden_fields = hidden_fields or []
        hidden_fields_masks = [re.sub(r':\d+', r':\d+', f) for f in hidden_fields]
        cleaned = {}
        errors = defaultdict(list)

        checkbox_names = self.get_all_checkboxes(source, hidden_fields=hidden_fields)
        for chb in checkbox_names:
            source[chb] = source.get(chb, '')

        source = self.normalize_indeces(source)

        cleaned, errors = self._validate_with_validators(source, cleaned, errors)

        errors = self._validate_required_fields(cleaned, errors, hidden_fields_masks, checkbox_names)
        errors = self._validate_choices(cleaned, errors, hidden_fields)
        errors = self._validate_inlines(cleaned, errors, hidden_fields)

        errors = {k: v for k, v in errors.items() if v}
        return cleaned, errors

    @staticmethod
    def normalize_indeces(input_data):
        ''' Returns normalized inputs, where indeces, if not consecutive, are
        mapped to 0 to n. Fields without indeces remain untouched.

        Example input:
            {
                'a__b': 'value 1',
                'a__babab': 'value 10',
                'a__c_#{c:3}': 'value 2',
                'a__d_#{d:4}__e': 'value 3',
                'a__d_#{d:4}__f': 'value 4',
                'a__d_#{d:8}__e': 'value 5',
                'a__d_#{d:8}__f': 'value 6',
                'a__g_#{g:5}__h__j_#{j:11}': 'value 7',
                'a__g_#{g:5}__h__j_#{j:15}': 'value 8',
                'a__g_#{g:7}__h__j_#{j:12}': 'value 9'
            }

        Example result:
            {
                'a__b': 'value 1',
                'a__c_#{c:0}': 'value 2',
                'a__d_#{d:0}__e': 'value 3',
                'a__d_#{d:0}__f': 'value 4',
                'a__d_#{d:1}__e': 'value 5',
                'a__d_#{d:1}__f': 'value 6',
                'a__g_#{g:0}__h__j_#{j:0}': 'value 7',
                'a__g_#{g:0}__h__j_#{j:1}': 'value 8',
                'a__g_#{g:1}__h__j_#{j:0}': 'value 9'
            }
        '''
        sorted_input_data_items = sorted(input_data.items(), key=lambda x: x[0])
        # `translate` is dict, with
        #   key - tuple of `name`:`index` strings.
        #         Last element of tuple is string, which will be replaced.
        #         Elements from first to last but one needed to
        #         ensure correct processing of nested indexed names
        #   value - `name`:`index` string for which last element of key tuple
        #         will be replaced
        translate = {}

        # `counts` is dict with value defaults to 0.
        #   key - tuple, where
        #     [:-1] elements are `name`:`index` string
        #     [-1] element is `name` string
        #   value - count of groups of `name` with different indeces
        counts = defaultdict(lambda: 0)

        # resulting data
        new_data = {}

        # in first part, `translate` and `counts` dictionaries are generated from inputs' keys
        for k, _ in sorted_input_data_items:

            # find all entries in key, which are look like `name`:`index`
            # two re groups are fetched: (`name`:`index`, `name`)
            ms = re.findall(r'#{((.*?):\d+)}', k)

            if ms:
                new_translation_key, _ = tuple(zip(*ms))
                there_are_indexed_names_in_the_key = bool(ms)
                translation_not_yet_added = new_translation_key not in translate
                if there_are_indexed_names_in_the_key and translation_not_yet_added:
                    # create new `counts_key`
                    last_name = ms[-1][1]
                    all_but_last_name_with_indexes = [a[0] for a in ms[:-1]]
                    counts_key = tuple(all_but_last_name_with_indexes + [last_name])

                    # update `translate` and `counts`
                    translate[new_translation_key] = '{}:{}'.format(last_name, counts[counts_key])
                    counts[counts_key] += 1

        # in second part, `new_data` is generated, using defined `translate` and `counts`
        for k, v in sorted_input_data_items:
            new_k = k
            for from_, to_ in translate.items():
                # if all names are in new_k, ...
                for name_with_index in from_:
                    if name_with_index not in new_k:
                        break
                # ... replace last entry with `to_`
                # NOTE! name_with_index remains after the loop with value of last index
                # NOTE! else statement of for loop executes if loop exits normally(i.e. no break)
                else:
                    new_k = new_k.replace(name_with_index, to_)
            new_data[new_k] = v

        return new_data

    def _validate_with_validators(self, source, cleaned, errors):
        for k, v in source.items():
            el = self.get_element_by_path(k)
            processed = el.process_value(v)
            cleaned[k] = processed
            if processed:
                errors[k] = el.validate_atom(processed)
        return cleaned, errors

    def process_value(self, value):
        processed = value
        for processor in self.processors:
            processed = processor(processed)
        return processed

    def validate_atom(self, processed):
        if isinstance(processed, list):
            errors = []
            for p in processed:
                errors += map(lambda v: v(p), self.validators)
        else:
            errors = map(lambda v: v(processed), self.validators)
        errors = filter(bool, errors)
        return errors

    def _validate_required_fields(self, cleaned, errors, hidden_fields_masks, checkbox_names):
        required_masks = self.get_required_masks(hidden_fields_masks)
        for k, v in cleaned.items():
            required = False
            for mask in required_masks:
                if re.match(mask, k):
                    required = True
                    break
            if required and (k not in checkbox_names) and (not cleaned.get(k, None)):
                errors[k] = [self.error_messages['required']] + errors[k]
        return errors

    def _validate_choices(self, cleaned, errors, hidden_fields):
        choice_elements = self._get_choice_elements(hidden_fields)
        for ch in choice_elements:
            inputs = [k for k in cleaned.keys() if ch.name in k]

            for group in groupby(sorted(inputs), key=lambda x: x.split(ch.name)[0]):
                prefix, group_input_keys = group
                if len([k for k in group_input_keys if cleaned.get(k)]) > ch.max_occurs:
                    k = prefix + ch.name
                    elements_s = ', '.join(['\'{0}\''.format(e.label_text) for e in ch.subelements])
                    if ch.min_occurs == ch.max_occurs:
                        message = 'Exactly {min}'
                    elif ch.max_occurs == ch.UNBOUNDED:
                        message = '{min} or more'
                    elif ch.min_occurs == 0:
                        message = 'Up to {max}'
                    else:
                        message = ('{min} to {max}')
                    message = (message + ' of the these boxes should be filled: {boxes}').format(
                        min=ch.min_occurs,
                        max=ch.max_occurs,
                        boxes=elements_s)
                    errors[k] = errors[k] + [message]
        return errors

    def _validate_inlines(self, cleaned, errors, hidden_fields):
        inline_elements = self._get_inline_elements(hidden_fields)
        for inline in inline_elements:
            inputs = [x for x in cleaned.keys() if '{0}_#{{'.format(inline.name) in x]

            rx = re.compile(r'#{' + inline.name + ':(\d+)}')
            groups = groupby(sorted(inputs), key=lambda x: rx.search(x).group(1))
            inlines_count = len(list(groups))
            if inlines_count > inline.max_occurs:
                k = inline.prefixed_name()
                errors[k] = errors[k] + [self.error_messages['max_occurs_violated'].format(inline.max_occurs)]
            if inlines_count < inline.min_occurs:
                k = inline.prefixed_name()
                errors[k] = errors[k] + [self.error_messages['min_occurs_violated'].format(inline.min_occurs)]
        return errors

    def _get_choice_elements(self, hidden_fields):
        choice_elements = []
        elements = [self]
        while elements:
            el = elements.pop()
            if 'choice' in el.name and el.prefixed_name() not in hidden_fields:
                choice_elements.append(el)
            elements.extend(el.subelements or [])
        return choice_elements

    def _get_inline_elements(self, hidden_fields):
        inline_elements = []
        elements = [self]
        while elements:
            el = elements.pop()
            if el.inlines_needed() and el.prefixed_name() not in hidden_fields:
                inline_elements.append(el)
            elements.extend(el.subelements or [])
        return inline_elements

    def get_element_by_path(self, path):
        # remove indexed inline marks
        path_string = re.sub(r'([a-zA-Z0-9]+)_#{\1:[0-9]+}', r'\1', path)
        # add extra underscore to split correctly
        path_string = re.sub(r'(:choice_\d+:_)', r'\1_', path_string)
        path_names = path_string.split(self.nesting_connector)
        el = self
        for name in path_names[1:]:
            el = el.get_subelement(name)
        return el

    def get_subelement(self, name):
        for sub in self.subelements:
            if sub.name == name:
                return sub
        return None

    def get_mask(self):
        if self.inlines_needed():
            result = self._get_name_with_inline_suffix(index=r'\d+')
        else:
            result = self.name
        return result

    def get_required_masks(self, hidden_fields_masks):
        required = []
        elements = [('', self)]
        while elements:
            prefix, el = elements.pop()
            new_prefix = ('__' if prefix else '').join([prefix, el.get_mask()])
            if el.required and new_prefix not in hidden_fields_masks:
                required.append('^{}$'.format(new_prefix))
            for sub in el.subelements:
                elements.append((new_prefix, sub))
        return required

    @property
    def required(self):
        return self.min_occurs > 0

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

    def get_class_required(self):
        return 'required' if self.required else ''

    def set_initial_data(self, data):
        self.initial_data = data
        if data:
            for el in self.subelements:
                el.set_initial_data(self.initial_data)
        return self

    def get_ordered_dict_with_data(self, data):
        value = data[self.name]
        if isinstance(value, list):
            return [self.get_ordered_dict_with_data({self.name: v}) for v in value]

        if not isinstance(value, dict):
            return value

        ordata = OrderedDict()
        subelements = list(self.subelements)
        while subelements:
            sub = subelements.pop(0)
            if ':choice' in sub.name:
                subelements = sub.subelements + subelements
            if sub.name in value:
                ordata[sub.name] = sub.get_ordered_dict_with_data(value)

        return ordata

    def _print_tree(self, level=0):
        print(level * '--', self.name)
        for el in self.subelements:
            el._print_tree(level+1)
