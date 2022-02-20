# Note that you need the -s flag on pytest when you run these tests otherwise
# some of the tests will fail. In other words, you need to type `pytest -s`
from typing import cast

import io
import os
import random
import tempfile
import unittest
import pytest

from shalchemy import sh, bin
import shalchemy.runner

FAKE_STDIN = cast(io.IOBase, tempfile.TemporaryFile())
FAKE_STDOUT = cast(io.IOBase, tempfile.TemporaryFile())
FAKE_STDERR = cast(io.IOBase, tempfile.TemporaryFile())
shalchemy.runner._DEFAULT_STDIN = FAKE_STDIN
shalchemy.runner._DEFAULT_STDOUT = FAKE_STDOUT
shalchemy.runner._DEFAULT_STDERR = FAKE_STDERR

os.chdir(os.path.dirname(__file__))


def random_string(length: int = 16):
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(length))


def random_filename():
    return os.path.join('garbage', f'{random_string()}.txt')


class TestRedirection(unittest.TestCase):
    content: str
    filename: str
    fileobj: io.TextIOWrapper

    @pytest.fixture(autouse=True)
    def capfd(self, capfd):
        self.capfd = capfd

    def setUp(self):
        self.content = random_string()
        self.filename = random_filename()
        self.fileobj = open(self.filename, 'w+')

    def tearDown(self):
        try:
            os.remove(self.filename)
        except FileNotFoundError:
            pass

    # Utilities
    def read_file(self) -> str:
        self.fileobj.seek(0)
        return self.fileobj.read()

    def write_file(self, content: str, append: bool = False):
        if not append:
            self.fileobj.seek(0)
        self.fileobj.write(content)
        self.fileobj.flush()

    # Tests for >
    def test_filename_out(self):
        # Works
        sh.run(bin.echo('-n', self.content) > self.filename)
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(bin.echo('-n', self.content) > self.filename)
        sh.run(bin.echo('-n', self.content) > self.filename)
        self.assertEqual(self.read_file(), self.content)

    def test_file_out(self):
        # Works
        sh.run(bin.echo('-n', self.content) > self.fileobj)
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(bin.echo('-n', self.content) > self.fileobj)
        sh.run(bin.echo('-n', self.content) > self.fileobj)
        self.assertEqual(self.read_file(), self.content)

    def test_stream_out(self):
        with io.StringIO() as stream:
            # Works
            sh.run(bin.echo('-n', self.content) > stream)
            stream.seek(0)
            self.assertEqual(stream.read(), self.content)
            # Appending
            sh.run(bin.echo('-n', self.content) > stream)
            sh.run(bin.echo('-n', self.content) > stream)
            stream.seek(0)
            self.assertEqual(stream.read(), self.content)

    def test_filename_out_explicit(self):
        # Works
        sh.run(bin.echo('-n', self.content).out_(self.filename))
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(bin.echo('-n', self.content).out_(self.filename))
        sh.run(bin.echo('-n', self.content).out_(self.filename))
        self.assertEqual(self.read_file(), self.content)

    # Tests for >>
    def test_filename_out_append(self):
        # Works
        sh.run(bin.echo('-n', self.content) >> self.filename)
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(bin.echo('-n', self.content) >> self.filename)
        sh.run(bin.echo('-n', self.content) >> self.filename)
        self.assertEqual(self.read_file(), self.content * 3)

    def test_file_out_append(self):
        # Works
        sh.run(bin.echo('-n', self.content) >> self.fileobj)
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(bin.echo('-n', self.content) >> self.fileobj)
        sh.run(bin.echo('-n', self.content) >> self.fileobj)
        self.assertEqual(self.read_file(), self.content * 3)

    def test_stream_out_append(self):
        with io.StringIO() as stream:
            # Works
            sh.run(bin.echo('-n', self.content) >> stream)
            stream.seek(0)
            self.assertEqual(stream.read(), self.content)
            # # Appending
            sh.run(bin.echo('-n', self.content) >> stream)
            sh.run(bin.echo('-n', self.content) >> stream)
            stream.seek(0)
            self.assertEqual(stream.read(), self.content * 3)

    def test_filename_out_append_explicit(self):
        # Works
        sh.run(bin.echo('-n', self.content).out_(self.filename, append=True))
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(bin.echo('-n', self.content).out_(self.filename, append=True))
        sh.run(bin.echo('-n', self.content).out_(self.filename, append=True))
        self.assertEqual(self.read_file(), self.content * 3)

    # Tests for <
    def test_filename_in(self):
        self.write_file(self.content)
        self.assertEqual(str(bin.cat < self.filename), self.content)

    def test_file_in(self):
        self.write_file(self.content)
        self.fileobj.seek(0)
        self.assertEqual(str(bin.cat < self.fileobj), self.content)
        self.assertEqual(str(bin.cat < self.fileobj), '')
        self.fileobj.seek(0)
        self.assertEqual(str(bin.cat < self.fileobj), self.content)

    def test_stream_in(self):
        with io.StringIO(self.content) as stream:
            self.assertEqual(str(bin.cat < stream), self.content)
            self.assertEqual(str(bin.cat < stream), '')
            stream.seek(0)
            self.assertEqual(str(bin.cat < stream), self.content)

    def test_stream_in_explicit(self):
        self.write_file(self.content)
        self.assertEqual(str(bin.cat.in_(self.filename)), self.content)


if __name__ == '__main__':
    unittest.main()
