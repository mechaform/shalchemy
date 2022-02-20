from tempfile import TemporaryFile
from typing import Any, cast, IO, List, Optional, Sequence, Union

import io
import shlex
import textwrap
import subprocess

from .arguments import UncompiledArgument, compile_arguments
from .run_result import (
    FileResult,
    RunResult,
    ReadSubstitutePreparation,
    StreamPipe,
    WriteSubstitutePreparation,
)
from .types import (
    ParenthesisKind,
    PublicArgument,
    ShalchemyFile,
    PublicKeywordArgument,
    KeywordArgumentRenderer,
    ShalchemyOutputStream,
)


def is_shalchemy_expression(object: Any) -> bool:
    if isinstance(object, CommandExpression):
        return True
    if isinstance(object, PipeExpression):
        return True
    if isinstance(object, RedirectInExpression):
        return True
    if isinstance(object, RedirectOutExpression):
        return True
    return False


def is_shalchemy_file(object: Any) -> bool:
    if isinstance(object, str):
        return True
    if isinstance(object, io.IOBase):
        return True
    return False


def represent_file(file: Union[str, io.IOBase]):
    if isinstance(file, str):
        return shlex.quote(file)
    elif isinstance(file, io.IOBase) and getattr(file, 'name', None):
        return f'File({getattr(file, "name")})'
    else:
        return repr(file)


class ShalchemyExpression:
    @property
    def read_sub(self) -> 'ReadSubstitute':
        return ReadSubstitute(self)

    @property
    def write_sub(self) -> 'WriteSubstitute':
        return WriteSubstitute(self)

    def __or__(self, rhs: 'ShalchemyExpression'):
        return PipeExpression(self, rhs)

    def __lt__(self, rhs: ShalchemyFile):
        return RedirectInExpression(self, rhs)

    def __gt__(self, rhs: ShalchemyFile):
        return RedirectOutExpression(self, rhs, append=False)

    def __rshift__(self, rhs: ShalchemyFile):
        return RedirectOutExpression(self, rhs, append=True)

    def __ge__(self, rhs: ShalchemyFile):
        return RedirectOutExpression(self, rhs, stderr=True, append=False)

    def in_(self, rhs: ShalchemyFile, append: bool = False):
        return RedirectInExpression(self, rhs)

    def out_(self, rhs: ShalchemyFile, append: bool = False):
        return RedirectOutExpression(self, rhs, append=append)

    def err_(self, rhs: ShalchemyFile, append: bool = False):
        return RedirectOutExpression(
            self,
            rhs,
            append=append,
            stderr=True,
        )

    def __bool__(self):
        from .runner import _internal_run
        result = _internal_run(self)
        result.wait()
        return result.main.returncode == 0

    def __int__(self):
        return int(str(self))

    def __str__(self):
        from .runner import _internal_run
        result = _internal_run(self, stdout=subprocess.PIPE)
        answer = result.main.stdout.read().decode()
        result.wait()
        return answer

    def __iter__(self):
        return str(self).rstrip('\n').split('\n').__iter__()

    def _run(
        self,
        stdin: Optional[ShalchemyOutputStream],
        stdout: Optional[ShalchemyOutputStream],
        stderr: Optional[ShalchemyOutputStream],
    ) -> RunResult:
        raise NotImplementedError()

    def _repr(self, paren: ParenthesisKind) -> str:
        raise NotImplementedError()


