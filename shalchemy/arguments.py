import shlex


def default_convert(keyword: str, value: str) -> str:
    return f"--{keyword.replace('_', '-')}={shlex.quote(value)}"
