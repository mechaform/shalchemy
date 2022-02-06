from typing import List, Optional

import io
import subprocess


class RunResult:
    main: subprocess.Popen
    processes: List[subprocess.Popen]
    files: List[io.IOBase]

    def __init__(
        self,
        main: subprocess.Popen,
        processes: Optional[List[subprocess.Popen]] = None,
        files: Optional[List[io.IOBase]] = None,
    ):
        self.main = main
        self.processes = processes or []
        self.files = files or []

    def wait(self):
        for process in self.processes:
            process.wait()
        self.cleanup()

    def cleanup(self):
        for file in self.files:
            file.close()
