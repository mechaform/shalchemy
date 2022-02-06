import shutil as _shutil
from .expressions import CommandExpression as _CommandExpression


__all__ = []


def __getattr__(name) -> _CommandExpression:
    if name == '__path__':
        return None
    if _shutil.which(name) is None:
        raise ValueError(f'{name} not found in PATH')
    return _CommandExpression(name)
