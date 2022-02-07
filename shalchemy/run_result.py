from cmath import exp
from typing import TYPE_CHECKING, List, Optional, Union

import io
import os
import subprocess
import shutil
import tempfile
if TYPE_CHECKING:
    from .expressions import ShalchemyExpression, ShalchemyOutputStream


class RunResult:
    main: subprocess.Popen
    file: Union[io.TextIOWrapper, int]
    processes: List[subprocess.Popen]
    files: List[Union[io.IOBase, int]]
    directories: List[str]

    def __init__(
        self,
        main: subprocess.Popen,
        processes: Optional[List[subprocess.Popen]] = None,
        files: Optional[List[io.IOBase]] = None,
        directories: Optional[List[str]] = None,
    ):
        if isinstance(main, subprocess.Popen):
            self.main = main
        else:
            self.file = main
        self.processes = processes or []
        self.files = files or []
        self.directories = directories or []

    def wait(self):
        for process in self.processes:
            process.wait()
        self.cleanup()

    def cleanup(self):
        for file in self.files:
            if isinstance(file, io.IOBase):
                file.close()
            else:
                os.close(file)
        for dir in self.directories:
            shutil.rmtree(dir)


class ReadSubstitutePreparation:
    tmpdir: str
    filename: str
    writer: int
    context: RunResult

    def __init__(
        self,
        expression: 'ShalchemyExpression',
        stdin: io.IOBase,
        stdout: 'ShalchemyOutputStream',
        stderr: 'ShalchemyOutputStream',
    ):
        # Create a temporary directory so we can get a file called /tmp/tmpXXXXXX/fifo
        self.tmpdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tmpdir, 'fifo')
        self.writer = open(self.filename, 'w')
        self.context = expression._run(
            stdin=stdin,
            stdout=self.writer,
            stderr=stderr,
        )

    def _run(self):
        return RunResult(
            main=self.context.main,
            processes=self.context.processes,
            files=[*self.context.files, self.writer],
            directories=[*self.context.directories, self.tmpdir]
        )


class WriteSubstitutePreparation:
    expression: 'ShalchemyExpression'
    stdin: io.IOBase
    stdout: 'ShalchemyOutputStream'
    stderr: 'ShalchemyOutputStream'
    tmpdir: str
    filename: str

    def __init__(
        self,
        expression: 'ShalchemyExpression',
        stdin: io.IOBase,
        stdout: 'ShalchemyOutputStream',
        stderr: 'ShalchemyOutputStream',
    ):
        self.expression = expression
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        # Create a temporary directory so we can get a file called /tmp/tmpXXXXXX/fifo
        self.tmpdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tmpdir, 'fifo')
        os.mkfifo(self.filename, 0o600)

    def _run(self) -> RunResult:
        reader = os.open(self.filename, os.O_NONBLOCK + os.O_RDONLY)
        opened_directories = [self.tmpdir]
        opened_files = [reader]
        context = self.expression._run(
            stdin=reader,
            stdout=self.stdout,
            stderr=self.stderr,
        )
        return RunResult(
            main=context.main,
            processes=context.processes,
            files=[*context.files, *opened_files],
            directories=[*context.directories, *opened_directories],
        )
