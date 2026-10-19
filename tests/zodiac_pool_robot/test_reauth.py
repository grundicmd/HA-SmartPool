"""Dependency-free regression checks for HACS reauthentication handling."""

from pathlib import Path
import ast
import json
import unittest

ROOT = Path(__file__).parents[2] / "custom_components" / "zodiac_pool_robot"


class ReauthContractTests(unittest.TestCase):
    def test_reauth_methods_and_reload(self):
        source = (ROOT / "config_flow.py").read_text()
        tree = ast.parse(source)
        flow = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name == "ZodiacPoolRobotConfigFlow")
        methods = {node.name: node for node in flow.body if isinstance(node, ast.AsyncFunctionDef)}
        self.assertIn("async_step_reauth", methods)
        self.assertIn("async_step_reauth_confirm", methods)
        self.assertIn("async_update_reload_and_abort", ast.unparse(methods["async_step_reauth_confirm"]))
        self.assertIn("await client.async_login()", ast.unparse(methods["async_step_reauth_confirm"]))

    def test_auth_exceptions_precede_generic_errors(self):
        for filename, method in (("coordinator.py", "_async_update_data"),
                                 ("api.py", "async_get_status")):
            source = ast.parse((ROOT / filename).read_text())
            matches = [node for node in ast.walk(source)
                       if isinstance(node, ast.AsyncFunctionDef) and node.name == method]
            self.assertEqual(len(matches), 1)
            bodies = [ast.unparse(node) for node in ast.walk(matches[0])
                      if isinstance(node, ast.Try)]
            self.assertTrue(any("except ZodiacAuthError" in body for body in bodies),
                            filename)
        coord = (ROOT / "coordinator.py").read_text()
        self.assertLess(coord.index("except ZodiacAuthError"),
                        coord.index("except ZodiacApiError"))

    def test_reauth_translations(self):
        for name in ("strings.json", "translations/en.json", "translations/ru.json"):
            doc = json.loads((ROOT / name).read_text())
            self.assertIn("reauth_confirm", doc["config"]["step"])
            self.assertIn("password", doc["config"]["step"]["reauth_confirm"]["data"])
            self.assertIn("reauth_successful", doc["config"]["abort"])


if __name__ == "__main__":
    unittest.main()
