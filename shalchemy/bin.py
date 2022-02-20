from typing import cast, List
import shutil as _shutil
from .runner import sh as _sh
from .expressions import CommandExpression as _CommandExpression
from .arguments import default_kwarg_render as _default_kwarg_render

__all__: List[str] = []


def __getattr__(name) -> _CommandExpression:
    if name == '__path__':
        return cast(_CommandExpression, None)
    if _shutil.which(name) is None:
        raise ValueError(f'{name} not found in PATH')
    return _sh(name, _kwarg_render=_default_kwarg_render)
