from typing import Callable, Sequence, Union, TYPE_CHECKING
import io
from enum import Enum


if TYPE_CHECKING:
    from .expressions import (
        ReadSubstitute,
        WriteSubstitute,
    )
    from .arguments import UncompiledArgument


PublicArgument = Union[
    str,
    int,
    float,
    'ReadSubstitute',
    'WriteSubstitute',
]

PublicKeywordArgument = Union[
    bool,
    str,
    int,
    float,
    'ReadSubstitute',
    'WriteSubstitute',
]

InternalArgument = Union[str, 'UncompiledArgument']

ShalchemyFile = Union[
    str,
    io.IOBase,
]

ShalchemyOutputStream = Union[
    io.IOBase,
    int,
]

KeywordArgumentRenderer = Callable[[str, PublicKeywordArgument], Sequence[str]]


class ParenthesisKind(Enum):
    NEVER = 1
    ALWAYS = 2
    COMPOUND_ONLY = 3
