from typing import Any, List, Dict, Callable, TYPE_CHECKING

import shlex

if TYPE_CHECKING:
    from .expressions import ShalchemyArgument


def default_convert(keyword: str, value: str) -> str:
    return f"--{keyword.replace('_', '-')}={shlex.quote(value)}"


def flatten(stuff: List[Any]):
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
    args: List['ShalchemyArgument'],
    kwargs: Dict[str, 'ShalchemyArgument'],
    _kwarg_convert: Callable[[str, 'ShalchemyArgument'], str] = default_convert
) -> List[Any]:
    result = []
    for arg in flatten(args):
        result.append(arg)
    for key, value in kwargs.items():
        result.append(_kwarg_convert(key, value))
    return result
