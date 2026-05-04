"""
Bedrock 2.0 smoke runner.

Usage:
    python -m tests.smoke           # all
    python -m tests.smoke audio     # subset
    python -m tests.smoke services themes

Exit code = number of failed tests. 0 means everything green.

Designed to be a drop-in for `scripts/test.sh`. No pytest dependency.
Each test module exposes a `run()` that returns a list of
(name, ok: bool, info: str) tuples.
"""
import os
import sys
import time

# Be quiet about Kivy banner when imported by tests.
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

GREEN = "\033[32m" if sys.stdout.isatty() else ""
RED = "\033[31m" if sys.stdout.isatty() else ""
DIM = "\033[2m" if sys.stdout.isatty() else ""
RESET = "\033[0m" if sys.stdout.isatty() else ""

GROUPS = {
    "sensors":  "tests.test_sensors",
    "audio":    "tests.test_audio",
    "services": "tests.test_services",
    "themes":   "tests.test_themes",
}


def fmt(name, ok, info):
    mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    return f"  [{mark}] {name:<50} {DIM}{info}{RESET}"


def run_group(group_name, module_path):
    print(f"\n=== {group_name} ===")
    try:
        mod = __import__(module_path, fromlist=["run"])
    except Exception as e:
        print(f"  [{RED}LOAD-FAIL{RESET}] {module_path}: {e}")
        return [(module_path, False, repr(e))]
    t0 = time.time()
    results = mod.run()
    dt = time.time() - t0
    for name, ok, info in results:
        print(fmt(name, ok, info))
    print(f"  {DIM}({len(results)} tests, {dt:.2f}s){RESET}")
    return results


def main(argv):
    selected = [g for g in argv if g in GROUPS] or list(GROUPS.keys())
    print(f"Bedrock smoke — running: {', '.join(selected)}")
    print(f"  python: {sys.version.split()[0]}")
    print(f"  cwd:    {os.getcwd()}")

    all_results = []
    for g in selected:
        all_results.extend(run_group(g, GROUPS[g]))

    failed = [r for r in all_results if not r[1]]
    print()
    print(f"Total: {len(all_results)} tests, "
          f"{GREEN}{len(all_results) - len(failed)} pass{RESET}, "
          f"{RED}{len(failed)} fail{RESET}")
    if failed:
        print("\nFAILURES:")
        for name, _, info in failed:
            print(f"  • {name}: {info}")
    return len(failed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
