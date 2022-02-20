# Note that you need the -s flag on pytest when you run these tests otherwise
# some of the tests will fail. In other words, you need to type `pytest -s`

import io
import tempfile

from shalchemy import sh, bin
from shalchemy.test.base import TestCase

complain = bin.shalchemyprobe.complain
errcat = bin.shalchemyprobe.errcat


class TestRedirectionSimple(TestCase):
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
        # Passing the filename should make it open its own copy so no need to re-seek
        self.assertEqual(str(bin.cat < self.filename), self.content)

    def test_file_in(self):
        self.write_file(self.content)
        self.fileobj.seek(0)
        self.assertEqual(str(bin.cat < self.fileobj), self.content)

        # Passing a file object should pass it our actual file descriptor
        # So it moves our pointer as well
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

    # Tests for >=
    def test_stderr_to_stdout(self):
        # Plain stderr redirect
        self.assertEqual(str(complain('--both', '-n', self.content) >= '&1'), self.content * 2)
        # Using the err_ function
        self.assertEqual(str(complain('--both', '-n', self.content).err_('&1')), self.content * 2)
        # Setting append=True should do nothing
        self.assertEqual(str(complain('--both', '-n', self.content).err_('&1', append=True)), self.content * 2)

    def test_filename_err(self):
        # Works
        sh.run(complain('-n', self.content) >= self.filename)
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(complain('-n', self.content) >= self.filename)
        sh.run(complain('-n', self.content) >= self.filename)
        self.assertEqual(self.read_file(), self.content)

    def test_file_err(self):
        # Works
        sh.run(complain('-n', self.content) >= self.fileobj)
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(complain('-n', self.content) >= self.fileobj)
        sh.run(complain('-n', self.content) >= self.fileobj)
        self.assertEqual(self.read_file(), self.content)

    def test_stream_err(self):
        with io.StringIO() as stream:
            # Works
            sh.run(complain('-n', self.content) >= stream)
            stream.seek(0)
            self.assertEqual(stream.read(), self.content)
            # Appending
            sh.run(complain('-n', self.content) >= stream)
            sh.run(complain('-n', self.content) >= stream)
            stream.seek(0)
            self.assertEqual(stream.read(), self.content)

    def test_filename_err_explicit(self):
        # Works
        sh.run(complain('-n', self.content).err_(self.filename))
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(complain('-n', self.content).err_(self.filename))
        sh.run(complain('-n', self.content).err_(self.filename))
        self.assertEqual(self.read_file(), self.content)

    # Tests for 2>>
    def test_filename_err_append(self):
        # Works
        sh.run(complain('-n', self.content).err_(self.filename, append=True))
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(complain('-n', self.content).err_(self.filename, append=True))
        sh.run(complain('-n', self.content).err_(self.filename, append=True))
        self.assertEqual(self.read_file(), self.content * 3)

    def test_file_err_append(self):
        # Works
        sh.run(complain('-n', self.content).err_(self.fileobj, append=True))
        self.assertEqual(self.read_file(), self.content)
        # Appending
        sh.run(complain('-n', self.content).err_(self.fileobj, append=True))
        sh.run(complain('-n', self.content).err_(self.fileobj, append=True))
        self.assertEqual(self.read_file(), self.content * 3)

    def test_stream_err_append(self):
        with io.StringIO() as stream:
            # Works
            sh.run(complain('-n', self.content).err_(stream, append=True))
            stream.seek(0)
            self.assertEqual(stream.read(), self.content)
            # # Appending
            sh.run(complain('-n', self.content).err_(stream, append=True))
            sh.run(complain('-n', self.content).err_(stream, append=True))
            stream.seek(0)
            self.assertEqual(stream.read(), self.content * 3)


class TestRedirectionChained(TestCase):
    def test_stderr_stdout_devnull(self):
        sh.run(complain('--both', '-n', self.content).err_('&1', append=True))
        self.assertEqual(self.read_stdout(), self.content * 2)

        sh.run(complain('--both', '-n', self.content).err_('&1', append=True).out_('/dev/null'))
        self.assertEqual(self.read_stdout(), '')

        sh.run(complain('--both', '-n', self.content).out_('/dev/null').err_('&1', append=True))
        self.assertEqual(self.read_stdout(), '')

    def test_all_mixed(self):
        stream_in = io.StringIO(self.content)

        with tempfile.TemporaryFile('rt') as tferr:
            # Go crazy and do every possible way of redirection together
            sh.run(((errcat('--both') < stream_in) >= tferr) > self.filename)
            tferr.seek(0)
            self.assertEqual(tferr.read(), self.content)
            self.assertEqual(self.fileobj.read(), self.content)

    def test_all_files(self):
        stream_in = io.StringIO(self.content)
        stream_out = io.StringIO()
        stream_err = io.StringIO()

        sh.run(
            errcat('--both')
                .in_(stream_in)
                .out_(stream_out)
                .err_(stream_err)
        )

        stream_out.seek(0)
        stream_err.seek(0)

        self.assertEqual(stream_out.read(), self.content)
        self.assertEqual(stream_err.read(), self.content)

        stream_in.close()
        stream_out.close()
        stream_err.close()


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
        sh.run(bin.echo('-n', 'hello') > stream)
        stream.seek(0)
        self.assertEqual(stream.read(), 'hello')
        self.assertEqual(str(bin.cat < io.StringIO('hello world')), 'hello world')

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
