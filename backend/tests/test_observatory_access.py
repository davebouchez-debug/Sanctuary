"""Dependency-free regression check for the Observatory route authorization wiring."""
import ast
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def route_guards(path, router, prefix=""):
    guards = {}
    tree = ast.parse((BACKEND / path).read_text("utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            receiver = decorator.func.value
            if not isinstance(receiver, ast.Name) or receiver.id != router or not decorator.args:
                continue
            path_arg = decorator.args[0]
            if not isinstance(path_arg, ast.Constant) or not isinstance(path_arg.value, str):
                continue
            if path_arg.value.startswith(prefix):
                deps = next((kw.value for kw in decorator.keywords if kw.arg == "dependencies"), None)
                guards[(decorator.func.attr, path_arg.value)] = ast.unparse(deps) if deps else None
    return guards


class ObservatoryAccessWiring(unittest.TestCase):
    def test_provenance_routes_require_guardian(self):
        guarded = route_guards("server.py", "api_router", "/provenance/")
        self.assertIn(("get", "/provenance/turn/{provenance_id}"), guarded)
        self.assertIn(("get", "/provenance/turns"), guarded)
        self.assertTrue(all(guard == "[Depends(require_guardian)]" for guard in guarded.values()), guarded)

    def test_ledger_routes_require_guardian_except_secret_authenticated_cron(self):
        guarded = route_guards("observatory_ledger/routes.py", "router")
        self.assertIn(("get", "/entry/{entry_id:path}"), guarded)
        self.assertIn(("post", "/run"), guarded)
        guarded.pop(("post", "/cron/tick"))
        self.assertTrue(all(guard == "[Depends(require_guardian)]" for guard in guarded.values()), guarded)


if __name__ == "__main__":
    unittest.main()
