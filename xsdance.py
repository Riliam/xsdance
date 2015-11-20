import json

from utils import serialize_xml, make_exception


class Element(object):

    ValueRequiredError = make_exception('ValueRequiredError')
    ValidationError = make_exception('ValidationError')

    nesting_connector = '__'
    default_input = '<input name="{name}" value="{value}"/>'
    default_wrapper = '<div data-element={name}>{content}<span class="error"></span></div>'  # NOQA
    parent_element_wrapper = '<div style="border: 1px solid black;"><h5>{parent_name}</h5>{content}</div>'  # NOQA

    error_messages = {
        'required': 'This field is required',
    }

    def __init__(self, name, value=None, label_text='',
                 html_input=default_input,
                 html_wrapper=default_wrapper,
                 min_occurs=1, max_occurs=1,
                 parent=None, validators=None):
        self.name = name
        self.value = value
        self.label_text = label_text or name
        self.html_input = html_input
        self.html_wrapper = html_wrapper
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.parent = parent
        self.validators = validators or []

        self.subelements = []

        if parent:
            parent._add_subelement(self)

    def __repr__(self):
        return self.name

    @property
    def prefixed_name(self):
        name = self.name
        if self.parent:
            name = '{prefix}{connector}{name}'.format(
                prefix=self._get_full_prefix(),
                connector=self.nesting_connector,
                name=name)
        return name

    def render_html(self):
        content = self._render_subelements_html()\
            or self._html_input_with_value()
        return self.html_wrapper.format(
            name=self.prefixed_name,
            content=content)

    def render_xml(self):
        if not self.value:
            raise Element.ValueRequiredError
        return serialize_xml(self.value)

    def render_json(self):
        if not self.value:
            raise Element.ValueRequiredError
        return json.dumps(self.value)

    def validate(self, d):
        errors = {}
        value = d[self.name]
        for sub in self.subelements:
            v = value.get(sub.name, None)
            if v is None and sub.min_occurs > 0:
                errors[sub.prefixed_name] = [self.error_messages['required']]
            else:
                suberrors = sub.validate(value)
                if suberrors:
                    errors.update(suberrors)

        for validator in self.validators:
            result = validator(value)
            if result:
                errors[self.prefixed_name] =\
                    errors.get(self.prefixed_name, []) + [result]

        return errors

    def _html_input_with_value(self):
        name = self.prefixed_name
        if self.html_input:
            return self.html_input.format(name=name, value=self.value or '')
        return ''

    def _render_subelements_html(self):
        content = ''.join(el.render_html() for el in self.subelements)
        if content:
            content = self.parent_element_wrapper.format(
                parent_name=self.name,
                content=content)
        return content

    def _add_subelement(self, el):
        self.subelements.append(el)

    def _get_full_prefix(self):
        parents = []
        el = self
        while getattr(el, 'parent'):
            parents.append(el.parent.name)
            el = el.parent
        return self.nesting_connector.join(reversed(parents))
