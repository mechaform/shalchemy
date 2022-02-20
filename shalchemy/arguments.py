from dataclasses import dataclass
import io
from typing import Any, cast, List, Dict, Sequence, Union, TYPE_CHECKING
from .types import ParenthesisKind, PublicArgument, PublicKeywordArgument
from .run_result import ReadSubstitutePreparation, WriteSubstitutePreparation
import sys

if TYPE_CHECKING:
    from .expressions import ReadSubstitute, WriteSubstitute


from shalchemy.types import (
    InternalArgument,
    KeywordArgumentRenderer,
)


def default_kwarg_render(keyword: str, value: PublicKeywordArgument) -> Sequence[str]:
    if value is True:
        return [f"--{keyword.replace('_', '-')}"]
    elif value is None or value is False:
        return []
    return [f"--{keyword.replace('_', '-')}={value}"]


def flatten(stuff: Sequence[Any]):
    if not isinstance(stuff, (list, tuple)):
        return stuff
    flattened = []
    for x in stuff:
        if isinstance(x, (list, tuple)):
            flattened.extend(flatten(x))
        else:
            flattened.append(x)
    return flattened


def compile_arguments(
    args: Sequence['PublicArgument'],
    kwargs: Dict[str, PublicKeywordArgument],
    _kwarg_render: KeywordArgumentRenderer = default_kwarg_render
) -> List[InternalArgument]:
    from .expressions import ReadSubstitute, WriteSubstitute
    result: List[InternalArgument] = []
    for arg in flatten(args):
        result.append(arg)
    for key, value in kwargs.items():
        if isinstance(value, (str, int, float, bool)):
            result.extend(_kwarg_render(key, value))
        elif isinstance(value, (ReadSubstitute, WriteSubstitute)):
            result.append(UncompiledArgument(key, value, _kwarg_render))
        else:
            raise TypeError(
                'Keyword arguments must be one of [str, int, float, bool, ReadSubstitute, WriteSubstitute]',
                value
            )
    return result


@dataclass
class ArgumentCompilationResult:
    args: Sequence[str]
    prepared_args: List[Union[WriteSubstitutePreparation, ReadSubstitutePreparation]]


UncompiledKeywordArgument = Union[
    'ReadSubstitute',
    'WriteSubstitute',
]

class UncompiledArgument:
    key: str
    value: UncompiledKeywordArgument
    render: KeywordArgumentRenderer

    def __init__(self, key: str, value: UncompiledKeywordArgument, render: KeywordArgumentRenderer):
        self.key = key
        self.value = value
        setattr(self, 'render', render)

    def compile(self, filename: str) -> Sequence[str]:
        # Avoid mypy typing self.render as a bound method
        render: KeywordArgumentRenderer = getattr(self, 'render')
        return render(self.key, filename)

    def _repr(self, paren: ParenthesisKind = None):
        render: KeywordArgumentRenderer = getattr(self, 'render')
        fname = f'{self.value._repr(ParenthesisKind.ALWAYS)}'
        return render(self.key, fname)

    def __repr__(self):
        return self._repr
