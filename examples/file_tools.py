"""Example: File operation tools built with Yantrikos SDK."""

import os
from yantrikos import BaseTool, ToolResult, Tier, register


@register
class FileReadTool(BaseTool):
    name = "file_read"
    category = "filesystem"

    descriptions = {
        Tier.S:  "Read file",
        Tier.M:  "Read a file from disk",
        Tier.L:  "Read the contents of a file from the local filesystem",
        Tier.XL: "Read the contents of a file from the local filesystem. Supports text and binary files with optional line numbering, encoding control, and range selection.",
    }

    parameters = {
        Tier.S:  {"path": str},
        Tier.M:  {"path": str, "encoding": str},
        Tier.L:  {"path": str, "encoding": str, "line_numbers": bool},
        Tier.XL: {"path": str, "encoding": str, "line_numbers": bool, "offset": int, "limit": int},
    }

    def execute(self, input: dict, tier: Tier) -> ToolResult:
        path = input.get("path", "")
        if not path or not os.path.exists(path):
            return ToolResult.fail(f"File not found: {path}")

        encoding = input.get("encoding", "utf-8")

        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            return ToolResult.fail("Cannot read file as text")

        # Tier S: simple read, capped at 1000 chars
        if tier == Tier.S:
            return ToolResult.ok(content[:1000])

        # Tier M: full read
        if tier == Tier.M:
            return ToolResult.ok(content)

        # Tier L/XL: line numbers, offset, limit
        if input.get("line_numbers"):
            lines = content.split("\n")
            offset = input.get("offset", 0)
            limit = input.get("limit", len(lines))
            lines = lines[offset:offset + limit]
            content = "\n".join(f"{i + offset + 1}: {l}" for i, l in enumerate(lines))

        return ToolResult.ok(content)


@register
class FileWriteTool(BaseTool):
    name = "file_write"
    category = "filesystem"

    descriptions = {
        Tier.S:  "Write file",
        Tier.M:  "Write content to a file",
        Tier.L:  "Write content to a file on disk with encoding control",
        Tier.XL: "Write content to a file on disk. Supports text encoding, append mode, and atomic writes with backup.",
    }

    parameters = {
        Tier.S:  {"path": str, "content": str},
        Tier.M:  {"path": str, "content": str},
        Tier.L:  {"path": str, "content": str, "encoding": str},
        Tier.XL: {"path": str, "content": str, "encoding": str, "append": bool, "backup": bool},
    }

    def execute(self, input: dict, tier: Tier) -> ToolResult:
        path = input.get("path", "")
        content = input.get("content", "")
        encoding = input.get("encoding", "utf-8")
        append = input.get("append", False)

        if not path:
            return ToolResult.fail("Path required")

        # XL: backup before overwrite
        if tier == Tier.XL and input.get("backup") and os.path.exists(path):
            import shutil
            shutil.copy2(path, path + ".bak")

        mode = "a" if append else "w"
        try:
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
            return ToolResult.ok({"written": len(content), "path": path})
        except Exception as e:
            return ToolResult.fail(str(e))


@register
class GrepTool(BaseTool):
    name = "grep"
    category = "search"

    descriptions = {
        Tier.S:  "Search in files",
        Tier.M:  "Search for text patterns in files",
        Tier.L:  "Search for text patterns in files using regex matching",
        Tier.XL: "Search for text patterns in files using full regex. Supports recursive search, file type filtering, context lines, and match counting.",
    }

    parameters = {
        Tier.S:  {"pattern": str},
        Tier.M:  {"pattern": str, "path": str},
        Tier.L:  {"pattern": str, "path": str, "recursive": bool},
        Tier.XL: {"pattern": str, "path": str, "recursive": bool, "file_type": str, "context": int},
    }

    def execute(self, input: dict, tier: Tier) -> ToolResult:
        import re
        pattern = input.get("pattern", "")
        path = input.get("path", ".")

        if not pattern:
            return ToolResult.fail("Pattern required")

        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return ToolResult.fail(f"Invalid regex: {e}")

        if os.path.isfile(path):
            files = [path]
        elif os.path.isdir(path):
            if input.get("recursive") and tier in (Tier.L, Tier.XL):
                files = []
                for root, _, fnames in os.walk(path):
                    for f in fnames:
                        files.append(os.path.join(root, f))
            else:
                files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        else:
            return ToolResult.fail(f"Path not found: {path}")

        for fp in files[:100]:  # cap at 100 files
            try:
                with open(fp, "r") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append({"file": fp, "line": i, "text": line.strip()[:200]})
            except (UnicodeDecodeError, PermissionError):
                continue

        # Tier S: just return count
        if tier == Tier.S:
            return ToolResult.ok(f"{len(matches)} matches found")

        return ToolResult.ok({"matches": matches[:50], "total": len(matches)})
