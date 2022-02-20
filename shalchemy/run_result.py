from typing import TYPE_CHECKING, cast, List, Optional, Sequence

import io
import os
import subprocess
import shutil
import tempfile

if TYPE_CHECKING:
    from .expressions import ShalchemyExpression, ShalchemyOutputStream


class StreamPipe:
    source: io.IOBase
    dest: io.IOBase
    append: bool

    def __init__(self, source: io.IOBase, dest: io.IOBase, append: bool):
        self.source = source
        self.dest = dest
        self.append = append

    def pipe(self):
        if not self.append:
            try:
                self.dest.truncate(0)
                self.dest.seek(0)
            except io.UnsupportedOperation:
                pass
        self.source.seek(0)
        self.dest.write(self.source.read())


class FileResult:
    fileno: int
    open_files: List[io.IOBase]
    stream_pipes: List[StreamPipe]

    def __init__(
        self,
        fileno: int,
        open_files: Optional[List[io.IOBase]] = None,
        stream_pipes: Optional[List[StreamPipe]] = None,
    ):
        self.fileno = fileno
        self.open_files = open_files if open_files is not None else []
        self.stream_pipes = stream_pipes if stream_pipes is not None else []


class RunResult:
    main: subprocess.Popen
    file: 'ShalchemyOutputStream'
    processes: List[subprocess.Popen]
    files: Sequence['ShalchemyOutputStream']
    directories: List[str]
    stream_pipes: List[StreamPipe]

    def __init__(
        self,
        main: subprocess.Popen,
        processes: Optional[List[subprocess.Popen]] = None,
        files: Optional[List['ShalchemyOutputStream']] = None,
        directories: Optional[List[str]] = None,
        stream_pipes: List[StreamPipe] = None,
    ):
        if isinstance(main, subprocess.Popen):
            self.main = main
        else:
            self.file = main
        self.processes = processes or []
        self.files = files or []
        self.directories = directories or []
        self.stream_pipes = stream_pipes or []

    def wait(self):
        for process in self.processes:
            process.wait()
        for sm in self.stream_pipes:
            sm.pipe()
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
    writer: io.IOBase
    context: RunResult

    def __init__(
        self,
        expression: 'ShalchemyExpression',
        stdin: Optional['ShalchemyOutputStream'],
        stdout: Optional['ShalchemyOutputStream'],
        stderr: Optional['ShalchemyOutputStream'],
    ):
        # Create a temporary directory so we can get a file called /tmp/tmpXXXXXX/fifo
        self.tmpdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tmpdir, 'fifo')
        self.writer = cast(io.IOBase, open(self.filename, 'w'))
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
            directories=[*self.context.directories, self.tmpdir],
            stream_pipes=self.context.stream_pipes,
        )


class WriteSubstitutePreparation:
    expression: 'ShalchemyExpression'
    stdin: Optional['ShalchemyOutputStream']
    stdout: Optional['ShalchemyOutputStream']
    stderr: Optional['ShalchemyOutputStream']
    tmpdir: str
    filename: str

    def __init__(
        self,
        expression: 'ShalchemyExpression',
        stdin: Optional['ShalchemyOutputStream'],
        stdout: Optional['ShalchemyOutputStream'],
        stderr: Optional['ShalchemyOutputStream'],
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
        reader = cast(io.IOBase, open(self.filename, 'r'))
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
            stream_pipes=context.stream_pipes,
        )
