import shutil as _shutil
from .expressions import ShellCommand as _ShellCommand


__all__ = []


def __getattr__(name) -> _ShellCommand:
    if name == '__path__':
        return None
    if _shutil.which(name) is None:
        raise ValueError(f'{name} not found in PATH')
    return _ShellCommand(name)
