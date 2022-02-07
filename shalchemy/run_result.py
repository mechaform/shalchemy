from typing import List, Optional

import io
import subprocess
import shutil


class RunResult:
    main: subprocess.Popen
    file: io.TextIOWrapper
    processes: List[subprocess.Popen]
    files: List[io.IOBase]
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
            file.close()
        for dir in self.directories:
            shutil.rmtree(dir)
