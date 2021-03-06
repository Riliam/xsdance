# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division, absolute_import  # NOQA

import copy
import os

from lxml import etree

from .element import Element
from .utils import Validator

_ = lambda x: x


class x:

    @staticmethod
    def get_tag(node):
        return node.tag.split('}')[-1]

    @staticmethod
    def element_content_to_dict(element):
        return {x.get_tag(el): (x.element_content_to_dict(el) or el.text)
                for el in element.iterchildren()}

    @staticmethod
    def full_path_of_included_schema(file_path, included_path):
        dir_path = os.path.dirname(file_path)

        abs_dir_path = os.path.abspath(dir_path)
        joined_path = os.path.join(abs_dir_path, included_path)
        full_path = os.path.normpath(joined_path)
        return full_path

    @staticmethod
    def exists(node):
        return node is not None


class CheckboxProcessor(object):

    def __init__(self, value):
        self.value = value

    def __call__(self, v):
        return self.value if v else ''


class ElementNotFound(BaseException):
    pass


class TypeNotFound(BaseException):
    pass


class Generator(object):

    ElementNotFound = ElementNotFound
    TypeNotFound = TypeNotFound
    PRIMITIVE_TYPES_PATH = 'IRS/primitive_types.xsd'
    UNBOUNDED = 999
    TOP_LEVEL_ELEMENT_NAME = 'schema'

    DT_FORMAT = {
        'DateType': 'YYYY-MM-DD HH:MM',
        'YearMonthType': 'YYYY-MM',
        'TaxYearEndMonthDtType': 'YYMM',
        'MonthType': 'MM',
        'MonthDayType': 'MM-DD',
        'QuarterEndDateType': 'YYYY-MM-DD',
        'YearType': 'YYYY',
        'TimeType': 'HH:MM:SS',
        'datetime': 'YYYY-MM-DD HH:MM:SS',
    }

    default_html_label = '''
        <label for="{name}" class="{required}">{label_text}</label>
    '''
    default_html_help = '''
        <span for="{name}" class="help-text">{help_text}</span>
    '''

    default_html_input = '''
        <input type="text" name="{name}" value="{value}" {disabled}/>
    '''
    default_html_datetime_picker = '''
        <div class="input-group date date-field">

             <input type="text"
                class="form-control"
                name="{{name}}"
                value="{{value}}"
                {{disabled}}
                data-date-format="{date_format}">

             <span class="input-group-addon">
                 <i class="icon-calendar"></i>
             </span>
        </div>
    '''
    default_html_checkbox = '''
        <input type="checkbox" name="{{name}}" value="{value}" {{disabled}} {{checked}}/>
    '''
    default_html_select = '''
        <select {multiple} name="{{name}}" {{disabled}} data-value="{{value}}">
            <option></option>
            {options}
        </select>
    '''
    default_html_option = '<option value="{value}">{text}</option>'
    default_html_edit_checkbox = '''
        <input id="ch_hide_{name}" name="ch_hide_{name}" type="checkbox" {checked} class="hide unstyled-field hidden-block"/>
    '''  # NOQA

    default_html_wrapper = '''
        <div class="grid-stack-item"
            {gridster_settings}
            data-element-name="{name}"
            data-element-prefixed-name="{prefixed_name}">

          <div class="grid-stack-item-content">
              {edit_checkbox}
              {content}
              {inline_buttons}
              {error}
          </div>
        </div>
    '''
    default_html_parent_element_wrapper = '''
        <div class="grid-stack fieldset-content">
            {content}
        </div>
    '''
    default_html_input_wrapper = '''
        <div class="fieldset fieldset-content">
            {label}
            {help_text}
            {html_input}
            <div class="error" id="{name}"></div>
        </div>
    '''

    default_html_inline_button_add = '''
        <a class="btn btn-default btn-add add-inline"
            data-element-name="{name}"
            data-elements-count="{current_elements_count}"
            data-max-elements-count="{max_count}"
            data-empty-item-wrapper="{empty}">

          <i class="icon-add"></i><span>Add</span>

        </a>
    '''
    default_html_inline_button_remove = '''
        <a class="btn btn-default btn-remove remove-inline"
            data-element-name="{name}"
            data-min-elements-count="{min_count}">

          <i class="icon-delete"></i><span>Remove</span>

        </a>
    '''
    default_html_inline_buttons_wrapper = '''
        <div class="wrap-btns">{content}</div>
    '''

    default_html_inline_item_wrapper = '''
        <div class="grid-stack-item" {gridster_settings} data-element-prefixed-name="{prefixed_name}">
            <div class="grid-stack-item-content">
                {content}
            </div>
            {remove_button}
        </div>
    '''

    def __init__(self, element_class=Element,
                 primitive_types_path=PRIMITIVE_TYPES_PATH,

                 html_label=default_html_label,
                 html_help=default_html_help,

                 html_input=default_html_input,
                 html_datetime_picker=default_html_datetime_picker,
                 html_checkbox=default_html_checkbox,
                 html_select=default_html_select,
                 html_option=default_html_option,
                 html_inline_button_add=default_html_inline_button_add,
                 html_inline_button_remove=default_html_inline_button_remove,
                 html_inline_buttons_wrapper=default_html_inline_buttons_wrapper,
                 html_wrapper=default_html_wrapper,
                 html_parent_element_wrapper=default_html_parent_element_wrapper,
                 html_input_wrapper=default_html_input_wrapper,
                 html_inline_item_wrapper=default_html_inline_item_wrapper,

                 html_edit_checkbox=default_html_edit_checkbox,
                 ):

        self.element_class = element_class
        self.primitive_types_path = primitive_types_path

        self.html_datetime_picker = html_datetime_picker
        self.html_checkbox = html_checkbox
        self.html_select = html_select
        self.html_option = html_option

        self.filepath = None
        self.elements_cache = {}
        self.nsmap = {}

        self.includes = []
        self.included_files = []
        self.root = None
        self.choice_counter = 0

        self.element_kwargs = {
            'html_label': html_label,
            'html_help': html_help,
            'html_input': html_input,
            'html_wrapper': html_wrapper,
            'html_parent_element_wrapper': html_parent_element_wrapper,
            'html_edit_checkbox': html_edit_checkbox,
            'html_input_wrapper': html_input_wrapper,
            'html_inline_button_add': html_inline_button_add,
            'html_inline_button_remove': html_inline_button_remove,
            'html_inline_buttons_wrapper': html_inline_buttons_wrapper,
            'html_inline_item_wrapper': html_inline_item_wrapper,
        }

    def create_element(self, *args, **kwargs):
        all_kwargs_dict = dict(self.element_kwargs, **kwargs)

        name = args[0]
        parent_name = kwargs.get('parent_name', None)
        if self.TOP_LEVEL_ELEMENT_NAME in (name, parent_name):
            all_kwargs_dict['html_wrapper'] = '''
                {edit_checkbox}
                {content}
            '''
            all_kwargs_dict['html_parent_element_wrapper'] = '''
                {content}
            '''
        el = self.element_class(*args, **all_kwargs_dict)
        el.UNBOUNDED = self.UNBOUNDED
        return el

    def run(self, xsd_filepath):
        self.filepath = xsd_filepath
        tree = etree.parse(xsd_filepath, parser=etree.XMLParser(
            remove_comments=True
        ))
        self.root = tree.getroot()
        self.nsmap = self.root.nsmap

        # BEGIN weird magic with namespaces:
        # This shit is in lxml, it yells at empty namespace, if you try
        # to use it in .find or .xpath kind of methods.

        # NOTE! ###   For elements with tag like 'Description'
        # NOTE! ###   use 'none:Description'
        self.nsmap['none'] = self.nsmap[None]
        self.nsmap.pop(None)
        # STOP weird magic

        primitive_types = etree.parse(self.primitive_types_path)
        primitive_types_root = primitive_types.getroot()
        self.includes.append(primitive_types_root)
        assert self.nsmap['xsd'] == primitive_types_root.nsmap['xsd']

        result = self.parse(self.root)
        return result

    def parse(self, node, el=None):
        func_name = 'parse_{}'.format(x.get_tag(node))
        func = getattr(self, func_name, None)
        if func:
            return func(node, el)
        return None

    def parse_schema(self, node, el):
        schema = self.create_element(self.TOP_LEVEL_ELEMENT_NAME)
        self._process_subnodes(node, schema,
                               skip=['simpleType', 'complexType'])
        return schema

    def parse_include(self, node=None, el=None, include_path=None):
        include_path = include_path\
            or x.full_path_of_included_schema(self.filepath, node.attrib['schemaLocation'])

        if include_path not in self.included_files:
            include_root = etree.parse(include_path).getroot()
            self.includes.append(include_root)
            self.included_files.append(include_path)

            nsmap = {k: v for k, v in include_root.nsmap.items() if k}
            include_includes = [x.full_path_of_included_schema(include_path, e.attrib['schemaLocation'])
                                for e in include_root.xpath('//xsd:include', namespaces=nsmap)]
            for include_include_path in include_includes:
                self.parse_include(include_path=include_include_path, el=el)

    def parse_import(self, node, el):
        self.parse_include(node, el)

    def parse_element(self, node, parent_el):
        new_el = self._get_element_from_cache_or_create(node, parent_el)
        parent_el.add_subelement(new_el)

        type_name = node.attrib.get('type', None)
        if type_name:
            self._process_type_by_name(type_name, new_el)

        new_el.min_occurs = int(node.attrib.get('minOccurs', 1))
        max_occurs = node.attrib.get('maxOccurs', 1)
        new_el.max_occurs = int(Generator.UNBOUNDED
                                if max_occurs == 'unbounded'
                                else max_occurs)
        self._process_subnodes(node, new_el)

    def parse_choice(self, node, parent_el):
        choice_name = ':choice_{}:'.format(self.choice_counter)
        self.choice_counter += 1
        choice_element = self.create_element(choice_name, parent_name=parent_el.name)
        parent_el.add_subelement(choice_element)

        min_occurs = int(node.attrib.get('minOccurs', 1))
        choice_element.min_occurs = min_occurs
        max_occurs = node.attrib.get('maxOccurs', 1)
        choice_element.max_occurs = int(Generator.UNBOUNDED
                                        if max_occurs == 'unbounded'
                                        else max_occurs)
        if choice_element.min_occurs == choice_element.max_occurs:
            label = _('Fill {min} of the following boxes')
        elif choice_element.max_occurs == Generator.UNBOUNDED:
            label = _('Fill {min} or more of the following boxes')
        else:
            label = _('Fill {min} to {max} of the following boxes')
        choice_element.label_text = label.format(min=choice_element.min_occurs,
                                                 max=choice_element.max_occurs)

        self._process_subnodes(node, choice_element)

    def parse_annotation(self, node, el):
        description_1 = \
            node.find('.//none:Description', namespaces=self.nsmap)
        description_2 = \
            node.find('.//xsd:Description', namespaces=self.nsmap)
        el.label_text = el.label_text or getattr(description_1, 'text', '') or \
            getattr(description_2, 'text', '')
        el.add_kwargs(**x.element_content_to_dict(node))

    def parse_sequence(self, node, el):
        self._process_subnodes(node, el)

    # parse attributes

    def parse_attribute(self, node, el):
        # TODO
        self._process_subnodes(node, el)

    def parse_attributeGroup(self, node, el):
        # TODO
        self._process_subnodes(node, el)

    # parse type

    def parse_simpleType(self, node, el):
        self._process_subnodes(node, el)

    def parse_simpleContent(self, node, el):
        self._process_subnodes(node, el)

    def parse_complexType(self, node, el):
        self._process_subnodes(node, el)

    def parse_complexContent(self, node, el):
        self._process_subnodes(node, el)

    # parse extensions and restrictions

    def parse_extension(self, node, el):
        base_type_name = node.attrib.get('base', None)
        if base_type_name:
            self._process_type_by_name(base_type_name, el)

        self._process_subnodes(node, el)

    def parse_restriction(self, node, el):
        base_type_name = node.attrib.get('base', None)
        if base_type_name:
            self._process_type_by_name(base_type_name, el)

        restrictions = [(x.get_tag(n), n.attrib.get('value', '')) for n in node
                        if x.get_tag(n) != 'enumeration']

        for rname, rvalue in restrictions:
            el.add_validator(Validator(rname, rvalue))

        enum_items = [n.attrib.get('value', '') for n in node
                      if x.get_tag(n) == 'enumeration']
        if enum_items:
            if len(enum_items) == 1:
                value = enum_items[0]
                html_input = self.html_checkbox.format(value=value)

                el.html_input = html_input
                el.add_processor(CheckboxProcessor(value))
            else:
                choices = list(zip(enum_items, enum_items))
                options = [self.html_option.format(value=value, text=text)
                           for value, text in choices]
                html_input = self.html_select.format(
                    multiple='multiple' if el.max_occurs > 1 else '',
                    options=''.join(options))
                el.html_input = html_input
            el.add_validator(Validator('enumeration', enum_items))

    # helpers

    def _get_element_from_cache_or_create(self, node, parent_el):
        name = node.attrib.get('name', None)
        ref = node.attrib.get('ref', None)
        new_el = None
        if name:
            new_el = self.create_element(name, parent_name=parent_el.name)
            self.elements_cache[name] = new_el
        elif ref:
            cached_el = self.elements_cache.get(ref, None)
            if cached_el:
                new_el = copy.deepcopy(cached_el)
        if not new_el:
            raise Generator.ElementNotFound
        return new_el

    def _process_subnodes(self, top_node, el, skip=None):
        skip = skip or []
        for node in top_node:
            if x.get_tag(node) not in skip:
                self.parse(node, el)

    def _process_type_by_name(self, type_name, el):
        if 'irs:' in type_name:
            type_name = type_name.split('irs:')[-1]
        if 'xsd:' in type_name:
            type_name = type_name.split('xsd:')[-1]

        # if type is one of datetime picker types,
        # assign corresponding html input and format
        dt_format = self.DT_FORMAT.get(type_name, '')
        if dt_format:
            el.html_input = self.default_html_datetime_picker.format(
                date_format=dt_format)
        # end datepicker block

        if type_name == 'anySimpleType':
            return
        simpleType_expr = './/xsd:simpleType[@name="{}"]'.format(type_name)
        complexType_expr = './/xsd:complexType[@name="{}"]'.format(type_name)

        queue = [self.root] + self.includes
        for root in queue:
            node = root.find(simpleType_expr, namespaces=self.nsmap)
            if not x.exists(node):
                node = root.find(complexType_expr, namespaces=self.nsmap)

            if x.exists(node):
                self.parse(node, el)
                break
        else:
            raise Generator.TypeNotFound('{} not found'.format(type_name))
