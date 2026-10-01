# Repo Snapshot Auditor

Capture a precise Git commit as a source archive and a machine-readable evidence manifest. Intended for repository collection, handoff, and engineering review.

## Run

Requires Python 3.9+ and Git. No third-party runtime dependencies.

```sh
PYTHONPATH=src python3 -m repo_snapshot_auditor /absolute/path/to/repository --ref HEAD --output /absolute/path/to/new-evidence-folder
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The output directory must be new and outside the source repository. Outputs are `source.tar` and `manifest.json`. The manifest records the resolved commit, commit date, SHA-256 checksum, tracked paths, file extensions, submodule pins, symlinks, and structural checks. Uncommitted files do not enter the archive; the manifest flags a dirty working tree.

## Review boundary

README, license, tests, and CI checks only detect file presence. They do not establish correctness, useful scope, license compatibility, or passing tests. An assessor must still read code, execute appropriate tests, inspect task boundaries, and verify collection requirements. Git attributes may exclude or substitute archived files. Submodule contents and Git LFS payloads are not fetched.

Archives can contain any committed data, including secrets. Inspect the source and evidence before sharing. The manifest intentionally omits remote URLs and local paths.

## Development provenance

Initial implementation was created with Codex assistance. This is a new portfolio project, not evidence of historical contributions or third-party acceptance. Git history, test results, and later reviews should reflect actual work. No backdated commits or synthetic reviews.

## Next milestones

- v0.1: local commit snapshot and evidence manifest; integration tests.
- v0.2 (planned): explicit collection rules, file-content inventory and LFS detection.
- v0.3 (planned): compare two commit manifests and report collection-relevant changes.

Only v0.1 functionality is currently implemented. No release or external review is claimed.
