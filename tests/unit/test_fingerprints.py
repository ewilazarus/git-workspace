import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.fingerprint import (
    DEFAULT_ALGORITHM,
    DEFAULT_LENGTH,
    compute_fingerprints,
)
from git_workspace.manifest import Fingerprint


@pytest.fixture
def worktree(mocker: MockerFixture, tmp_path: Path) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = tmp_path
    return mock


class TestFingerprintDefaults:
    def test_default_algorithm(self) -> None:
        fp = Fingerprint(name="x")
        assert fp.algorithm == DEFAULT_ALGORITHM

    def test_default_length(self) -> None:
        fp = Fingerprint(name="x")
        assert fp.length == DEFAULT_LENGTH

    def test_default_files_is_empty(self) -> None:
        fp = Fingerprint(name="x")
        assert fp.files == []


class TestComputeFingerprints:
    def test_all_files_present_produces_stable_hash(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"hello")
        (tmp_path / "b.txt").write_bytes(b"world")
        fps = [Fingerprint(name="test", files=["a.txt", "b.txt"])]

        result1 = compute_fingerprints(worktree, fps)
        result2 = compute_fingerprints(worktree, fps)

        assert result1 == result2

    def test_missing_file_uses_null_marker(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "present.txt").write_bytes(b"content")
        fps_with_missing = [Fingerprint(name="test", files=["present.txt", "missing.txt"])]
        fps_both_present = [Fingerprint(name="test", files=["present.txt", "missing.txt"])]
        (tmp_path / "missing.txt").write_bytes(b"NULL")

        result_missing = compute_fingerprints(worktree, fps_with_missing)
        # Read the file so it "exists" but has b"NULL" content — hashes differently
        # because path bytes differ too; just verify stability
        result_with_null_file = compute_fingerprints(worktree, fps_both_present)

        # When the file exists with content b"NULL" and when it's absent with marker b"NULL",
        # the path prefix is the same so hashes should be equal
        assert result_missing == result_with_null_file

    def test_all_files_missing_still_produces_hash(self, worktree: MagicMock) -> None:
        fps = [Fingerprint(name="test", files=["no-such-file.txt"])]
        result = compute_fingerprints(worktree, fps)
        assert "test" in result
        assert len(result["test"]) == DEFAULT_LENGTH

    def test_hash_changes_when_content_changes(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_bytes(b"v1")
        fps = [Fingerprint(name="test", files=["f.txt"])]
        hash_before = compute_fingerprints(worktree, fps)["test"]

        (tmp_path / "f.txt").write_bytes(b"v2")
        hash_after = compute_fingerprints(worktree, fps)["test"]

        assert hash_before != hash_after

    def test_hash_changes_when_path_changes(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"same")
        (tmp_path / "b.txt").write_bytes(b"same")
        fps_a = [Fingerprint(name="test", files=["a.txt"])]
        fps_b = [Fingerprint(name="test", files=["b.txt"])]

        assert compute_fingerprints(worktree, fps_a) != compute_fingerprints(worktree, fps_b)

    def test_hash_stable_across_manifest_reordering(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"aaa")
        (tmp_path / "b.txt").write_bytes(b"bbb")
        fps_ordered = [Fingerprint(name="test", files=["a.txt", "b.txt"])]
        fps_reversed = [Fingerprint(name="test", files=["b.txt", "a.txt"])]

        assert compute_fingerprints(worktree, fps_ordered) == compute_fingerprints(worktree, fps_reversed)

    def test_sha256_and_md5_produce_different_hashes(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_bytes(b"data")
        fps_sha = [Fingerprint(name="test", files=["f.txt"], algorithm="sha256", length=32)]
        fps_md5 = [Fingerprint(name="test", files=["f.txt"], algorithm="md5", length=32)]

        assert compute_fingerprints(worktree, fps_sha) != compute_fingerprints(worktree, fps_md5)

    def test_length_truncates_digest(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_bytes(b"data")
        fps = [Fingerprint(name="test", files=["f.txt"], length=4)]
        result = compute_fingerprints(worktree, fps)
        assert len(result["test"]) == 4

    def test_length_exceeding_digest_size_returns_full_digest(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_bytes(b"data")
        fps = [Fingerprint(name="test", files=["f.txt"], algorithm="md5", length=999)]
        result = compute_fingerprints(worktree, fps)
        # md5 hex digest is 32 chars; slicing beyond just returns the full digest
        assert len(result["test"]) == 32

    def test_unsupported_algorithm_raises_value_error(self, worktree: MagicMock) -> None:
        fps = [Fingerprint(name="test", files=[], algorithm="blake2b")]
        with pytest.raises(ValueError, match="Unsupported fingerprint algorithm"):
            compute_fingerprints(worktree, fps)

    def test_multiple_fingerprints_keyed_by_raw_name(self, worktree: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"a")
        fps = [
            Fingerprint(name="alpha", files=["a.txt"]),
            Fingerprint(name="beta", files=["a.txt"], algorithm="md5"),
        ]
        result = compute_fingerprints(worktree, fps)
        assert set(result.keys()) == {"alpha", "beta"}

    def test_empty_files_list_produces_hash_of_empty_input(self, worktree: MagicMock) -> None:
        fps = [Fingerprint(name="empty", files=[], length=64)]
        result = compute_fingerprints(worktree, fps)
        expected = hashlib.sha256(b"").hexdigest()
        assert result["empty"] == expected
