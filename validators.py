import re

funcs = {
    'minLength': (lambda r, v: len(v) >= int(r),
                  'Length should be greater than {rvalue}'),

    'length': (lambda r, v: len(v) == int(r),
               'Length should be equal to {rvalue}'),

    'maxLength': (lambda r, v: len(v) <= int(r),
                  'Length should be lesst than {rvalue}'),

    'pattern': (lambda r, v: re.match(r, str(v)),
                'Value should match {rvalue}'),

    'enumeration': (lambda r, v: v in r,
                    'Should be one of {rvalue}'),

    'maxInclusive': (lambda r, v: v <= int(r),
                     'Should be less than or equal to {rvalue}'),

    'maxExclusive': (lambda r, v: v < int(r),
                     'Should be less than {rvalue}'),

    'minInclusive': (lambda r, v: v >= int(r),
                     'Should be greater than or equal to {rvalue}'),

    'minExclusive': (lambda r, v: v > int(r),
                     'Should be greater than {rvalue}'),

    'totalDigits': (lambda r, v: len(re.sub('[,.L]', '', str(v))) < int(r),
                    'Total digits count should be less than {rvalue}'),

    'fractionDigits': (lambda r, v: len(str(v).split('.')[-1]) < int(r),
                       'Fraction digits count should be less than {rvalue}'),

    'whiteSpace': (lambda r, v: True, 'Error message'),
    'Assertions': (lambda r, v: True, 'Error message'),
    'explicitTimezone': (lambda r, v: True, 'Error message'),
}


class Validator:

    def __init__(self, rname, rvalue):
        self.test_func, self.error_message = funcs[rname]
        self.rvalue = rvalue

    def __call__(self, value):
        result = False
        result = self.test_func(self.rvalue, value)
        if not result:
            return self.error_message.format(rvalue=self.rvalue, value=value)
