import hashlib
import os
from importlib.metadata import version
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import certifi
from botocore.httpsession import get_cert_path
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version
import pytest
import requests

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("region", ["AWS_REGION", "AWS_DEFAULT_REGION"])
def test_workflow_region_fallback(region):
    workflow = (ROOT / ".github/workflows/pytest.yml").read_text()
    assert f"      {region}: ${{{{ vars.{region} || 'us-west-2' }}}}" in workflow


def test_certifi_floor():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    floor = SpecifierSet(project["tool"]["poetry"]["dependencies"]["certifi"])
    assert "2026.10.18" not in floor
    assert "2026.10.19" in floor


def test_installed_certifi_and_selected_store():
    assert Version(version("certifi")) >= Version("2026.10.19")
    assert Path(requests.certs.where()).samefile(certifi.where())
    assert Path(get_cert_path(True)).samefile(certifi.where())


@pytest.mark.parametrize(
    "package, minimum",
    [("idna", "3.15"), ("urllib3", "2.8.0"), ("setuptools", "84.1.0")],
)
def test_installed_security_floor(package, minimum):
    assert Version(version(package)) >= Version(minimum)


def test_production_requirements_match_lock():
    lock = tomllib.loads((ROOT / "poetry.lock").read_text())
    expected = {
        package["name"]: (
            package["version"],
            {file["hash"] for file in package["files"]},
        )
        for package in lock["package"]
        if "main" in package["groups"]
    }
    exported = {}
    rows = (
        (ROOT / "sleuth/requirements.txt").read_text().replace("\\\n", "").splitlines()
    )
    for row in rows:
        if not row.strip() or row.startswith("#"):
            continue
        requirement = Requirement(row.split(" --hash=")[0].strip())
        assert str(requirement.marker) == 'python_version >= "3.10"'
        name = requirement.name.replace("_", "-").lower()
        assert name not in exported
        exported[name] = (
            str(requirement.specifier).removeprefix("=="),
            set(re.findall(r"--hash=(sha256:[0-9a-f]{64})", row)),
        )
    assert exported == expected


def test_example_runtime_matches_readme():
    for path in (ROOT / "examples/simple/main.tf", ROOT / "README.md"):
        assert (
            re.search(r'runtime\s*=\s*"(python[^"]+)"', path.read_text())[1]
            == "python3.13"
        )


@pytest.mark.parametrize("zip_name", ["deployment.zip", "custom.zip"])
def test_build_contains_dependencies_and_application(tmp_path, monkeypatch, zip_name):
    shutil.copytree(
        ROOT / "sleuth",
        tmp_path / "sleuth",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    requirements = tmp_path / "reqs"
    requirements.mkdir()
    shutil.copytree(Path(certifi.__file__).parent, requirements / "certifi")
    metadata = f"certifi-{version('certifi')}.dist-info"
    shutil.copytree(
        Path(certifi.__file__).parent.parent / metadata, requirements / metadata
    )
    commands = tmp_path / "bin"
    commands.mkdir()
    pip = commands / "pip"
    pip.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > pip-arguments.txt\n')
    pip.chmod(0o700)
    monkeypatch.setenv("PATH", f"{commands}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("ZIP_NAME", zip_name)
    subprocess.run(["bash", str(ROOT / "scripts/build")], cwd=tmp_path, check=True)
    arguments = (tmp_path / "pip-arguments.txt").read_text()
    assert "--require-hashes" in arguments
    assert "--no-deps" in arguments
    with zipfile.ZipFile(tmp_path / zip_name) as archive:
        for path in (
            "handler.py",
            "sleuth/services.py",
            "sleuth/auditor.py",
            "certifi/cacert.pem",
        ):
            assert path in archive.namelist()
        assert (
            f"Version: {version('certifi')}"
            in archive.read(f"{metadata}/METADATA").decode()
        )
    checksum, filename = (tmp_path / "checksums.txt").read_text().split()
    assert filename == zip_name
    assert checksum == hashlib.sha256((tmp_path / zip_name).read_bytes()).hexdigest()
