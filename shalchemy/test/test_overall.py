# Note that you need the -s flag on pytest when you run these tests otherwise
# some of the tests will fail (i.e. `pytest -s`)
from typing import cast

import io
import tempfile
import textwrap
from glob import glob

from shalchemy import sh, bin
from shalchemy.bin import cat, diff, echo, find, grep, rm, wc
from shalchemy.test.base import TestCase


class TestOverall(TestCase):
    def test_basic(self):
        self.assertTrue(cat('./fixtures/shuffled_words.txt') | grep('apple') > '/dev/null')
        self.assertEqual(self.read_stdout(), '')
        self.assertEqual(self.read_stderr(), '')

        self.assertTrue(cat('./fixtures/shuffled_words.txt') | grep('apple'))
        self.assertEqual(self.read_stdout().strip(), 'apple')
        self.assertEqual(self.read_stderr(), '')

        self.assertTrue(grep('apple') < './fixtures/shuffled_words.txt')
        self.assertEqual(self.read_stdout().strip(), 'apple')
        self.assertEqual(self.read_stderr(), '')

        self.assertEqual(str(grep('apple') < './fixtures/shuffled_words.txt').rstrip(), 'apple')
        self.assertEqual(int(grep('apple') | sh('wc -c') < './fixtures/shuffled_words.txt'), 6)
        self.assertEqual(self.read_stdout(), '')
        self.assertEqual(self.read_stderr(), '')

    def test_pipe(self):
        self.assertEqual(
            int(
                cat(
                    './fixtures/shuffled_words.txt',
                    './fixtures/sorted_words.txt',
                    './fixtures/shuffled_words.txt',
                    './fixtures/sorted_words.txt',
                ) |
                wc('-l')
            ),
            40
        )
        self.assertEqual(
            int(
                cat(
                    './fixtures/shuffled_words.txt',
                    './fixtures/sorted_words.txt',
                    './fixtures/shuffled_words.txt',
                    './fixtures/sorted_words.txt',
                ) |
                sh('sort') |
                sh('uniq') |
                wc('-l')
            ),
            10
        )
        self.assertEqual(
            int(
                cat(
                    './fixtures/shuffled_words.txt',
                    './fixtures/sorted_words.txt',
                    './fixtures/shuffled_words.txt',
                    './fixtures/sorted_words.txt',
                ) |
                grep('a') |
                grep('t') |
                grep('e') |
                wc('-l')
            ),
            4
        )

    def test_file_redirects(self):
        some_input = tempfile.TemporaryFile('w+')
        some_output = tempfile.TemporaryFile('w+')
        some_input.write('hello world')
        some_input.seek(0)
        sh.run((sh('tr [a-z] [A-Z]') < some_input) > some_output)
        some_output.seek(0)
        result = some_output.read()
        some_input.close()
        some_output.close()
        self.assertEqual(result, 'HELLO WORLD')

    def test_io_strings(self):
        some_input = io.StringIO('hello world')
        some_output = io.StringIO()
        sh.run((sh('tr [a-z] [A-Z]') < some_input) > some_output)
        some_output.seek(0)
        result = some_output.read()
        some_input.close()
        some_output.close()
        self.assertEqual(result, 'HELLO WORLD')
        stream = io.StringIO()
        sh.run(echo('-n', 'hello') > stream)
        stream.seek(0)
        self.assertEqual(stream.read(), 'hello')
        self.assertEqual(str(cat < io.StringIO('hello world')), 'hello world')

    def test_file_redirects_alt(self):
        some_input = tempfile.TemporaryFile('w+')
        some_output = tempfile.TemporaryFile('w+')
        some_input.write('hello world')
        some_input.seek(0)
        sh.run(sh('tr [a-z] [A-Z]').in_(some_input).out_(some_output))
        some_output.seek(0)
        output_text = some_output.read()
        some_input.close()
        some_output.close()
        self.assertEqual(output_text, 'HELLO WORLD')

    def test_bool(self):
        if not ((grep('apple') < './fixtures/shuffled_words.txt') > '/dev/null'):
            raise Exception('That should have been true')
        if grep('impossible') < './fixtures/shuffled_words.txt':
            raise Exception('That should have been true')

    def test_iter(self):
        result = []
        for x in cat('./fixtures/shuffled_words.txt') | bin.sort:
            result.append(x)
        self.assertEqual(result, [
            'apple',
            'banana',
            'carrot',
            'grape',
            'lime',
            'mango',
            'orange',
            'papaya',
            'raspberry',
            'watermelon',
        ])

    def test_interpolate(self):
        result = str(bin.wc(f'-l {bin.find("./fixtures/ -name *_words.txt -type f")}'))
        expected = """
            10 ./fixtures/shuffled_words.txt
            10 ./fixtures/sorted_words.txt
            20 total
        """
        self.assertEqual(
            textwrap.dedent(result).strip(),
            textwrap.dedent(expected).strip(),
        )

    def test_find(self):
        with tempfile.TemporaryFile('w+') as tf:
            for file in find('./fixtures', '-name', '*_words.txt'):
                sh.run(cat(file) >> tf)
            tf.seek(0)
            result1 = tf.read()

        result2 = ''
        for filename in glob('./fixtures/*_words.txt'):
            with open(filename, 'r') as file:
                result2 += file.read()
        self.assertEqual(result1, result2)

    def test_large(self):
        result2 = str(cat('./fixtures/lorem_ipsum.txt') | bin.sort)
        result = []
        for x in cat('./fixtures/lorem_ipsum.txt') | bin.sort:
            result.append(x)
        self.assertEqual('\n'.join(result).strip(), result2.strip())

    def test_read_sub(self):
        self.assertTrue(diff(
            (cat('./fixtures/shuffled_words.txt') | bin.sort('-r')).read_sub,
            (cat('./fixtures/shuffled_words.txt') | bin.sort | bin.tac).read_sub,
        ) > '/dev/null')
        self.assertFalse(diff(
            (cat('./fixtures/shuffled_words.txt') | bin.sort('-r')).read_sub,
            (cat('./fixtures/shuffled_words.txt') | bin.sort).read_sub,
        ) > '/dev/null')

    def test_write_sub(self):
        sh.run(
            cat('./fixtures/shuffled_words.txt') |
            bin.tee(
                (cat > './fixtures/shuffled_words2.txt').write_sub,
                (cat > './fixtures/shuffled_words3.txt').write_sub,
            ) > '/dev/null'
        )
        self.assertEqual(
            str(cat('./fixtures/shuffled_words.txt')),
            str(cat('./fixtures/shuffled_words2.txt')),
        )
        self.assertEqual(
            str(cat('./fixtures/shuffled_words.txt')),
            str(cat('./fixtures/shuffled_words3.txt')),
        )
        sh.run(bin.rm('./fixtures/shuffled_words2.txt', './fixtures/shuffled_words3.txt'))
