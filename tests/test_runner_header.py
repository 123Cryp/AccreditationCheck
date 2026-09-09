"""
Discovered live, not predicted by the offline stub (which has no concept of
the runner header at all — see CHANGELOG.md "[0.1.1]" and SECURITY.md
"Runner header must be pinned"): GenVM rejects the `:latest`/`:test` alias
runner tags outside Debug mode with
`':test/ :latest runner used in non-debug mode, this is not allowed'`.

This test can't catch a *behavioral* mismatch (the offline stub never talks
to a real runner), but it CAN catch a regression back to an alias tag via
plain static inspection of the header line, which is cheap and worth having
now that we know this specific failure mode exists.
"""
import os
import re

import conftest  # noqa: F401

_CONTRACT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract.py"
)

_FORBIDDEN_ALIAS_TAGS = {"latest", "test"}


class TestRunnerHeaderIsPinned:
    def setup_method(self):
        with open(_CONTRACT_PATH, "r") as f:
            self.lines = f.readlines()

    def test_second_line_is_a_depends_header(self):
        assert len(self.lines) >= 2
        assert '"Depends"' in self.lines[1]
        assert "py-genlayer:" in self.lines[1]

    def test_runner_tag_is_not_an_alias(self):
        match = re.search(r"py-genlayer:([A-Za-z0-9_.\-]+)", self.lines[1])
        assert match is not None, "could not find a py-genlayer:<tag> runner tag on line 2"
        tag = match.group(1)
        assert tag not in _FORBIDDEN_ALIAS_TAGS, (
            f"runner header uses alias tag {tag!r}, which GenVM rejects outside "
            f"Debug mode (confirmed live: \"':test/ :latest runner used in "
            f"non-debug mode, this is not allowed'\"). Use a pinned runner hash "
            f"instead, e.g. py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"
        )

    def test_runner_tag_looks_like_a_pinned_hash_not_a_short_word(self):
        # Heuristic, not a guarantee: a pinned runner hash is long. This is
        # meant to catch an accidental typo/alias, not to validate the hash
        # is actually resolvable (only a live deploy attempt can confirm that).
        match = re.search(r"py-genlayer:([A-Za-z0-9_.\-]+)", self.lines[1])
        tag = match.group(1)
        assert len(tag) >= 20, (
            f"runner tag {tag!r} looks too short to be a pinned runner hash — "
            f"double-check it isn't an alias"
        )