class CommandExpression(ShalchemyExpression):
    _args: Sequence[Union[str, UncompiledArgument]]
    _kwarg_render: KeywordArgumentRenderer

    def __init__(
        self,
        *args: Union[str, UncompiledArgument],
        _kwarg_render: KeywordArgumentRenderer = None
    ):
        self._args = args
        # Bypass mypy complaints about "assigning to a method"
        setattr(self, '_kwarg_render', _kwarg_render)


    def __call__(self, *args: PublicArgument, **kwargs: PublicKeywordArgument):
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
            return CommandExpression(
                *self._args,
                *shlex.split(args[0]),
                _kwarg_render=getattr(self, '_kwarg_render'),
            )

        renderer: KeywordArgumentRenderer
        if '_kwarg_render' in kwargs:
            renderer = cast(KeywordArgumentRenderer, kwargs.pop('_kwarg_render'))
        else:
            renderer = getattr(self, '_kwarg_render')

        compiled = compile_arguments(
            args,
            kwargs,
            _kwarg_render=renderer,
        )

        return CommandExpression(
            *self._args,
            *compiled,
            _kwarg_render=renderer,
        )

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        return self.__call__(attr)

    def _run(
        self,
        stdin: Optional[ShalchemyOutputStream],
        stdout: Optional[ShalchemyOutputStream],
        stderr: Optional[ShalchemyOutputStream],
    ) -> RunResult:
        opened_processes: List[subprocess.Popen] = []
        opened_files: List[ShalchemyOutputStream] = []
        opened_directories: List[str] = []
        opened_stream_pipes: List[StreamPipe] = []
        prepared_args: List[Union[WriteSubstitutePreparation, ReadSubstitutePreparation]] = []
        arguments: List[str] = []

        for arg in self._args:
            if isinstance(arg, (ReadSubstitute, WriteSubstitute)):
                preparation = arg._prepare(
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                )
                prepared_args.append(preparation)
                arguments.append(preparation.filename)
            elif isinstance(arg, UncompiledArgument):
                preparation = arg.value._prepare(
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                )
                compiled_args = arg.compile(preparation.filename)
                prepared_args.append(preparation)
                arguments.extend(compiled_args)
            else:
                arguments.append(arg)

        process = subprocess.Popen(
            arguments,
            stdin=cast(Union[IO, int, None], stdin),
            stdout=cast(Union[IO, int, None], stdout),
            stderr=cast(Union[IO, int, None], stderr),
        )

        for preparation in prepared_args:
            context = preparation._run()
            opened_processes.extend(context.processes)
            opened_files.extend(context.files)
            opened_directories.extend(context.directories)
            opened_stream_pipes.extend(context.stream_pipes)

        return RunResult(
            main=process,
            processes=[*opened_processes, process],
            files=opened_files,
            directories=opened_directories,
            stream_pipes=opened_stream_pipes,
        )

    def _repr(self, paren: ParenthesisKind):
        result = []
        for arg in self._args:
            if isinstance(arg, str):
                result.append(shlex.quote(arg))
            else:
                result.append(arg._repr())
        return ' '.join(result)

    def __repr__(self):
        return f'$({self._repr(ParenthesisKind.NEVER)})'


class PipeExpression(ShalchemyExpression):
    lhs: ShalchemyExpression
    rhs: ShalchemyExpression

    def __init__(self, lhs: ShalchemyExpression, rhs: ShalchemyExpression):
        if not is_shalchemy_expression(lhs):
            raise TypeError(f'{repr(lhs)} must be an ShalchemyExpression')
        if not is_shalchemy_expression(rhs):
            raise TypeError(f'{repr(rhs)} must be an ShalchemyExpression')
        self.lhs = lhs
        self.rhs = rhs

    def _run(
        self,
        stdin: Optional[ShalchemyOutputStream],
        stdout: Optional[ShalchemyOutputStream],
        stderr: Optional[ShalchemyOutputStream],
    ) -> RunResult:
        context_lhs = self.lhs._run(
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=stderr,
        )
        context_rhs = self.rhs._run(
            stdin=cast(io.IOBase, context_lhs.main.stdout),
            stdout=stdout,
            stderr=stderr,
        )
        return RunResult(
            main=context_rhs.main,
            processes=[*context_lhs.processes, *context_rhs.processes],
            files=[*context_lhs.files, *context_rhs.files],
            directories=[*context_lhs.directories, *context_rhs.directories],
            stream_pipes=[*context_lhs.stream_pipes, *context_rhs.stream_pipes],
        )

    def _repr(self, paren: ParenthesisKind = ParenthesisKind.COMPOUND_ONLY):
        repr_lhs = self.lhs._repr(ParenthesisKind.COMPOUND_ONLY)
        repr_rrhs = self.rhs._repr(ParenthesisKind.COMPOUND_ONLY)
        if paren == ParenthesisKind.NEVER:
            return f'{repr_lhs} | {repr_rrhs}'
        else:
            return f'({repr_lhs} | {repr_rrhs})'

    def __repr__(self):
        return f'$({self._repr(ParenthesisKind.NEVER)})'


