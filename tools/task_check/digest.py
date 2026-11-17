"""Task identity shared with Lab's formats.game_dev_rl.checks.

The digest is of the task as delivered, before defaults or retired-check filtering. In a dataset its agent and
grader halves are merged first. Keep canonicalisation identical to Lab (sorted keys, compact JSON, Unicode UTF-8).
Standard library only.
"""

import hashlib
import json

GRADER_KEYS = ("milestones",)


def merged(task, grader):
    """Join task.json and grader.json exactly as formats.game_dev_rl.checks.merged does."""
    whole = dict(task)
    for k in GRADER_KEYS:
        if k in grader:
            whole[k] = grader[k]
    if isinstance(grader.get("seed"), dict) and isinstance(whole.get("seed"), dict):
        whole["seed"] = dict(whole["seed"], **grader["seed"])
    return whole


def canonical_digest(task):
    """SHA-256 of canonical JSON, byte for byte the digest Lab pins on the task model."""
    return hashlib.sha256(json.dumps(task, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()
