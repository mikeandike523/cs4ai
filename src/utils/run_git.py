from .subprocess_management import make_runner, RunResult

run_git_impl = make_runner('git')

def run_git(args, **kwargs) -> RunResult:
    return run_git_impl(args, **kwargs)