class RedirectInExpression(ShalchemyExpression):
    lhs: ShalchemyExpression
    rhs: ShalchemyFile

    def __init__(self, lhs: ShalchemyExpression, rhs: ShalchemyFile):
        self.lhs = lhs
        self.rhs = rhs
        if not isinstance(rhs, (io.IOBase, str)):
            raise TypeError('Expected a str or io.IOBase', rhs)

    def _make_os_file(self, file: ShalchemyFile) -> FileResult:
        if isinstance(file, str):
            osfile = cast(io.IOBase, open(file, 'r'))
            return FileResult(fileno=osfile.fileno(), open_files=[osfile])

        try:
            fileno = file.fileno()
            return FileResult(fileno)
        except io.UnsupportedOperation:
            pass

        tf: io.IOBase
        if isinstance(file, io.BytesIO):
            tf = cast(io.IOBase, TemporaryFile('wb+'))
            tf.write(file.read())
            tf.seek(0)
        else:
            tf = cast(io.IOBase, TemporaryFile('wt+'))
            tf.write(file.read())
            tf.seek(0)
        return FileResult(tf.fileno(), open_files=[tf])

    def _run(
        self,
        stdin: Optional[ShalchemyOutputStream],
        stdout: Optional[ShalchemyOutputStream],
        stderr: Optional[ShalchemyOutputStream],
    ) -> RunResult:
        file_result = self._make_os_file(self.rhs)

        context_lhs = self.lhs._run(
            stdin=file_result.fileno,
            stdout=stdout,
            stderr=stderr,
        )
        return RunResult(
            main=context_lhs.main,
            processes=context_lhs.processes,
            files=[*context_lhs.files, *file_result.open_files],
            directories=context_lhs.directories,
            stream_pipes=context_lhs.stream_pipes,
        )

    def _repr(self, paren: ParenthesisKind):
        return f'{self.lhs._repr(ParenthesisKind.COMPOUND_ONLY)} < {represent_file(self.rhs)}'

    def __repr__(self):
        return f'$({self._repr(ParenthesisKind.NEVER)})'


class RedirectOutExpression(ShalchemyExpression):
    lhs: ShalchemyExpression
    rhs: ShalchemyFile
    redirect_stderr: bool
    append: bool
    _parents: List[ShalchemyExpression]
    _process: subprocess.Popen
    _file: io.TextIOWrapper

    def __init__(self, lhs, rhs, append: bool = False, stderr=False):
        self.lhs = lhs
        self.rhs = rhs
        self.append = append
        self.redirect_stderr = stderr
        self._parents = []


    def _make_os_file(self, file: ShalchemyFile, append: bool) -> FileResult:
        if isinstance(file, str):
            if file == '&1':
                return FileResult(fileno=subprocess.STDOUT, open_files=[])
            elif file == '&2':
                raise ValueError('Redirects to stderr (&2) is unsupported')
            mode = 'a' if append else 'w'
            osfile = open(file, mode)
            return FileResult(fileno=osfile.fileno(), open_files=[cast(io.IOBase, osfile)])

        try:
            fileno = file.fileno()
            if not append:
                try:
                    file.truncate(0)
                    file.seek(0)
                except io.UnsupportedOperation:
                    pass
            return FileResult(fileno, open_files=[])
        except io.UnsupportedOperation:
            pass

        tf: io.IOBase
        if isinstance(file, io.BytesIO):
            tf = cast(io.IOBase, TemporaryFile('w+b'))
            tf.write(file.read())
            tf.seek(0)
        else:
            tf = cast(io.IOBase, TemporaryFile('w+t'))
            tf.write(file.read())
            tf.seek(0)
        return FileResult(
            tf.fileno(),
            open_files=[tf],
            stream_pipes=[StreamPipe(source=tf, dest=file, append=append)],
        )

    def _run(
        self,
        stdin: Optional[ShalchemyOutputStream],
        stdout: Optional[ShalchemyOutputStream],
        stderr: Optional[ShalchemyOutputStream],
    ) -> RunResult:
        actual_stdout: Optional[ShalchemyOutputStream]
        actual_stderr: Optional[ShalchemyOutputStream]
        file_result: FileResult
        if self.redirect_stderr:
            file_result = self._make_os_file(self.rhs, self.append)
            actual_stdout = stdout
            actual_stderr = file_result.fileno
        else:
            file_result = self._make_os_file(self.rhs, self.append)
            actual_stdout = file_result.fileno
            actual_stderr = stderr

        context_lhs = self.lhs._run(
            stdin=stdin,
            stdout=actual_stdout,
            stderr=actual_stderr,
        )
        return RunResult(
            main=context_lhs.main,
            processes=context_lhs.processes,
            files=[*context_lhs.files, *file_result.open_files],
            directories=context_lhs.directories,
            stream_pipes=[*context_lhs.stream_pipes, *file_result.stream_pipes],
        )

    def _repr(self, paren: ParenthesisKind):
        if self.redirect_stderr and self.append:
            op = '2>>'
        elif self.redirect_stderr:
            op = '2>'
        elif self.append:
            op = '>>'
        else:
            op = '>'

        return f'{self.lhs._repr(ParenthesisKind.COMPOUND_ONLY)} {op} {represent_file(self.rhs)}'

    def __repr__(self):
        return f'$({self._repr(ParenthesisKind.NEVER)})'


