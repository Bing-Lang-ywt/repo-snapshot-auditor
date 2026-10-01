import hashlib
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from repo_snapshot_auditor.__main__ import snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.git("init")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "README.md").write_text("committed content\n")
        self.git("add", ".")
        self.git("commit", "-m", "Create fixture")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def test_dirty_tree_does_not_change_snapshot(self):
        (self.repo / "README.md").write_text("uncommitted changes\n")
        (self.repo / "secret.txt").write_text("not tracked\n")
        out = self.base / "evidence"
        report = snapshot(self.repo, "HEAD", out)
        self.assertTrue(report["working_tree_dirty"])
        self.assertEqual(report["files"], ["README.md"])
        with tarfile.open(out / "source.tar") as archive:
            self.assertEqual(archive.extractfile("README.md").read(), b"committed content\n")
            self.assertNotIn("secret.txt", archive.getnames())
        self.assertEqual(report["archive_sha256"], hashlib.sha256((out / "source.tar").read_bytes()).hexdigest())
        self.assertEqual(json.loads((out / "manifest.json").read_text()), report)

    def test_same_commit_produces_same_archive(self):
        a = snapshot(self.repo, "HEAD", self.base / "a")
        b = snapshot(self.repo, "HEAD", self.base / "b")
        self.assertEqual(a["archive_sha256"], b["archive_sha256"])

    def test_existing_output_is_preserved(self):
        out = self.base / "existing"
        out.mkdir()
        (out / "keep.txt").write_text("keep")
        with self.assertRaises(FileExistsError):
            snapshot(self.repo, "HEAD", out)
        self.assertEqual((out / "keep.txt").read_text(), "keep")

    def test_output_inside_repository_is_rejected(self):
        with self.assertRaises(ValueError):
            snapshot(self.repo, "HEAD", self.repo / "evidence")

    def test_invalid_ref_does_not_create_output(self):
        out = self.base / "invalid"
        with self.assertRaises(subprocess.CalledProcessError):
            snapshot(self.repo, "missing-ref", out)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
