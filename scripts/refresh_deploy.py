#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PUBLIC_DOMAIN = "arcade.adrianlumley.co"
PUBLIC_URL = f"https://{PUBLIC_DOMAIN}/"
GENERATED_EXCLUDES = {
    "dist",
    "data/latest.json",
    "data/runs",
    "data/summon.json",
    "__pycache__",
}
REQUIRED_DIST_FILES = {
    "index.html",
    "CNAME",
    "app/index.html",
    "app/app.js",
    "app/style.css",
    "data/latest.json",
    "data/summon.json",
}
FORBIDDEN_DIST_PARTS = {".git", "__pycache__", "data/runs"}
FORBIDDEN_TEXT_SNIPPETS = (
    str(ROOT),
    str(Path.home()),
    '"stdout"',
    '"stderr"',
    '"raw"',
    '"status_lines"',
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh Agent Arcade state and publish the sanitized static site.",
    )
    parser.add_argument(
        "personas",
        nargs="*",
        help="Optional summon personas. Defaults to all personas when omitted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full local refresh/build/validation flow without committing or pushing.",
    )
    parser.add_argument(
        "--skip-main-push",
        action="store_true",
        help="Do not commit or push changes on the main branch.",
    )
    parser.add_argument(
        "--skip-gh-pages",
        action="store_true",
        help="Do not publish the dist/ build to the gh-pages branch.",
    )
    return parser.parse_args(argv[1:])


def log(message: str) -> None:
    print(f"[refresh] {message}")


