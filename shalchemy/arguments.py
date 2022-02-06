from typing import Any, Dict, List


class ShalchemyArguments:
    _args: List[Any]
    _kwargs: Dict[Any, Any]

    def __init__(self, args: List[Any], kwargs: Dict[Any, Any]):
        self._args = args
        self._kwargs = kwargs

    def to_array(self):
        return self._args

    def __str__(self):
        return str(self._args) + ' ' + str(self._kwargs)


def compile_arguments(args: List[Any], kwargs: Dict[Any, Any]):
    return args
