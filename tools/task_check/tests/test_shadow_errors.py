"""A build check's `shadow_errors` (Lab game grader 1.23.0): every build of the task is made with
-ShadowVariableErrors, so a shadowing declaration fails it as the task's reported C4459 error does."""

import unittest

import helpers  # noqa: F401  (puts the tools folder on the path)

from task_check import check, tasks


def task(**build):
    return {"milestones": [{"name": "builds", "checks": [{"name": "editor_builds", "kind": "build", **build}]}]}


class ShadowErrors(unittest.TestCase):
    def test_only_a_task_that_sets_it_builds_with_the_switch(self):
        self.assertEqual(tasks.build_args(task()), [])
        self.assertEqual(tasks.build_args(task(fails_at_start=True, shadow_errors=True)), ["-ShadowVariableErrors"])
        self.assertNotIn("shadow_errors", tasks.check({"name": "b", "kind": "build"}))

    def test_a_shared_build_passes_the_switch_and_nothing_otherwise(self):
        asked = []

        class Project:
            def build(self, timeout, **kw):
                asked.append(kw)
                return "built"

        check.Built(Project()).build(60)
        kept2 = check.Built(Project())
        kept2.build(60, ["-ShadowVariableErrors"])
        self.assertEqual(asked, [{}, {"args": ["-ShadowVariableErrors"]}])


if __name__ == "__main__":
    unittest.main()