def run(args: list[str], *, cwd: Path = ROOT, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    log(" ".join(args))
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if result.returncode != 0:
        if capture_output:
            if result.stdout:
                sys.stdout.write(result.stdout)
            if result.stderr:
                sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    if capture_output and result.stdout:
        sys.stdout.write(result.stdout)
    return result


def ensure_main_branch() -> None:
    branch = run(["git", "branch", "--show-current"], capture_output=True).stdout.strip()
    if branch != "main":
        raise SystemExit(f"refresh_deploy must run from the main branch; current branch is {branch or 'detached'}")


def refresh_local_state(personas: list[str]) -> None:
    python = sys.executable or "python3"
    run([python, "scripts/collect_state.py"])
    run([python, "scripts/summon.py", *(personas or ["all"])])
    run([python, "scripts/build_dist.py"])


def ensure_cname() -> None:
    DIST.mkdir(exist_ok=True)
    cname_path = DIST / "CNAME"
    cname_path.write_text(f"{PUBLIC_DOMAIN}\n", encoding="utf-8")
    log(f"Ensured {cname_path.relative_to(ROOT)} -> {PUBLIC_DOMAIN}")


def iter_dist_files() -> list[Path]:
    return sorted(path for path in DIST.rglob("*") if path.is_file())


def find_json_keys(value: object, blocked: set[str], *, prefix: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key in blocked:
                matches.append(next_prefix)
            matches.extend(find_json_keys(item, blocked, prefix=next_prefix))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            matches.extend(find_json_keys(item, blocked, prefix=f"{prefix}[{index}]"))
    return matches


def validate_dist() -> None:
    if not DIST.exists():
        raise SystemExit("dist/ is missing; build step did not complete")

    files = iter_dist_files()
    relpaths = {path.relative_to(DIST).as_posix() for path in files}
    missing = sorted(REQUIRED_DIST_FILES - relpaths)
    if missing:
        raise SystemExit(f"dist leak check failed; missing files: {', '.join(missing)}")

    cname_value = (DIST / "CNAME").read_text(encoding="utf-8").strip()
    if cname_value != PUBLIC_DOMAIN:
        raise SystemExit(f"dist leak check failed; CNAME must be {PUBLIC_DOMAIN}, found {cname_value!r}")

    bad_paths = [
        path.relative_to(DIST).as_posix()
        for path in DIST.rglob("*")
        if any(part in FORBIDDEN_DIST_PARTS for part in path.parts)
    ]
    if bad_paths:
        raise SystemExit(f"dist leak check failed; forbidden paths present: {', '.join(sorted(bad_paths))}")

    latest_payload = json.loads((DIST / "data" / "latest.json").read_text(encoding="utf-8"))
    latest_matches = find_json_keys(latest_payload, {"stdout", "stderr", "raw", "status_lines", "command"})
    if latest_matches:
        raise SystemExit(f"dist leak check failed; blocked keys in dist/data/latest.json: {', '.join(latest_matches)}")

    summon_payload = json.loads((DIST / "data" / "summon.json").read_text(encoding="utf-8"))
    summon_matches = find_json_keys(summon_payload, {"stdout", "stderr", "raw", "status_lines", "command"})
    if summon_matches:
        raise SystemExit(f"dist leak check failed; blocked keys in dist/data/summon.json: {', '.join(summon_matches)}")

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for snippet in FORBIDDEN_TEXT_SNIPPETS:
            if snippet and snippet in text:
                relpath = path.relative_to(DIST).as_posix()
                raise SystemExit(f"dist leak check failed; found forbidden text in {relpath}: {snippet}")

    log("dist leak check passed")


def tracked_status_lines() -> list[str]:
    result = run(["git", "status", "--short"], capture_output=True).stdout
    return [line for line in result.splitlines() if line.strip()]


def path_is_generated(path_text: str) -> bool:
    candidate = path_text.strip()
    return any(
        candidate == excluded
        or candidate.startswith(f"{excluded}/")
        or candidate.endswith(f"/{excluded}")
        for excluded in GENERATED_EXCLUDES
    )


def main_worktree_has_changes() -> bool:
    for line in tracked_status_lines():
        candidate = line[3:]
        if " -> " in candidate:
            old_path, new_path = candidate.split(" -> ", 1)
            if not path_is_generated(old_path) or not path_is_generated(new_path):
                return True
            continue
        if not path_is_generated(candidate):
            return True
    return False


def commit_and_push_main(*, dry_run: bool) -> None:
    if not main_worktree_has_changes():
        log("No main-branch changes to commit")
        return

    if dry_run:
        log("Dry run: main branch has changes and would be committed/pushed")
        return

    run(["git", "add", "-A", "."])
    for excluded in ("dist", "data/latest.json", "data/runs", "data/summon.json", "__pycache__"):
        run(["git", "reset", "HEAD", "--", excluded], capture_output=True)

    if not main_worktree_has_changes():
        log("Only generated artifacts changed on main; nothing to commit")
        return

    message = f"Refresh Agent Arcade deploy flow ({datetime.now().astimezone().date().isoformat()})"
    run(["git", "commit", "-m", message])
    run(["git", "push", "origin", "main"])


def reset_worktree_contents(path: Path) -> None:
    for child in path.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_dist_to(path: Path) -> None:
    for child in DIST.iterdir():
        target = path / child.name
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def gh_pages_has_changes(path: Path) -> bool:
    status = run(["git", "status", "--short"], cwd=path, capture_output=True).stdout
    return any(line.strip() for line in status.splitlines())


def publish_gh_pages(*, dry_run: bool) -> None:
    if dry_run:
        log("Dry run: gh-pages publish skipped after local build and validation")
        return

    with tempfile.TemporaryDirectory(prefix="agent-arcade-gh-pages-") as temp_dir:
        worktree = Path(temp_dir) / "site"
        run(["git", "worktree", "add", "--force", "-B", "gh-pages", str(worktree), "HEAD"])
        try:
            reset_worktree_contents(worktree)
            copy_dist_to(worktree)
            run(["git", "add", "--all"], cwd=worktree)

            if not gh_pages_has_changes(worktree):
                log("gh-pages is already up to date")
                return

            if dry_run:
                log("Dry run: gh-pages branch has updates and would be committed/pushed")
                return

            stamp = datetime.now().astimezone().isoformat(timespec="seconds")
            run(["git", "commit", "-m", f"Publish Agent Arcade {stamp}"], cwd=worktree)
            run(["git", "push", "--force", "origin", "gh-pages"], cwd=worktree)
        finally:
            run(["git", "worktree", "remove", "--force", str(worktree)])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ensure_main_branch()
    refresh_local_state(args.personas)
    ensure_cname()
    validate_dist()

    if not args.skip_main_push:
        commit_and_push_main(dry_run=args.dry_run)
    else:
        log("Skipping main branch push")

    if not args.skip_gh_pages:
        publish_gh_pages(dry_run=args.dry_run)
    else:
        log("Skipping gh-pages publish")

    print(PUBLIC_URL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
