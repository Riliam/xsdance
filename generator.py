import copy
import os

from lxml import etree

from element import Element
from utils import make_exception


Schema = Element


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


class Generator(object):

    ElementNotFound = make_exception('ElementNotFound')
    TypeNotFound = make_exception('TypeNotFound')

    def __init__(self):
        self.filepath = None
        self.elements_cache = {}
        self.nsmap = {}

        self.includes = []
        self.root = None

    def run(self, xsd_filepath):
        self.filepath = xsd_filepath
        tree = etree.parse(xsd_filepath, parser=etree.XMLParser(
            remove_comments=True
        ))
        self.root = tree.getroot()
        self.nsmap = self.root.nsmap

        # BEGIN weird magic with namespaces:
        # This shit is in lxml, it yells at empty namespace, if you try
        # to use it in .find or .xpath kind of methods
        # NOTE! ### for elements with tag like 'Description'
        # NOTE! ### use 'none:Description'
        self.nsmap['none'] = self.nsmap[None]
        self.nsmap.pop(None)
        # STOP weird magic

        result = self.parse(self.root)
        return result

    def parse(self, node, el=None):
        func_name = 'parse_{}'.format(x.get_tag(node))
        func = getattr(self, func_name, None)
        if func:
            return func(node, el)
        return None

    def parse_schema(self, top_node, el):
        schema = Schema('schema')
        self._process_subnodes(top_node, schema)
        return schema

    def parse_include(self, top_node, el):
        path = top_node.attrib['schemaLocation']
        include_path = x.full_path_of_included_schema(self.filepath, path)
        include_root = etree.parse(include_path, parser=etree.XMLParser(
            remove_comments=True
        )).getroot()
        self.includes.append(include_root)

    def parse_element(self, top_node, parent_el):
        new_el = self._get_element_from_cache_or_create(top_node)
        parent_el.add_subelement(new_el)

        type_name = top_node.attrib.get('type', None)
        if type_name:
            self._process_type_by_name(type_name, new_el)

        self._process_subnodes(top_node, new_el)

    def parse_choice(self, top_node, parent_el):
        choice_element = Element('choice')
        parent_el.add_subelement(choice_element)

        self._process_subnodes(top_node, choice_element)

    def parse_annotation(self, top_node, el):
        description =\
            top_node.find('.//none:Description', namespaces=self.nsmap)
        el.label_text = getattr(description, 'text', '')
        el.add_kwargs(**x.element_content_to_dict(top_node))

    def parse_sequence(self, top_node, el):
        self._process_subnodes(top_node, el)

    # parse attributes

    def parse_attribute(self, top_node, el):
        self._process_subnodes(top_node, el)

    def parse_attributeGroup(self, top_node, el):
        self._process_subnodes(top_node, el)

    # parse type

    def parse_simpleType(self, top_node, el):
        self._process_subnodes(top_node, el)

    def parse_simpleContent(self, top_node, el):
        self._process_subnodes(top_node, el)

    def parse_complexType(self, top_node, el):
        self._process_subnodes(top_node, el)

    def parse_complexContent(self, top_node, el):
        self._process_subnodes(top_node, el)

    # parse extensions and restrictions

    def parse_extension(self, top_node, el):
        self._process_subnodes(top_node, el)

    def parse_restriction(self, top_node, el):
        self._process_restrictions(top_node, el)

    # helpers

    def _process_restrictions(self, top_node, el):
        pass

    def _get_type_by_name(self, name):
        return None

    def _get_element_from_cache_or_create(self, top_node):
        name = top_node.attrib.get('name', None)
        ref = top_node.attrib.get('ref', None)
        new_el = None
        if name:
            new_el = Element(name)
            self.elements_cache[name] = new_el
        elif ref:
            cached_el = self.elements_cache.get(ref, None)
            if cached_el:
                new_el = copy.deepcopy(cached_el)
        if not new_el:
            raise Generator.ElementNotFound
        return new_el

    def _process_subnodes(self, top_node, el):
        for node in top_node:
            self.parse(node, el)

    def _process_type_by_name(self, type_name, el):
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
            raise Generator.TypeNotFound
