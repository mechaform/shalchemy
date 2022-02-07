from typing import Any, Callable, List, Union

from enum import Enum
import io
import os
import sys
import shlex
import tempfile
import textwrap
import subprocess

from .arguments import compile_arguments
from .run_result import RunResult, ReadSubstitutePreparation, WriteSubstitutePreparation


class ParenthesisKind(Enum):
    NEVER = 1
    ALWAYS = 2
    COMPOUND_ONLY = 3


ShalchemyArgument = Union[
    str,
    'ShalchemyExpression',
    'ReadSubstitute',
    'WriteSubstitute',
]

ShalchemyExpression = Union[
    'CommandExpression',
    'PipeExpression',
    'RedirectInExpression',
    'RedirectOutExpression',
]

ShalchemyFile = Union[
    str,
    io.IOBase,
]

ShalchemyOutputStream = Union[
    io.IOBase,
    int,
]


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
    if isinstance(file, io.TextIOWrapper):
        return f'File({repr(file.name)})'
    elif isinstance(file, str):
        return shlex.quote(file)
    else:
        return repr(file)


class ShalchemyBase:
    @property
    def read_sub(self) -> 'ReadSubstitute':
        return ReadSubstitute(self)

    @property
    def write_sub(self) -> 'WriteSubstitute':
        return WriteSubstitute(self)

    def stderr(self, destination: ShalchemyFile, append=False):
        return RedirectOutExpression(
            self,
            destination,
            append=append,
            stderr=True,
        )

    def __or__(self, rhs):
        return PipeExpression(self, rhs)

    def __lt__(self, rhs):
        return RedirectInExpression(self, rhs)

    def __gt__(self, rhs):
        return RedirectOutExpression(self, rhs)

    def in_(self, rhs):
        return RedirectInExpression(self, rhs)

    def out(self, rhs):
        return RedirectOutExpression(self, rhs)

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
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
    ) -> RunResult:
        raise NotImplementedError()

    def _repr(self, paren: ParenthesisKind) -> str:
        raise NotImplementedError()


class CommandExpression(ShalchemyBase):
    _args: List[ShalchemyArgument]
    _kwarg_convert: Callable[[str, ShalchemyArgument], str]

    def __init__(
        self,
        *args: List[ShalchemyArgument],
        **kwargs: Any,
    ):
        self._args = args
        self._kwarg_convert = kwargs.pop('_kwarg_convert')

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
            return CommandExpression(
                *self._args,
                *shlex.split(args[0]),
                _kwarg_convert=self._kwarg_convert,
            )

        compiled = compile_arguments(
            args,
            kwargs,
            _kwarg_convert=self._kwarg_convert,
        )

        return CommandExpression(
            *self._args,
            *compiled,
            _kwarg_convert=self._kwarg_convert,
        )

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        return self.__call__(attr)

    def _run(
        self,
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
    ) -> RunResult:
        opened_processes = []
        opened_files = []
        opened_directories = []
        prepared_args = []
        arguments = []

        for arg in self._args:
            if isinstance(arg, (ReadSubstitute, WriteSubstitute)):
                preparation = arg._prepare(
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                )
                prepared_args.append(preparation)
                arguments.append(preparation.filename)
            else:
                arguments.append(arg)

        process = subprocess.Popen(
            arguments,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )

        for preparation in prepared_args:
            context = preparation._run()
            opened_processes.extend(context.processes)
            opened_files.extend(context.files)
            opened_directories.extend(context.directories)

        return RunResult(
            main=process,
            processes=[*opened_processes, process],
            files=opened_files,
            directories=opened_directories,
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


class PipeExpression(ShalchemyBase):
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
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
    ) -> RunResult:
        context_lhs = self.lhs._run(
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=stderr,
        )
        context_rhs = self.rhs._run(
            stdin=context_lhs.main.stdout,
            stdout=stdout,
            stderr=stderr,
        )
        return RunResult(
            main=context_rhs.main,
            processes=[*context_lhs.processes, *context_rhs.processes],
            files=[*context_lhs.files, *context_rhs.files],
            directories=[*context_lhs.directories, *context_rhs.directories],
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


class RedirectInExpression(ShalchemyBase):
    lhs: ShalchemyExpression
    rhs: ShalchemyFile

    def __init__(self, lhs: ShalchemyExpression, rhs: ShalchemyFile):
        self.lhs = lhs
        self.rhs = rhs

    def _run(
        self,
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
    ) -> RunResult:
        opened_files = []
        if isinstance(self.rhs, io.IOBase):
            actual_stdin = self.rhs
        else:
            actual_stdin = open(self.rhs, 'r')
            opened_files.append(actual_stdin)

        context_lhs = self.lhs._run(
            stdin=actual_stdin,
            stdout=stdout,
            stderr=stderr,
        )
        return RunResult(
            main=context_lhs.main,
            processes=context_lhs.processes,
            files=[*context_lhs.files, *opened_files],
            directories=context_lhs.directories,
        )

    def _repr(self, paren: ParenthesisKind):
        return f'{self.lhs._repr(ParenthesisKind.COMPOUND_ONLY)} < {represent_file(self.rhs)}'

    def __repr__(self):
        return f'$({self._repr(ParenthesisKind.NEVER)})'


class RedirectOutExpression(ShalchemyBase):
    lhs: ShalchemyExpression
    rhs: ShalchemyFile
    stderr: bool
    append: bool
    _parents: List[ShalchemyExpression]
    _process: subprocess.Popen
    _file: io.TextIOWrapper

    def __init__(self, lhs, rhs, append: bool = False, stderr=False):
        self.lhs = lhs
        self.rhs = rhs
        self.append = append
        self.stderr = stderr
        self._parents = []

    def _run(
        self,
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
    ) -> RunResult:
        opened_files = []
        if self.stderr:
            actual_stdout = stdout
            if isinstance(self.rhs, io.IOBase):
                actual_stderr = self.rhs
            elif self.append:
                actual_stderr = open(self.rhs, 'a')
                opened_files.append(actual_stderr)
            else:
                actual_stderr = open(self.rhs, 'w')
                opened_files.append(actual_stderr)
        else:
            actual_stderr = stderr
            if isinstance(self.rhs, io.IOBase):
                actual_stdout = self.rhs
            elif self.append:
                actual_stdout = open(self.rhs, 'a')
                opened_files.append(actual_stdout)
            else:
                actual_stdout = open(self.rhs, 'w')
                opened_files.append(actual_stdout)

        context_lhs = self.lhs._run(
            stdin=stdin,
            stdout=actual_stdout,
            stderr=actual_stderr,
        )
        return RunResult(
            main=context_lhs.main,
            processes=context_lhs.processes,
            files=[*context_lhs.files, *opened_files],
            directories=context_lhs.directories,
        )

    def _repr(self, paren: ParenthesisKind):
        if self.stderr and self.append:
            op = '2>>'
        elif self.stderr:
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
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
    ) -> RunResult:
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
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
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
