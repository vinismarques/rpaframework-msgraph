import os
import platform
import re
import shutil
import subprocess
import toml
from glob import glob
from pathlib import Path

from invoke import task, call, ParseError
from colorama import Fore, Style

from tasks_common import poetry


def _git_root():
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    output = output.decode().strip()
    return Path(output)


def _remove_blank_lines(text):
    return os.linesep.join([s for s in text.splitlines() if s])


GIT_ROOT = _git_root()
CONFIG = GIT_ROOT / "config"
TOOLS = GIT_ROOT / "tools"

if platform.system() != "Windows":
    ACTIVATE_PATH = GIT_ROOT / ".venv" / "bin" / "activate"
    ACTIVATE = f"source {ACTIVATE_PATH}"
else:
    ACTIVATE_PATH = GIT_ROOT / ".venv" / "Scripts" / "activate"
    ACTIVATE = f"{ACTIVATE_PATH}.bat"


CLEAN_PATTERNS = [
    ".cache",
    ".pytest_cache",
    ".venv",
    ".mypy_cache",
    "**/__pycache__",
    "**/*.pyc",
    "**/*.egg-info",
    "tests/output",
    "*.libspec",
    "*.pkl",
]

EXPECTED_POETRY_CONFIG = {
    "virtualenvs": {"in-project": True, "create": True, "path": "null"},
    "experimental": {"new-installer": True},
    "installer": {"parallel": True},
}


def _is_poetry_configured():
    try:
        poetry_toml = toml.load(GIT_ROOT / "poetry.toml")
        return all(
            [
                poetry_toml.get(key, None) == value
                for key, value in EXPECTED_POETRY_CONFIG.items()
            ]
        )
    except FileNotFoundError:
        return False


def _run(ctx, app, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    return ctx.run(f"{app} {command}", **kwargs)


def pip(ctx, command, **kwargs):
    return _run(ctx, "pip", command, **kwargs)


def sphinx(ctx, command, **kwargs):
    return poetry(ctx, f"run sphinx-build {command}", **kwargs)


def docgen(ctx, command, *flags, **kwargs):
    return poetry(ctx, f"run docgen {' '.join(flags)} {command}", **kwargs)


def python_tool(ctx, tool, *args, **kwargs):
    if tool[-3:] != ".py":
        tool_path = TOOLS / f"{tool}.py"
    else:
        tool_path = TOOLS / tool
    return poetry(ctx, f"run python {tool_path} {' '.join(args)}", **kwargs)


def package_invoke(ctx, directory, command, **kwargs):
    with ctx.cd(directory):
        return _run(ctx, "invoke", command, **kwargs)


def git(ctx, command, **kwargs):
    return _run(ctx, "git", command, **kwargs)


@task()
def clean(ctx, venv=True):
    """Cleans the virtual development environment by
    completely removing build artifacts and the .venv.
    You can set ``--no-venv`` to avoid this default.

    If ``--docs`` is supplied, the build artifacts for
    local documentation will also be cleaned.

    You can set flag ``all`` to clean all packages as
    well.
    """
    union_clean_patterns = []
    if venv:
        union_clean_patterns.extend(CLEAN_PATTERNS)
    for pattern in union_clean_patterns:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)
            try:
                os.remove(path)
            except OSError:
                pass


@task
def setup_poetry(ctx, username=None, password=None, token=None, devpi_url=None):
    """Configure local poetry installation for development.
    If you provide ``username`` and ``password``, you can
    also configure your pypi access. Our version of poetry
    uses ``keyring`` so the password is not stored in the
    clear.

    Alternatively, you can set ``token`` to use a pypi token, be sure
    to include the ``pypi-`` prefix in the token.

    NOTE: Robocorp developers can use ``https://devpi.robocorp.cloud/ci/test``
    as the devpi_url and obtain credentials from the Robocorp internal
    documentation.
    """
    poetry(ctx, "config -n --local virtualenvs.in-project true")
    poetry(ctx, "config -n --local virtualenvs.create true")
    poetry(ctx, "config -n --local virtualenvs.path null")
    poetry(ctx, "config -n --local experimental.new-installer true")
    poetry(ctx, "config -n --local installer.parallel true")
    if devpi_url:
        poetry(
            ctx,
            f"config -n --local repositories.devpi.url '{devpi_url}'",
        )
    if username and password and token:
        raise ParseError(
            "You cannot specify username-password combination and token simultaneously"
        )
    if username and password:
        poetry(ctx, f"config -n http-basic.pypi {username} {password}")
    elif username or password:
        raise ParseError("You must specify both username and password")
    if token:
        poetry(ctx, f"config -n pypi-token.pypi {token}")


@task
def install(ctx):
    """Install development environment. If ``reset`` is set,
    poetry will remove untracked packages, reverting the
    .venv to the lock file.

    If ``reset`` is attempted before an initial install, it
    is ignored.
    """
    if not _is_poetry_configured():
        call(setup_poetry)
    poetry(ctx, "install")


@task(install)
def test_python(ctx):
    """Run Python unit-tests."""
    poetry(ctx, "run pytest")


@task(install)
def test_robot(ctx):
    """Run Robot Framework tests."""
    exclude = "--exclude manual --exclude skip"
    poetry(
        ctx,
        f"run robot -d tests/output {exclude} -L TRACE tests/robot",
    )


@task(test_python, test_robot)
def test(_):
    """Run all tests."""


@task(install)
def lint(ctx):
    """Run format checks and static analysis."""
    poetry(ctx, "run black --check --diff src tests")
    poetry(ctx, f'run flake8 --config {CONFIG / "flake8"} src')
    poetry(ctx, f'run pylint -j1 --rcfile {CONFIG / "pylint"} src')


@task(install)
def pretty(ctx):
    """Run code formatter on source files."""
    poetry(ctx, "run black src")


@task(install)
def typecheck(ctx):
    """Run static type checks."""
    # TODO: Add --strict mode
    poetry(ctx, "run mypy src")


@task(lint, test)
def build(ctx):
    """Build distributable python package. (after linting, tests and libspec)"""
    poetry(ctx, "build -vv -f sdist")
    poetry(ctx, "build -vv -f wheel")


@task(clean, build, help={"ci": "Publish package to devpi instead of PyPI"})
def publish(ctx, ci=False):
    """Publish python package."""
    if ci:
        poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        poetry(ctx, "publish -v")
        ctx.run(f'{TOOLS / "tag.py"}')
