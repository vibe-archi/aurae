"""Run the shipped transparent validator's behavior without materializing a script."""
import copy
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/aurae/references/workspace-validator-source.md"


class WorkspaceValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        markdown = SOURCE.read_text(encoding="utf-8")
        source = markdown.split("```python\n", 1)[1].split("\n```", 1)[0]
        cls.validator = {"__name__": "aurae_reference_validator"}
        exec(compile(source, str(SOURCE), "exec"), cls.validator)

    def test_embedded_behavioral_regressions(self):
        result = self.validator["self_test"]()
        for case in result["cases"]:
            with self.subTest(case=case["case"]):
                self.assertTrue(case["passed"], case["errors"])
        self.assertTrue(result["passed"])

    def test_validation_is_read_only_and_deterministic(self):
        documents = self.validator["final_fixture"]()
        previous = self.validator["resolved_fixture"]()
        original = copy.deepcopy((documents, previous))
        validate = self.validator["validate_documents"]
        result = validate(documents, previous)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result, validate(documents, previous))
        self.assertEqual(original, (documents, previous))


if __name__ == "__main__":
    unittest.main()
