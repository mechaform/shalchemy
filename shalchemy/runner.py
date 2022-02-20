from typing import cast, Optional

import io
import sys
import shlex
from .expressions import CommandExpression, ShalchemyExpression, ShalchemyFile
from .arguments import compile_arguments, default_kwarg_render
from .run_result import RunResult


# This stuff is hacks for pytest
_DEFAULT_STDIN: io.IOBase = cast(io.IOBase, sys.stdin)
_DEFAULT_STDOUT: io.IOBase = cast(io.IOBase, sys.stdout)
_DEFAULT_STDERR: io.IOBase = cast(io.IOBase, sys.stderr)


class CommandCreator:
    def __call__(self, *args, **kwargs) -> CommandExpression:
        _kwarg_render = kwargs.pop('_kwarg_render',  default_kwarg_render)
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
            return CommandExpression(
                *shlex.split(args[0]),
                _kwarg_render=_kwarg_render,
            )

        compiled = compile_arguments(
            args,
            kwargs,
            _kwarg_render=_kwarg_render,
        )

        return CommandExpression(
            *compiled,
            _kwarg_render=_kwarg_render,
        )

    def run(
        self,
        expression: 'ShalchemyExpression',
        stdin: Optional[io.IOBase] = None,
        stdout: Optional[io.IOBase] = None,
        stderr: Optional[io.IOBase] = None,
    ) -> int:
        result = _internal_run(
            expression,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr
        )
        result.wait()
        return result.main.returncode


class ShellFile:
    def __init__(self, source: ShalchemyFile):
        pass


def _internal_run(
    expression: 'ShalchemyExpression',
    stdin: Optional[io.IOBase] = None,
    stdout: Optional[io.IOBase] = None,
    stderr: Optional[io.IOBase] = None,
) -> RunResult:
    actual_stdin = stdin if stdin is not None else _DEFAULT_STDIN
    actual_stdout = stdout if stdout is not None else _DEFAULT_STDOUT
    actual_stderr = stderr if stderr is not None else _DEFAULT_STDERR
    result = expression._run(
        stdin=actual_stdin,
        stdout=actual_stdout,
        stderr=actual_stderr,
    )
    return result

sh = CommandCreator()
run = sh.run
