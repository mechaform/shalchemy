from typing import List, Optional

import io
import sys
import shlex
from .expressions import CommandExpression, ShalchemyExpression
from .arguments import compile_arguments, default_convert
from .run_result import RunResult


# This stuff is hacks for pytest
_DEFAULT_STDIN = sys.stdin
_DEFAULT_STDOUT = sys.stdout
_DEFAULT_STDERR = sys.stderr


def sh(*args, **kwargs):
    _kwarg_convert = kwargs.pop('_kwarg_convert',  default_convert)
    if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
        return CommandExpression(
            *shlex.split(args[0]),
            _kwarg_convert=_kwarg_convert,
        )

    compiled = compile_arguments(
        args,
        kwargs,
        _kwarg_convert=_kwarg_convert,
    )

    return CommandExpression(
        *compiled,
        _kwarg_convert=_kwarg_convert,
        **kwargs,
    )


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


def run(
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
