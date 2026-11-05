"""scripts/publish.sh against a fake `aws` that records calls and simulates the bucket."""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "publish.sh"

FAKE_AWS = r"""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state = Path(os.environ["FAKE_STATE"])
args = sys.argv[1:]
with open(state / "calls.log", "a") as f:
    f.write(json.dumps(args) + "\n")
bucket = state / "bucket"
if os.environ.get("FAKE_FAIL") and any(a in os.environ["FAKE_FAIL"].split(",") for a in args):
    print("An error occurred (InternalError) when calling the operation", file=sys.stderr); sys.exit(1)
cmd = [a for a in args if not a.startswith("--") and not a.startswith("https://")]
if "--only-show-errors" in args and cmd[:2] == ["s3", "ls"]:
    print("Unknown options: --only-show-errors", file=sys.stderr); sys.exit(252)
def key(url): return url.split("/", 3)[3] if url.count("/") >= 3 else ""
if cmd[:2] == ["s3", "ls"]:
    prefix = key(cmd[2])
    for p in sorted(bucket.rglob("*")):
        if p.is_file() and str(p.relative_to(bucket)).startswith(prefix):
            print("2026-11-05 10:00:00 1 " + str(p.relative_to(bucket)))
elif cmd[:2] == ["s3", "cp"]:
    src, dst = cmd[2], cmd[3]
    if src.startswith("s3://"):
        p = bucket / key(src)
        if not p.exists():
            print("An error occurred (404) when calling the HeadObject operation: Key not found", file=sys.stderr); sys.exit(1)
        Path(dst).write_bytes(p.read_bytes())
    else:
        p = bucket / key(dst); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(Path(src).read_bytes())
elif cmd[:2] == ["s3", "rm"]:
    import shutil; shutil.rmtree(bucket / key(cmd[2]), ignore_errors=True)
"""


@pytest.fixture
def env(tmp_path):
    bindir = tmp_path / "bin"; bindir.mkdir()
    aws = bindir / "aws"; aws.write_text(FAKE_AWS); aws.chmod(aws.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "state" / "bucket").mkdir(parents=True)
    return {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "FAKE_STATE": str(tmp_path / "state"),
            "R2_ACCOUNT_ID": "acc", "R2_ACCESS_KEY_ID": "k", "R2_SECRET_ACCESS_KEY": "s"}


def run(env, *args):
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True)


def pack(tmp_path, names):
    d = tmp_path / "pack"; d.mkdir(exist_ok=True)
    for n in names:
        (d / n).write_text(n)
    return d


def test_pack_without_zones_succeeds(tmp_path, env):
    d = pack(tmp_path, ["valhalla_tiles.tar", "lanes.json", "landmarks.json", "basemap.mbtiles", "search.sqlite"])
    r = run(env, "pack", str(d), "packs/greece/2026-12-01/")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "state/bucket/packs/greece/2026-12-01/search.sqlite").exists()


def test_pack_refuses_to_overwrite_a_published_version(tmp_path, env):
    d = pack(tmp_path, ["lanes.json"])
    assert run(env, "pack", str(d), "packs/cyprus/v1/").returncode == 0
    r = run(env, "pack", str(d), "packs/cyprus/v1/")
    assert r.returncode != 0 and "already" in r.stderr


def test_list_reports_versions(tmp_path, env):
    d = pack(tmp_path, ["lanes.json"])
    run(env, "pack", str(d), "packs/cyprus/v1/")
    run(env, "pack", str(d), "packs/cyprus/v2/")
    r = run(env, "list")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"cyprus": ["v1", "v2"]}


def test_get_manifest_absent_is_not_an_error(tmp_path, env):
    r = run(env, "get-manifest", str(tmp_path / "old.json"))
    assert r.returncode == 0 and not (tmp_path / "old.json").exists()


def test_get_manifest_other_error_fails(tmp_path, env):
    r = run({**env, "FAKE_FAIL": "s3://mynav-maps/manifest.json"}, "get-manifest", str(tmp_path / "old.json"))
    assert r.returncode != 0
