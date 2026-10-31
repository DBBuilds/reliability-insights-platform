"""scripts/publish-pages.sh against a throwaway remote: what lands on the gh-pages branch."""

import os
import subprocess
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "publish-pages.sh"


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def site(path: Path, script: str, stamp: int = 1) -> Path:
    (path / "assets").mkdir(parents=True)
    (path / "index.html").write_text(f"src={script}")
    (path / "assets" / script).write_text("js")
    for f in path.rglob("*"):
        os.utime(f, (stamp, stamp))
    return path


def published(repo: Path) -> dict[str, str]:
    git("fetch", "-q", "origin", "gh-pages", cwd=repo)
    names = git("ls-tree", "-r", "--name-only", "origin/gh-pages", cwd=repo).split()
    return {n: git("show", f"origin/gh-pages:{n}", cwd=repo) for n in names}


def test_publish_replaces_changed_files_keeps_previews_and_removes_them(tmp_path):
    git("init", "-q", "--bare", "origin.git", cwd=tmp_path)
    git("clone", "-q", "origin.git", "repo", cwd=tmp_path)
    repo = tmp_path / "repo"
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "init", cwd=repo)
    publish = lambda *args: subprocess.run([str(SCRIPT), *args], cwd=repo, check=True, capture_output=True)  # noqa: E731

    publish(".", str(site(tmp_path / "v1", "index-AAAA.js")))
    publish("pr-5", str(site(tmp_path / "p1", "index-PPPP.js")))
    # Same size as v1, and stamped with the second the script's checkout will get: a copy that compares
    # size and time (rsync's default) skips it and publishes a stale index.html.
    while time.time() % 1 > 0.05:
        time.sleep(0.01)
    publish(".", str(site(tmp_path / "v2", "index-BBBB.js", int(time.time()))))
    files = published(repo)
    assert files["index.html"] == "src=index-BBBB.js"
    assert "assets/index-AAAA.js" not in files and "assets/index-BBBB.js" in files  # stale asset gone
    assert files["pr-5/index.html"] == "src=index-PPPP.js"  # the preview survives a main publish
    assert ".nojekyll" in files

    publish("pr-5")
    assert not any(n.startswith("pr-5/") for n in published(repo))
    assert subprocess.run([str(SCRIPT), "."], cwd=repo, capture_output=True).returncode == 1  # never wipe the site