class ProcessSubstituteExpression:
    pass


class ReadSubstitute(ProcessSubstituteExpression):
    __doc__ = textwrap.dedent(
        '''
            Process substitution is a technique to make the output of a command
            look like a file to the receiving process. One very common use of
            this is when using the diff command. Suppose you wanted to diff the
            file you have on disk with something on the internet. Normally, you
            would do:

            curl example.com/file.txt > tempfile.txt
            diff file.txt tempfile.txt
            rm tempfile.txt

            But actually you can do:

            diff file.txt <(curl example.com/file.txt)

            The <(command) syntax makes sh create a "file" in /dev/fd/xxxx. This
            is called Process Substitution.

            The way you do the same with shalchemy is:
            diff('file.txt', curl('example.com/file.txt').read_sub)

            Once an expression's `read_sub` method is called, the result is a
            ProcessSubstituteExpression which can no longer be composed with
            other expressions. It can only be used as an argument directly to
            other commands.
        '''
    ).strip()

    expression: ShalchemyExpression

    def __init__(self, expression: ShalchemyExpression):
        self.expression = expression

    def _prepare(
        self,
        stdin: Optional[ShalchemyOutputStream],
        stdout: Optional[ShalchemyOutputStream],
        stderr: Optional[ShalchemyOutputStream],
    ) -> ReadSubstitutePreparation:
        return ReadSubstitutePreparation(
            self.expression,
            stdin,
            stdout,
            stderr
        )

    def _repr(self, paren: ParenthesisKind = None):
        return f'<({self.expression._repr(ParenthesisKind.NEVER)})'

    def __repr__(self):
        return self._repr(paren=ParenthesisKind.ALWAYS)


class WriteSubstitute:
    __doc__ = textwrap.dedent(
        '''
            Process write substitution is a technique to make the output of a
            command look like a file to the receiving process. Write
            substitution is less commonly used than read substitution, but
            here's one (contrived) use-case:

            Suppose for some reason you want tee to write the output of a
            command to two different files. But one of them has to be uppercase
            for whatever reason and the other has to be lowercase. Also you
            want to see it in stdin. Normally what you would do is:

            some_command | tee upper.txt lower.txt
            tr [a-z] [A-Z] < upper.txt > actual_upper.txt
            mv actual_upper.txt upper.txt
            tr [A-A] [a-z] < lower.txt > actual_lower.txt
            mv actual_lower.txt lower.txt

            Very ugly. With write substitution you can do this instead:

            some_command | tee >(tr [a-z] [A-Z] > upper.txt) >(tr [A-Z] [a-z] > lower.txt)            

            The >(command) syntax makes sh create a "file" in /dev/fd/xxxx.
            This is called Process Substitution.

            The way you do the same with shalchemy is:
            sh('some_command') | tee(
                tr('[a-z]', '[A-Z]') > 'upper.txt').write_sub,
                tr('[A-Z]', '[a-z]') > 'lower.txt').write_sub,
            )

            Once an expression's `write_sub` method is called, the result is a
            ProcessSubstituteExpression which can no longer be composed with
            other expressions. It can only be used as an argument directly to
            other commands.3
        '''
    ).strip()
    expression: ShalchemyExpression

    def __init__(self, expression: ShalchemyExpression):
        self.expression = expression

    def _prepare(
        self,
        stdin: Optional[ShalchemyOutputStream],
        stdout: Optional[ShalchemyOutputStream],
        stderr: Optional[ShalchemyOutputStream],
    ) -> WriteSubstitutePreparation:
        return WriteSubstitutePreparation(
            self.expression,
            stdin,
            stdout,
            stderr
        )

    def _repr(self, paren: ParenthesisKind = None):
        return f'>({self.expression._repr(ParenthesisKind.NEVER)})'

    def __repr__(self, paren: ParenthesisKind = None):
        return self._repr(paren=ParenthesisKind.ALWAYS)
