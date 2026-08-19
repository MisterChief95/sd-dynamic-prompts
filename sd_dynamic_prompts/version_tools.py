# NB: this file may not import anything from `sd_dynamic_prompts` because it is used by `install.py`.

from __future__ import annotations

import dataclasses
import importlib.metadata
import logging
import shlex
import subprocess
import sys
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

try:
    import tomllib as tomli  # Python 3.11+
except ImportError:
    try:
        import tomli  # may have been installed already
    except ImportError:
        try:
            # pip has had this since version 21.2
            from pip._vendor import tomli
        except ImportError:
            raise ImportError(
                "A TOML library is required to install sd-dynamic-prompts, "
                "but could not be imported. "
                "Please install tomli (pip install tomli) and try again.",
            ) from None

try:
    from packaging.requirements import Requirement
except ImportError:
    # pip has had this since 2018
    from pip._vendor.packaging.requirements import (  # type: ignore[assignment]
        Requirement,
    )

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class InstallResult:
    requirement: Requirement
    installed: str | None

    @property
    def message(self) -> str | None:
        if self.correct:
            return None
        return (
            f"You have {self.requirement.name} version {self.installed or 'not'} installed, "
            f"but this extension requires version {self.requirement.specifier}. "
            f"Please run `install.py` from the sd-dynamic-prompts extension directory, "
            f"or `{self.pip_install_command}`."
        )

    @property
    def specifier_str(self) -> str:
        return str(self.requirement)

    @property
    def correct(self) -> bool:
        return bool(
            self.installed and self.requirement.specifier.contains(self.installed),
        )

    @property
    def pip_install_command(self) -> str:
        return f'pip install "{get_pip_requirement(self.requirement)}"'

    def raise_if_incorrect(self) -> None:
        message = self.message
        if message:
            raise RuntimeError(message)


@lru_cache(maxsize=1)
def get_requirements() -> tuple[str, ...]:
    toml_text = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    deps = tomli.loads(toml_text)["project"]["dependencies"]
    return tuple(str(dep) for dep in deps)


def get_install_result(req_str: str) -> InstallResult:
    req = Requirement(req_str)
    try:
        installed_version = importlib.metadata.version(req.name)
    except ImportError:
        installed_version = None
    res = InstallResult(requirement=req, installed=installed_version)
    return res


def get_requirements_install_results() -> Iterable[InstallResult]:
    """
    Get InstallResult objects for all requirements.
    """
    return (get_install_result(req_str) for req_str in get_requirements())


def get_dynamicprompts_install_result() -> InstallResult:
    """
    Get the InstallResult for the dynamicprompts requirement.
    """
    for req in get_requirements():
        if req.startswith("dynamicprompts"):
            return get_install_result(req)
    raise RuntimeError("dynamicprompts requirement not found")


# The forked dynamicprompts library is not published on PyPI. Wheels are
# published as GitHub release assets, tagged `v<version>`, by the fork's
# build_release_wheels workflow.
_DYNAMICPROMPTS_WHEEL_URL_TEMPLATE = (
    "https://github.com/MisterChief95/dynamicprompts/releases/download/"
    "v{version}/dynamicprompts-{version}-py3-none-any.whl"
)


def get_pinned_version(req: Requirement) -> str | None:
    """
    Get the exact version a requirement is pinned to with `==`, if any.
    """
    for spec in req.specifier:
        if spec.operator == "==":
            return spec.version
    return None


def get_pip_requirement(req: Requirement) -> str:
    """
    Render a requirement as a single `pip install` argument.

    dynamicprompts becomes a PEP 508 direct reference to the forked wheel,
    since the fork is not on PyPI. Everything else is rendered as-is.
    """
    if req.name.lower() != "dynamicprompts":
        return str(req)
    version = get_pinned_version(req)
    if not version:
        raise RuntimeError(
            f"The dynamicprompts requirement ({req}) must be pinned with `==` "
            f"so the forked wheel URL can be derived from it.",
        )
    extras = f"[{','.join(sorted(req.extras))}]" if req.extras else ""
    url = _DYNAMICPROMPTS_WHEEL_URL_TEMPLATE.format(version=version)
    return f"{req.name}{extras} @ {url}"


def _install_dynamicprompts(force: bool = False) -> bool:
    """
    Install the forked dynamicprompts library from its GitHub release wheel.

    Returns True if installation was attempted, False if skipped.
    """
    try:
        dp_result = get_dynamicprompts_install_result()
    except RuntimeError:
        logger.warning("dynamicprompts requirement not found; skipping install")
        return False

    if not force and dp_result.correct:
        return False

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        get_pip_requirement(dp_result.requirement),
    ]
    print("sd-dynamic-prompts installer: installing forked dynamicprompts")
    print(f"sd-dynamic-prompts installer: running {shlex.join(command)}")
    subprocess.check_call(command)
    return True


def install_requirements(force=False) -> None:
    """
    Invoke pip to install the requirements for the extension.

    The forked dynamicprompts library is installed from a GitHub release wheel
    (https://github.com/MisterChief95/dynamicprompts) rather than PyPI.
    All other requirements are installed from pyproject.toml as usual.
    """
    try:
        from launch import args

        if getattr(args, "skip_install", False):
            logger.info(
                "webui launch.args.skip_install is true, skipping dynamicprompts installation",
            )
            return
    except ImportError:
        pass

    # Install the forked dynamicprompts from its release wheel first.
    _install_dynamicprompts(force=force)

    # Install remaining (non-dynamicprompts) requirements from pyproject.toml.
    other_requirements = [
        get_pip_requirement(ires.requirement)
        for ires in get_requirements_install_results()
        if not ires.requirement.name.lower().startswith("dynamicprompts")
        and (force or not ires.correct)
    ]

    if not other_requirements:
        return

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        *other_requirements,
    ]
    print(f"sd-dynamic-prompts installer: running {shlex.join(command)}")
    subprocess.check_call(command)


def selftest() -> None:
    for res in get_requirements_install_results():
        print("[OK]" if res.correct else "????", res.requirement, res)


if __name__ == "__main__":
    selftest()
