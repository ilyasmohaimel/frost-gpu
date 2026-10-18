#!/usr/bin/env python3
"""Prepare pinned upstream checkouts with local patches. No build or install."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kwin-cache", type=Path, help="Optional local Git source for offline checks")
    parser.add_argument("--zss-cache", type=Path, help="Optional local Git source for offline checks")
    args = parser.parse_args()
    target = args.output.absolute()
    if target.exists():
        parser.error("Output exists; choose a new directory to preserve its contents")
    target.mkdir(parents=True)
    upstreams = json.loads((ROOT / "patches/upstreams.json").read_text())
    for name, source in upstreams.items():
        cache = getattr(args, name + "_cache")
        repo = target / name
        if cache:
            run("git", "clone", "--shared", "--no-checkout", "--", str(cache.resolve()), str(repo))
        else:
            run("git", "clone", "--filter=blob:none", "--no-checkout", "--", source["url"], str(repo))
        run("git", "checkout", "--detach", source["revision"], cwd=repo)
        patch = ROOT / "patches" / source["patch"]
        run("git", "apply", "--check", str(patch), cwd=repo)
        run("git", "apply", str(patch), cwd=repo)
        print(name + ": pinned revision and patch prepared", flush=True)


if __name__ == "__main__":
    main()
