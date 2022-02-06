import shutil as _shutil
from .runner import sh as _sh
from .expressions import CommandExpression as _CommandExpression
from .arguments import default_convert as _default_convert

__all__ = []


def __getattr__(name) -> _CommandExpression:
    if name == '__path__':
        return None
    if _shutil.which(name) is None:
        raise ValueError(f'{name} not found in PATH')
    return _sh(name, _kwarg_convert=_default_convert)
