import json
from typing import List, Sequence

from shalchemy import bin
from shalchemy.test.base import TestCase
from shalchemy.types import PublicKeywordArgument

probe = bin.shalchemyprobe

def quirky_render(keyword: str, value: PublicKeywordArgument) -> Sequence[str]:
    def alternate_case(s: str):
        result: List[str] = []
        for index, char in enumerate(s):
            if index % 2 == 0:
                result.append(char.upper())
            else:
                result.append(char.lower())
        return ''.join(result)
    return [f'--{keyword.upper()}', alternate_case(str(value))]


class TestArguments(TestCase):
    def test_shlexing(self):
        stdout = str(probe.args('this   -should  --be="parsed   like bash" -- more stuff   --goes  here'))
        parsed = json.loads(stdout)
        self.assertEqual(parsed[1:], [
            'args',
            'this',
            '-should',
            '--be=parsed   like bash',
            '--',
            'more',
            'stuff',
            '--goes',
            'here',
        ])

    def test_no_shlexing(self):
        stdout = str(probe.args('blah', 'this   -should  --be="parsed   like bash" -- more stuff   --goes  here'))
        parsed = json.loads(stdout)
        self.assertEqual(parsed[1:], [
            'args',
            'blah',
            'this   -should  --be="parsed   like bash" -- more stuff   --goes  here',
        ])

    def test_no_shlexing_list(self):
        stdout = str(probe.args(['this   -should  --be="parsed   like bash" -- more stuff   --goes  here']))
        parsed = json.loads(stdout)
        self.assertEqual(parsed[1:], [
            'args',
            'this   -should  --be="parsed   like bash" -- more stuff   --goes  here',
        ])

    def test_curried_expressions(self):
        probe_args = probe.args
        curried1 = probe_args.show.every.argument
        curried2 = curried1(fruit='apple', animal='sugar glider')
        curried3 = curried2.more('positional arguments', happy=True, sad=False, count=5)
        stdout = str(curried3)
        parsed = json.loads(stdout)
        self.assertEqual(parsed[1:], [
            'args',
            'show',
            'every',
            'argument',
            '--fruit=apple',
            '--animal=sugar glider',
            'more',
            'positional arguments',
            '--happy',
            '--count=5',
        ])
        print(parsed)

    def test_quirky_render(self):
        quirky_probe = bin.shalchemyprobe.args(_kwarg_render=quirky_render)
        stdout = str(quirky_probe('show', 'arguments', keyword='value', happy=True))
        parsed = json.loads(stdout)
        self.assertEqual(parsed[1:], [
            'args',
            'show',
            'arguments',
            '--KEYWORD',
            'VaLuE',
            '--HAPPY',
            'TrUe',
        ])

