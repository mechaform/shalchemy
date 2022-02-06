from glob import glob
import textwrap
from typing import Optional

import os
import tempfile
import unittest
import pytest

import shalchemy as sha
from shalchemy import sh, bin
from shalchemy.bin import cat, find, grep, wc
import shalchemy.runner

FAKE_STDIN = tempfile.TemporaryFile()
shalchemy.runner._DEFAULT_STDIN = FAKE_STDIN

os.chdir(os.path.dirname(__file__))


class TestShalchemy(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def capfd(self, capfd):
        self.capfd = capfd

    def test_basic(self):
        self.assertTrue(cat('./fixtures/shuffled_words.txt') | grep('apple') > '/dev/null')
        self.assertEqual(self.capfd.readouterr().out, '')
        self.assertEqual(self.capfd.readouterr().err, '')

        self.assertTrue(cat('./fixtures/shuffled_words.txt') | grep('apple'))
        self.assertEqual(self.capfd.readouterr().out.strip(), 'apple')
        self.assertEqual(self.capfd.readouterr().err, '')

        self.assertTrue(grep('apple') < './fixtures/shuffled_words.txt')
        self.assertEqual(self.capfd.readouterr().out.strip(), 'apple')
        self.assertEqual(self.capfd.readouterr().err, '')

        self.assertEqual(str(grep('apple') < './fixtures/shuffled_words.txt').rstrip(), 'apple')
        self.assertEqual(int(grep('apple') | sh('wc -c') < './fixtures/shuffled_words.txt'), 6)
        self.assertEqual(self.capfd.readouterr().out, '')
        self.assertEqual(self.capfd.readouterr().err, '')

    def test_if(self):
        if not ((grep('apple') < './fixtures/shuffled_words.txt')) > '/dev/null':
            raise Exception('That should have been true')
        if grep('impossible') < './fixtures/shuffled_words.txt':
            raise Exception('That should have been true')

    def test_chained(self):
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
        sha.run((sh('tr [a-z] [A-Z]') < some_input) > some_output)
        some_output.seek(0)
        result = some_output.read()
        some_input.close()
        some_output.close()
        self.assertEqual(result, 'HELLO WORLD')

    def test_file_redirects_alt(self):
        some_input = tempfile.TemporaryFile('w+')
        some_output = tempfile.TemporaryFile('w+')
        some_input.write('hello world')
        some_input.seek(0)
        sha.run(sh('tr [a-z] [A-Z]').in_(some_input).out(some_output))
        some_output.seek(0)
        result = some_output.read()
        some_input.close()
        some_output.close()
        self.assertEqual(result, 'HELLO WORLD')

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
                sha.run(cat(file) > tf)
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


# # You can check if commands ran successfully by casting to bool or directly using it in a conditional
# if (grep('-i', 'E') < 'words.txt') | grep('w'):
#     print('Found it!')
# else:
#     print('It was not there!')

# # You can directly use files (or other file-like objects) opened in Python as redirection targets!
# with open('animals.txt', 'w+') as file:
#     file.write('Beetle\nChimpanzee\nAardvark')
#     file.seek(0)
#     sha.run(sort < file)

# sha.run(sh('rm', 'animals.txt'))

# sha.run(mkdir('hello'))

# os.chdir('hello')
# sha.run(bin.pwd)


# def test_echo():
#     assert(str(echo('hello world')) == 'hello world')

# '''
# curl website.com | sort > sorted.txt
# diff <(curl website.com) <(curl evilsite.com)

# # Output of both file commands get saved into a tempfile then diff reads both tempfiles
# diff <(curl website.com) <(curl evilsite.com)
# sh('diff', sh('curl website.com').read_sub, sh('curl evilsite.com').read_sub)

# # Input of both file commands come from tee then the output of both get flushed to tee's stdout
# cat words.txt | tee >(sort) >(sort -r)
# sh('cat words.txt') | sh('tee', sh('sort').wsub, sh('sort -r').wsub)

# cat <(curl https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/5d752e5f0702da315298a6bb5a771586d6ff445c/wordle-answers-alphabetical.txt) | tee >(sort) >(sort -r) > /dev/null

# cat words.txt | tee > /dev/null >(sort -r) >(sort) | cat
# '''

if __name__ == '__main__':
    unittest.main()
