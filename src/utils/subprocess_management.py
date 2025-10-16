from dataclasses import dataclass
from subprocess import Popen, PIPE
from typing import Optional, List, Union, Callable
import os, shutil


@dataclass
class RunResult:
    stdout: str
    stderr: str
    exit_code: int

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def run_process(
    cmd: Union[str, List[str]],
    input: Optional[bytes] = None,
    text: bool = True,
    **popen_kwargs,
) -> RunResult:
    """
    Runs a subprocess command and captures stdout, stderr, and exit code.

    Args:
        cmd: Command to execute (string or list of args).
        input: Optional bytes to pass to stdin.
        text: If True, decode output as text (default True).
        **popen_kwargs: Forwarded to subprocess.Popen (e.g. cwd, env, shell, etc.)

    Returns:
        RunResult with stdout, stderr, exit_code, and .ok convenience property.
    """
    # Ensure pipes are set up
    popen_kwargs.setdefault("stdout", PIPE)
    popen_kwargs.setdefault("stderr", PIPE)
    if input is not None:
        popen_kwargs.setdefault("stdin", PIPE)

    with Popen(cmd, **popen_kwargs, text=text) as proc:
        stdout, stderr = proc.communicate(input=input)
        return RunResult(
            stdout=stdout or "",
            stderr=stderr or "",
            exit_code=proc.returncode,
        )


def make_runner(executable: str) -> Callable[..., RunResult]:
    """
    Returns a function that runs the given executable with the same API as run_process.
    If the executable is not an absolute path, uses shutil.which() to resolve it.
    Raises FileNotFoundError if not found.
    """

    # Resolve executable path
    if not os.path.isabs(executable):
        resolved = shutil.which(executable)
        if resolved is None:
            raise FileNotFoundError(f"Executable '{executable}' not found in PATH")
        executable = resolved

    def runner(args: Union[str, List[str]] = None, **kwargs) -> RunResult:
        """
        Runs the resolved executable with provided args.
        Args can be a string or list of args.
        """
        if args is None:
            cmd = [executable]
        elif isinstance(args, str):
            cmd = [executable, args]
        else:
            cmd = [executable] + list(args)
        return run_process(cmd, **kwargs)

    return runner
