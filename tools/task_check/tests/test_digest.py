"""Canonical task identity pinned against a digest computed with Lab's own format code."""

import importlib.util
import json
import unittest
from pathlib import Path

import helpers  # puts tools/ on the import path
from task_check.digest import canonical_digest, merged

FIXTURE = Path(__file__).parent / "fixtures" / "task-digest.json"


class TaskDigest(unittest.TestCase):
    def test_split_halves_have_the_digest_computed_with_lab(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        task = merged(fixture["task"], fixture["grader"])
        self.assertEqual(canonical_digest(task), fixture["digest"])
        # The source file and the two shipped halves represent the same task, even with Unicode and floats.
        spec = importlib.util.spec_from_file_location("split_tasks", Path(helpers.TOOLS) / "split-tasks.py")
        splitter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(splitter)
        agent, grader = splitter.split(task)
        self.assertEqual(merged(agent, grader), task)
        self.assertEqual(canonical_digest(merged(agent, grader)), fixture["digest"])

    def test_merging_uses_only_grader_keys_and_joins_seed(self):
        agent = {"name": "a", "title": "Agent title", "seed": {"commit": "first"}, "milestones": []}
        grader = {"name": "b", "title": "Ignored title", "seed": {"reference": "last"}, "milestones": [1]}
        self.assertEqual(merged(agent, grader), {**agent, "seed": {"commit": "first", "reference": "last"},
                                               "milestones": [1]})
        self.assertEqual(agent["seed"], {"commit": "first"}, "merging does not mutate the agent half")

    def test_key_order_and_json_whitespace_do_not_change_identity_but_grader_edits_do(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        task = merged(fixture["task"], fixture["grader"])
        reversed_task = dict(reversed(list(task.items())))
        self.assertEqual(canonical_digest(json.loads(json.dumps(reversed_task))), fixture["digest"])
        task["seed"]["reference"] = "c" * 40
        self.assertNotEqual(canonical_digest(task), fixture["digest"])


if __name__ == "__main__":
    unittest.main()
