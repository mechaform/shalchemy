from typing import cast

import io
import os
import random
import tempfile
import unittest

import shalchemy

FAKE_STDIN = cast(io.IOBase, tempfile.TemporaryFile())
FAKE_STDOUT = cast(io.IOBase, tempfile.TemporaryFile())
FAKE_STDERR = cast(io.IOBase, tempfile.TemporaryFile())
shalchemy.runner._DEFAULT_STDIN = FAKE_STDIN
shalchemy.runner._DEFAULT_STDOUT = FAKE_STDOUT
shalchemy.runner._DEFAULT_STDERR = FAKE_STDERR

os.chdir(os.path.dirname(__file__))


def random_string(length: int = 16) -> str:
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(length))


def random_filename() -> str:
    return os.path.join('garbage', f'{random_string()}.txt')


class TestCase(unittest.TestCase):
    content: str
    filename: str
    fileobj: io.TextIOWrapper

    def setUp(self):
        self.content = random_string()
        self.filename = random_filename()
        self.fileobj = open(self.filename, 'w+')
        self.clear_fake(FAKE_STDIN)
        self.clear_fake(FAKE_STDOUT)
        self.clear_fake(FAKE_STDERR)

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

    def clear_fake(self, fd: io.IOBase):
        fd.truncate(0)
        fd.seek(0)
        fd.flush()

    def read_stdout(self) -> str:
        FAKE_STDOUT.seek(0)
        bresult = FAKE_STDOUT.read()
        self.clear_fake(FAKE_STDOUT)
        return bresult.decode('utf-8')

    def read_stderr(self) -> str:
        FAKE_STDERR.seek(0)
        bresult = FAKE_STDERR.read()
        self.clear_fake(FAKE_STDERR)
        return bresult.decode('utf-8')
