# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division, absolute_import  # NOQA

from unittest import TestCase
from xsdance.utils import parse_inputs


class TestParseInputs(TestCase):
    maxDiff = None

    test_cases = [

        {
            'INPUTS': {
                "a__c": "Some text",
            },
            'SHOULD_BE': {
                "a": {
                    "c": "Some text",
                }
            },
        },


        {
            'INPUTS': {
                'a__d_#{d:0}': 'D value 0',
                'a__d_#{d:1}': 'D value 1',
            },
            'SHOULD_BE': {
                'a': {
                    'd': ['D value 0', 'D value 1'],
                },
            },
        },


        {
            'INPUTS': {
                'a__e_#{e:0}__f': 'F value of E value 0',
                'a__e_#{e:0}__g': 'G value of E value 0',
                'a__e_#{e:0}__h': 'H value of E value 0',
                'a__e_#{e:1}__f': 'F value of E value 1',
                'a__e_#{e:1}__g': 'G value of E value 1',
                'a__e_#{e:1}__h': 'H value of E value 1',
            },
            'SHOULD_BE': {
                'a': {
                    'e': [
                        {'f': 'F value of E value 0',
                         'g': 'G value of E value 0',
                         'h': 'H value of E value 0'},

                        {'f': 'F value of E value 1',
                         'g': 'G value of E value 1',
                         'h': 'H value of E value 1'}
                    ],

                },
            },
        },


        {
            'INPUTS': {
                'a__j__:choice_0:_i': 12,
            },
            'SHOULD_BE': {
                'a': {
                    'j': {
                        'i': 12,
                    },
                },
            },
        },


        {
            'INPUTS': {
                'a__:choice_1:_k': 'A',
                'a__:choice_1:_l': 'B',
            },
            'SHOULD_BE': {
                'a': {
                    'k': 'A',
                    'l': 'B',
                },
            },
        },
    ]

    def check_one_case(self, inputs, should_be):
        self.assertDictEqual(should_be, parse_inputs(inputs))

    def test_run(self):
        for case in self.test_cases:
            self.check_one_case(case['INPUTS'], case['SHOULD_BE'])
