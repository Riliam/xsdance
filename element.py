from utils import serialize_xml, serialize_json, make_exception


class Element(object):

    ValueRequiredError = make_exception('ValueRequiredError')

    nesting_connector = '__'
    default_html_label = '<label for="{name}">{label_text}</label>'
    default_html_help = '<span for="{name}">{help_text}</span>'
    default_html_input = '<input id="{name}" name="{name}" value="{value}"/>'
    default_html_wrapper =\
        '''<div data-element={name}>
               {content}
               <span class="error"></span>
           </div>'''
    default_parent_element_wrapper =\
        '''<div style="border: 1px solid black;">
               <h4>{parent_label}</h4>
               <div data-parent={parent_name}>{content}</div>
           </div>
        '''

    error_messages = {
        'required': 'This field is required',
    }

    def __init__(self, name, initial_data=None,
                 label_text='',
                 min_occurs=1,
                 max_occurs=1,
                 parent=None,
                 validators=None,
                 processors=None,
                 html_label=default_html_label,
                 html_input=default_html_input,
                 html_wrapper=default_html_wrapper,
                 html_parent_element_wrapper=default_parent_element_wrapper,
                 html_help=default_html_help,
                 **kwargs):
        self.name = name
        self.initial_data = initial_data or {}
        self.label_text = label_text
        self.html_label = html_label
        self.html_input = html_input
        self.html_wrapper = html_wrapper
        self.html_parent_element_wrapper = html_parent_element_wrapper
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.parent = parent
        self.validators = validators or []
        self.processors = processors or []
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
        if not self.initial_data:
            raise Element.ValueRequiredError
        return serialize_xml(self.cleaned_data())

    def render_json(self):
        if not self.initial_data:
            raise Element.ValueRequiredError
        return serialize_json(self.cleaned_data())

    def validate(self, d):
        errors = {}
        value = d[self.name]
        for sub in self.subelements:
            v = sub.process_value(value.get(sub.name, None))
            if v is None and sub.min_occurs > 0:
                errors[sub.prefixed_name] = [self.error_messages['required']]
            else:
                suberrors = sub.validate(value)
                if suberrors:
                    errors.update(suberrors)

        processed = self.process_value(value)
        self.cleaned_value = processed

        for validator in self.validators:
            result = validator(processed)
            if result:
                errors[self.prefixed_name] =\
                    errors.get(self.prefixed_name, []) + [result]

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

    def _get_full_prefix(self):
        parents = []
        el = self
        while getattr(el, 'parent'):
            parents.append(el.parent.name)
            el = el.parent
        return self.nesting_connector.join(reversed(parents))

    def _render_subelements_html(self):
        content = ''.join(el.render_html() for el in self.subelements)
        if content:
            content = self.html_parent_element_wrapper.format(
                parent_label=self.label_text or self.name,
                parent_name=self.name,
                content=content)
        return content

    def _html_input_with_value(self):
        name = self.prefixed_name

        if self.html_input:
            html_label = self.html_label.format(
                name=name,
                label_text=self.label_text or name,
            )
            input_html = self.html_input.format(
                name=name,
                value=self.initial_data.get(self.name) or ''
            )
            return html_label + input_html
        return ''

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
