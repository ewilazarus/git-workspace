import hashlib
import logging
from typing import TYPE_CHECKING

from git_workspace.manifest import Fingerprint

if TYPE_CHECKING:
    from git_workspace.worktree import Worktree

logger = logging.getLogger(__name__)

DEFAULT_ALGORITHM = "sha256"
DEFAULT_LENGTH = 12
SUPPORTED_ALGORITHMS = frozenset({"sha256", "md5"})
_MISSING_FILE_MARKER = b"NULL"

__all__ = [
    "DEFAULT_ALGORITHM",
    "DEFAULT_LENGTH",
    "Fingerprint",
    "SUPPORTED_ALGORITHMS",
    "compute_fingerprints",
]


def compute_fingerprints(worktree: Worktree, fingerprints: list[Fingerprint]) -> dict[str, str]:
    """
    Compute one short hash per fingerprint definition, keyed by raw name.

    For each fingerprint, files are sorted alphabetically then concatenated as
    ``<relative_path_bytes> + <file_bytes>`` (or ``b"NULL"`` when a file is
    missing or unreadable) into a single rolling hasher. The hex digest is
    then truncated to ``fingerprint.length`` characters.

    :param worktree: Worktree whose root is used to resolve file paths.
    :param fingerprints: Fingerprint definitions from the manifest.
    :returns: Mapping from raw fingerprint name to truncated hex digest.
    :raises ValueError: If a fingerprint specifies an unsupported algorithm.
    """
    result: dict[str, str] = {}
    for fp in fingerprints:
        if fp.algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported fingerprint algorithm {fp.algorithm!r} for fingerprint {fp.name!r}"
            )
        logger.debug(
            "computing fingerprint %r using %s over %d file(s)",
            fp.name,
            fp.algorithm,
            len(fp.files),
        )
        hasher = hashlib.new(fp.algorithm)
        for rel in sorted(fp.files):
            hasher.update(rel.encode("utf-8"))
            try:
                hasher.update((worktree.dir / rel).read_bytes())
            except OSError:
                logger.debug(
                    "file %r missing or unreadable in worktree %s, using NULL marker",
                    rel,
                    worktree.dir,
                )
                hasher.update(_MISSING_FILE_MARKER)
        digest = hasher.hexdigest()[: fp.length]
        logger.debug("fingerprint %r = %r", fp.name, digest)
        result[fp.name] = digest
    return result
