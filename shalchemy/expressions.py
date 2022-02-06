from multiprocessing import context
from typing import Any, Dict, List, Optional, Union

from enum import Enum
import io
import os
import sys
import subprocess

from .arguments import compile_arguments


class ParenthesisKind(Enum):
    NEVER = 1
    ALWAYS = 2
    COMPOUND_ONLY = 3


ShalchemyExpression = Union[
    'ShellCommand',
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
    if isinstance(object, ShellCommand):
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
        return f'ImplicitFile({repr(file)})'
    else:
        return repr(file)


class RunResult:
    main: subprocess.Popen
    processes: List[subprocess.Popen]
    files: List[io.IOBase]

    def __init__(
        self,
        main: subprocess.Popen,
        processes: Optional[List[subprocess.Popen]] = None,
        files: Optional[List[io.IOBase]] = None,
    ):
        self.main = main
        self.processes = processes or []
        self.files = files or []

    def wait(self):
        for process in self.processes:
            process.wait()
        for file in self.files:
            file.close()


class ShalchemyBase:
    def read_sub(self) -> 'ReadSubstitute':
        return ReadSubstitute(self)

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

    def __bool__(self):
        result = self._run(
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        result.wait()
        return result.main.returncode == 0

    def __str__(self):
        read, write = os.pipe()
        with os.fdopen(write) as write_pipe:
            result = self._run(
                stdin=sys.stdin,
                stdout=write_pipe,
                stderr=sys.stderr,
            )
            result.wait()
        with os.fdopen(read) as read_pipe:
            return read_pipe.read().rstrip('\n')

    def __iter__(self):
        read, write = os.pipe()
        with os.fdopen(write) as write_pipe:
            result = self._run(
                stdin=sys.stdin,
                stdout=write_pipe,
                stderr=sys.stderr,
            )
            result.wait()
        with os.fdopen(read) as read_pipe:
            return read_pipe.read().rstrip('\n').split('\n').__iter__()

    def _run(
        self,
        stdin: io.IOBase,
        stdout: ShalchemyOutputStream,
        stderr: ShalchemyOutputStream,
    ) -> RunResult:
        raise NotImplementedError()

    def _repr(self, paren: ParenthesisKind) -> str:
        raise NotImplementedError()


class ShellCommand(ShalchemyBase):
    _args: List[Any]
    _kwargs: Dict[Any, Any]

    def __init__(self, *args: List[Any], **kwargs: Dict[Any, Any]):
        self._args = args
        self._kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return ShellCommand(*(*self._args, *args), **{**self._kwargs, **kwargs})

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
        compiled = compile_arguments(self._args, self._kwargs)
        process = subprocess.Popen(
            compiled,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        return RunResult(
            main=process,
            processes=[process],
            files=[],
        )

    def _repr(self, paren: ParenthesisKind):
        compiled = compile_arguments(self._args, self._kwargs)
        return str(compiled)

    def __repr__(self):
        return f'$({self._repr(ParenthesisKind.ALWAYS_PAREN)})'


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
        )

    def _repr(self, paren: ParenthesisKind):
        return f'{repr(self.lhs, ParenthesisKind.COMPOUND_ONLY)} < {represent_file(self.rhs)}'

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

        return f'{repr(self.lhs, ParenthesisKind.COMPOUND_ONLY)} {op} {represent_file(self.rhs)}'

    def __repr__(self):
        return f'$({self._repr(ParenthesisKind.NEVER)})'


class ReadSubstitute(ShalchemyBase):
    expression: ShalchemyExpression

    def __init__(self, expression: ShalchemyExpression):
        self.expression = expression

    def _run(self, context: RunResult):
        pass

    def _repr(self, paren: ParenthesisKind = None):
        return f'<({self.expression._repr(ParenthesisKind.NEVER)})'

    def __repr__(self):
        return self._repr(paren=ParenthesisKind.ALWAYS)


class WriteSubstitute(ShalchemyBase):
    expression: ShalchemyExpression

    def __init__(self, expression: ShalchemyExpression):
        self.expression = expression

    def _run(self, context: RunResult):
        pass

    def _repr(self, paren: ParenthesisKind = None):
        return f'>({self.expression._repr(ParenthesisKind.NEVER)})'

    def __repr__(self, paren: ParenthesisKind = None):
        return self._repr(paren=ParenthesisKind.ALWAYS)


sh = ShellCommand


def run(
    expression: ShalchemyExpression,
    stdin: io.IOBase = sys.stdin,
    stdout: io.IOBase = sys.stdout,
    stderr: io.IOBase = sys.stderr,
) -> int:
    result = expression._run(
        stdin=stdin,
        stdout=stdout,
        stderr=stderr
    )
    result.wait()
    return result.main.returncode
