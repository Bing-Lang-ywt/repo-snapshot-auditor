import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def snapshot(repo, ref, output):
    repo = Path(repo).resolve()
    output = Path(output).resolve()
    root = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if repo != root:
        raise ValueError("Use the repository root, not a subdirectory")
    if output == root or root in output.parents:
        raise ValueError("Output must be outside the source repository")
    sha = git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()
    entries = git(repo, "ls-tree", "-r", "-z", sha).split(b"\0")
    files, submodules, symlinks = [], [], []
    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, object_sha = metadata.decode().split()
        path = raw_path.decode("utf-8", errors="surrogateescape")
        record = {"path": path, "mode": mode, "object_sha": object_sha}
        if kind == "commit":
            submodules.append(record)
        else:
            files.append(path)
            if mode == "120000":
                symlinks.append(record)
    dirty = bool(git(repo, "status", "--porcelain", "--untracked-files=normal"))
    basenames = {PurePosixPath(p).name.lower() for p in files}
    checks = {
        "readme_present": any(n.startswith("readme") for n in basenames),
        "license_present": any(n.startswith(("license", "copying")) for n in basenames),
        "test_files_present": any(
            "tests" in PurePosixPath(p).parts or PurePosixPath(p).name.startswith("test_")
            for p in files
        ),
        "github_actions_present": any(p.startswith(".github/workflows/") for p in files),
    }
    extensions = {}
    for p in files:
        extension = PurePosixPath(p).suffix or "[no extension]"
        extensions[extension] = extensions.get(extension, 0) + 1
    # Reserve a new directory so existing evidence can never be overwritten.
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "source.tar"
    with archive.open("wb") as stream:
        subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", sha],
                       stdout=stream, stderr=subprocess.PIPE, check=True)
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    report = {
        "schema_version": 1,
        "commit": sha,
        "commit_date": git(repo, "show", "-s", "--format=%cI", sha).decode().strip(),
        "archive_sha256": digest.hexdigest(),
        "working_tree_dirty": dirty,
        "tracked_file_count": len(files),
        "files": files,
        "extensions": dict(sorted(extensions.items())),
        "structural_checks": checks,
        "submodules": submodules,
        "symlinks": symlinks,
        "limitations": [
            "Structural checks establish presence only, not code quality or passing tests.",
            "Snapshot excludes uncommitted changes and untracked files.",
            "Submodule contents are excluded; their pinned commit IDs are recorded.",
            "Git LFS objects are not downloaded; archives may contain pointer files.",
            "Git export-ignore and export-subst attributes can affect archive contents.",
            "Repository URLs and local paths are omitted to avoid credential disclosure.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description="Capture a Git commit and auditable source manifest")
    parser.add_argument("repository", type=Path)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = snapshot(args.repository, args.ref, args.output)
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        # Do not echo Git stderr: remote URLs can contain credentials.
        print("Snapshot failed: " + (str(error) if not isinstance(error, subprocess.CalledProcessError)
                                    else "Git operation failed; verify repository and ref"), file=sys.stderr)
        return 1
    print(json.dumps({"commit": report["commit"], "archive_sha256": report["archive_sha256"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
