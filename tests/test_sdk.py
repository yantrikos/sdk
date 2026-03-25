"""Tests for Yantrikos SDK."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from yantrikos import BaseTool, ToolResult, Tier, register, get, all_tools, schemas, full_schemas
from yantrikos.registry import clear, count, by_category, categories
from yantrikos.errors import ToolValidationError


class TestTier(unittest.TestCase):
    def test_tier_values(self):
        self.assertEqual(Tier.S.value, "S")
        self.assertEqual(Tier.M.value, "M")
        self.assertEqual(Tier.L.value, "L")
        self.assertEqual(Tier.XL.value, "XL")

    def test_tier_config(self):
        from yantrikos.tier import get_tier_config
        s_config = get_tier_config(Tier.S)
        self.assertEqual(s_config["max_tools"], 4)
        self.assertEqual(s_config["format"], "mcq")

        xl_config = get_tier_config(Tier.XL)
        self.assertEqual(xl_config["max_tools"], 0)  # unlimited


class TestToolResult(unittest.TestCase):
    def test_ok(self):
        r = ToolResult.ok({"data": 42})
        self.assertTrue(r.success)
        self.assertEqual(r.output, {"data": 42})

    def test_fail(self):
        r = ToolResult.fail("something broke")
        self.assertFalse(r.success)
        self.assertEqual(r.error, "something broke")

    def test_ok_with_metadata(self):
        r = ToolResult.ok("hello", source="test", version=2)
        self.assertEqual(r.metadata["source"], "test")


class SampleTool(BaseTool):
    name = "sample"
    category = "test"
    descriptions = {
        Tier.S: "Do thing",
        Tier.M: "Do the thing",
        Tier.L: "Do the thing with options",
        Tier.XL: "Do the thing with full control and detailed output",
    }
    parameters = {
        Tier.S: {"input": str},
        Tier.M: {"input": str, "format": str},
        Tier.L: {"input": str, "format": str, "verbose": bool},
        Tier.XL: {"input": str, "format": str, "verbose": bool, "limit": int},
    }
    def execute(self, input: dict, tier: Tier) -> ToolResult:
        if tier == Tier.S:
            return ToolResult.ok(input.get("input", ""))
        return ToolResult.ok({"input": input.get("input"), "tier": tier.value})


class TestBaseTool(unittest.TestCase):
    def setUp(self):
        self.tool = SampleTool()

    def test_get_description_per_tier(self):
        self.assertEqual(self.tool.get_description(Tier.S), "Do thing")
        self.assertEqual(self.tool.get_description(Tier.XL), "Do the thing with full control and detailed output")

    def test_get_parameters_per_tier(self):
        s_params = self.tool.get_parameters(Tier.S)
        self.assertEqual(len(s_params), 1)
        self.assertIn("input", s_params)

        xl_params = self.tool.get_parameters(Tier.XL)
        self.assertEqual(len(xl_params), 4)

    def test_execute_tier_s(self):
        r = self.tool.execute({"input": "hello"}, Tier.S)
        self.assertTrue(r.success)
        self.assertEqual(r.output, "hello")

    def test_execute_tier_xl(self):
        r = self.tool.execute({"input": "hello"}, Tier.XL)
        self.assertTrue(r.success)
        self.assertEqual(r.output["tier"], "XL")

    def test_safe_execute(self):
        r = self.tool.safe_execute({"input": "test"}, Tier.S)
        self.assertTrue(r.success)
        self.assertGreaterEqual(r.duration_ms, 0)

    def test_safe_execute_missing_param(self):
        r = self.tool.safe_execute({}, Tier.S)
        self.assertFalse(r.success)
        self.assertIn("Missing", r.error)

    def test_to_schema(self):
        schema = self.tool.to_schema(Tier.M)
        self.assertEqual(schema["name"], "sample")
        self.assertEqual(schema["description"], "Do the thing")
        self.assertIn("input", schema["parameters"])
        self.assertIn("format", schema["parameters"])

    def test_to_full_schema(self):
        schema = self.tool.to_full_schema()
        self.assertIn("S", schema["tiers"])
        self.assertIn("XL", schema["tiers"])
        self.assertEqual(len(schema["tiers"]), 4)

    def test_get_embedding_text(self):
        text = self.tool.get_embedding_text()
        self.assertIn("sample", text)
        self.assertIn("full control", text)

    def test_validate_class(self):
        errors = SampleTool.validate_class()
        self.assertEqual(len(errors), 0)


class TestBadTool(unittest.TestCase):
    def test_missing_name(self):
        class BadTool(BaseTool):
            name = ""
            descriptions = {t: "x" for t in Tier}
            parameters = {t: {} for t in Tier}
        errors = BadTool.validate_class()
        self.assertGreater(len(errors), 0)

    def test_missing_tier_description(self):
        class PartialTool(BaseTool):
            name = "partial"
            descriptions = {Tier.S: "short"}  # missing M, L, XL
            parameters = {t: {} for t in Tier}
        errors = PartialTool.validate_class()
        self.assertGreater(len(errors), 0)

    def test_register_invalid_raises(self):
        with self.assertRaises(ToolValidationError):
            @register
            class InvalidTool(BaseTool):
                name = ""  # invalid


class TestRegistry(unittest.TestCase):
    def setUp(self):
        clear()

    def test_register_and_get(self):
        register(SampleTool)
        tool = get("sample")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "sample")

    def test_all_tools(self):
        register(SampleTool)
        tools = all_tools()
        self.assertEqual(len(tools), 1)

    def test_by_category(self):
        register(SampleTool)
        tools = by_category("test")
        self.assertEqual(len(tools), 1)
        self.assertEqual(by_category("nonexistent"), [])

    def test_categories(self):
        register(SampleTool)
        cats = categories()
        self.assertIn("test", cats)

    def test_schemas_per_tier(self):
        register(SampleTool)
        s_schemas = schemas(Tier.S)
        self.assertEqual(len(s_schemas), 1)
        self.assertEqual(s_schemas[0]["description"], "Do thing")
        self.assertEqual(len(s_schemas[0]["parameters"]), 1)

    def test_full_schemas(self):
        register(SampleTool)
        fs = full_schemas()
        self.assertEqual(len(fs), 1)
        self.assertIn("tiers", fs[0])

    def test_count(self):
        self.assertEqual(count(), 0)
        register(SampleTool)
        self.assertEqual(count(), 1)


class TestFileToolsExample(unittest.TestCase):
    """Test the example file tools."""

    def setUp(self):
        clear()
        # Force re-register by importing the tool classes directly
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from examples.file_tools import FileReadTool, FileWriteTool, GrepTool
        register(FileReadTool)
        register(FileWriteTool)
        register(GrepTool)

    def test_file_tools_registered(self):
        self.assertIsNotNone(get("file_read"))
        self.assertIsNotNone(get("file_write"))
        self.assertIsNotNone(get("grep"))

    def test_file_read_tier_s(self):
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world\n" * 100)
            path = f.name
        try:
            tool = get("file_read")
            r = tool.safe_execute({"path": path}, Tier.S)
            self.assertTrue(r.success)
            self.assertLessEqual(len(r.output), 1000)
        finally:
            os.unlink(path)

    def test_file_read_tier_xl_line_numbers(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("line one\nline two\nline three\n")
            path = f.name
        try:
            tool = get("file_read")
            r = tool.safe_execute({"path": path, "line_numbers": True}, Tier.XL)
            self.assertTrue(r.success)
            self.assertIn("1:", r.output)
            self.assertIn("2:", r.output)
        finally:
            os.unlink(path)

    def test_file_write(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            tool = get("file_write")
            r = tool.safe_execute({"path": path, "content": "test content"}, Tier.M)
            self.assertTrue(r.success)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                self.assertEqual(f.read(), "test content")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_grep_tier_s(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world\nfoo bar\nhello again\n")
            path = f.name
        try:
            tool = get("grep")
            r = tool.safe_execute({"pattern": "hello", "path": path}, Tier.S)
            self.assertTrue(r.success)
            self.assertIn("2 matches", r.output)
        finally:
            os.unlink(path)

    def test_grep_tier_m(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("error: something failed\ninfo: all good\nerror: another failure\n")
            path = f.name
        try:
            tool = get("grep")
            r = tool.safe_execute({"pattern": "error", "path": path}, Tier.M)
            self.assertTrue(r.success)
            self.assertEqual(r.output["total"], 2)
        finally:
            os.unlink(path)

    def test_schema_s_vs_xl(self):
        tool = get("file_read")
        s_schema = tool.to_schema(Tier.S)
        xl_schema = tool.to_schema(Tier.XL)
        # S has fewer params
        self.assertLess(len(s_schema["parameters"]), len(xl_schema["parameters"]))
        # S has shorter description
        self.assertLess(len(s_schema["description"]), len(xl_schema["description"]))


if __name__ == "__main__":
    unittest.main()
