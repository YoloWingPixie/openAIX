"""Command line: python3 -m openaix <command> [arguments], with tools/ on PYTHONPATH (Taskfile.yml sets it)."""
import importlib
import sys

COMMANDS = {
    "generate": ("openaix.generate", "generate schemas/, catalogues/ and examples/ (--check: fail when one is stale)"),
    "validate": ("openaix.check.validate", "validate the schemas and examples, or one document"),
    "lint": ("openaix.describe.lint", "lint every generated description"),
    "source-audit": ("openaix.sources.audit", "check that catalogue entries cite a resolvable first-party source"),
    "fetch-authorities": ("openaix.sources.fetch", "download and verify pinned authority files into .cache/"),
    "viewer": ("openaix.viewer", "serve the schema and example browser"),
}


def usage():
    width = max(map(len, COMMANDS))
    lines = ["usage: python3 -m openaix <command> [arguments]", "", "commands:"]
    lines += [f"  {name.ljust(width)}  {text}" for name, (_, text) in COMMANDS.items()]
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(usage())
    command = sys.argv[1]
    sys.argv = ["openaix " + command, *sys.argv[2:]]
    importlib.import_module(COMMANDS[command][0]).main()


if __name__ == "__main__":
    main()
