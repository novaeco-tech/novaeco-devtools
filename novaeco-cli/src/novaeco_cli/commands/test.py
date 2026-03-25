import argparse
import os
import subprocess
import sys

from rich.console import Console

console = Console()


def register_subcommand(subparsers):
    examples = """Examples:
  # Run all test layers (L5 -> L4 -> L3)
  novaeco test all

  # Run L5 Unit Tests (C++ Core & Python Domain/Service/Client)
  novaeco test unit

  # Run L4 Contract Tests
  novaeco test contract
  
  # Run L3 End-to-End Tests
  novaeco test e2e
"""
    parser = subparsers.add_parser(
        "test",
        help="Execute V-Model Test Suites (L5 to L3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )

    subs = parser.add_subparsers(dest="test_command", required=True)

    subs.add_parser("all", help="Run all component tests (Unit -> Contract -> E2E)")
    subs.add_parser("unit", help="Run L5 Unit Tests (C++ Core & Python Logic)")
    subs.add_parser("integration", help="Run L4 Integration Tests")
    subs.add_parser("contract", help="Run L4 API Contract Tests")
    subs.add_parser("e2e", help="Run L3 End-to-End Tests")
    subs.add_parser("performance", help="Run L5 Micro-Benchmarks")
    subs.add_parser("accessibility", help="Run L3 A11y Scans")


def get_test_env():
    """
    Injects local source directories into PYTHONPATH.
    This allows pytest to run against the latest local code WITHOUT
    requiring the developer to run `pip install -e .` after every edit.
    """
    env = os.environ.copy()
    paths = []
    for p in ["domain/src", "service/src", "client/src", "api/src"]:
        if os.path.exists(p):
            paths.append(os.path.abspath(p))

    if paths:
        existing = env.get("PYTHONPATH", "")
        # Append local paths first
        env["PYTHONPATH"] = ":".join(paths) + (":" + existing if existing else "")
    return env


def run_pytest(target_dirs, name, allow_fail=False):
    """Helper to run pytest safely against a list of directories."""
    valid_dirs = [d for d in target_dirs if os.path.exists(d)]

    if not valid_dirs:
        console.print(f"⚠️  No directories found for {name}. Skipping.")
        return True

    console.print(f"\n[bold blue]🧪 Running {name}...[/bold blue]")

    # We use --import-mode=importlib to prevent module name collisions
    # (e.g., if domain/tests/test_models.py and client/tests/test_models.py both exist)
    cmd = [sys.executable, "-m", "pytest", "--import-mode=importlib"] + valid_dirs

    result = subprocess.run(cmd, env=get_test_env())

    if result.returncode != 0:
        if allow_fail:
            console.print(f"[bold yellow]⚠️ {name} Failed (Non-blocking).[/bold yellow]")
        else:
            console.print(f"[bold red]❌ {name} Failed.[/bold red]")
        return False

    console.print(f"[bold green]✅ {name} Passed.[/bold green]")
    return True


def run_ctest():
    """Helper to run C++ Core unit tests via CTest."""
    if not os.path.exists("core"):
        return True  # Not a hybrid repo, skip gracefully

    console.print("\n[bold blue]🧪 Running L5 Unit Tests (C++ Core)...[/bold blue]")

    # Try using the Conan release preset (standard in CI)
    cmd = ["ctest", "--preset", "conan-release", "--output-on-failure"]

    try:
        result = subprocess.run(cmd, cwd="core")
        if result.returncode != 0:
            console.print("[bold red]❌ C++ Core Tests Failed.[/bold red]")
            return False
    except FileNotFoundError:
        console.print("[bold red]❌ 'ctest' not found. Is the C++ toolchain installed?[/bold red]")
        return False

    console.print("[bold green]✅ C++ Core Tests Passed.[/bold green]")
    return True


# --- Layer Runners ---


def test_unit():
    # Run C++ Core tests first
    c_success = run_ctest()
    if not c_success:
        return False

    # Then run Python Logic tests
    return run_pytest(["domain/tests", "service/tests", "client/tests"], "L5 Unit Tests (Python)")


def test_integration():
    return run_pytest(["tests/integration"], "L4 Integration Tests")


def test_contract():
    return run_pytest(["tests/integration/contracts"], "L4 Contract Tests")


def test_e2e():
    return run_pytest(["tests/e2e"], "L3 Component E2E Tests")


def test_performance():
    return run_pytest(["tests/performance"], "L5 Performance Benchmarks")


def test_accessibility():
    # Accessibility is often allowed to fail in early dev, so we pass allow_fail=True
    # or you can enforce it strictly by removing that parameter.
    return run_pytest(["tests/accessibility"], "L3 Accessibility Scans")


def execute(args):
    cmd = args.test_command
    success = True

    if cmd == "all":
        # Run the full V-Model stack in order
        success = test_unit()
        if success:
            success = test_contract()
        if success:
            success = test_integration()
        if success:
            success = test_e2e()

        if success:
            console.print("\n[bold green]🎉 All Component Test Layers Passed![/bold green]")
        else:
            console.print("\n[bold red]🛑 Test Suite Failed. Fix errors before proceeding.[/bold red]")
            sys.exit(1)

    elif cmd == "unit":
        success = test_unit()
    elif cmd == "integration":
        success = test_integration()
    elif cmd == "contract":
        success = test_contract()
    elif cmd == "e2e":
        success = test_e2e()
    elif cmd == "performance":
        success = test_performance()
    elif cmd == "accessibility":
        success = test_accessibility()

    if not success:
        sys.exit(1)
