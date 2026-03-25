import argparse
import os
import subprocess
import sys

from rich.console import Console

# We conditionally import the reporter so it doesn't crash if it's missing
try:
    from novaeco_cli.utils.reporting import RstReporter

    HAS_REPORTER = True
except ImportError:
    HAS_REPORTER = False

console = Console()


def register_subcommand(subparsers):
    examples = """Examples:
  # Run all static analysis checks (Lint, Types, Security)
  novaeco check all

  # Run linters and auto-fix formatting issues
  novaeco check lint --fix

  # Run strict type checking and auto-fix missing return types
  novaeco check typecheck --fix
  
  # Run security scanners (Bandit for Python, Semgrep for C++/Python)
  novaeco check security
"""
    parser = subparsers.add_parser(
        "check",
        help="Run static analysis (Linting, Formatting, Type Checking, SAST)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )

    subs = parser.add_subparsers(dest="check_command", required=True)

    p_all = subs.add_parser("all", help="Run all static analysis checks")
    p_all.add_argument(
        "--fix", action="store_true", help="Auto-fix linting/formatting and missing types where possible"
    )

    p_lint = subs.add_parser("lint", help="Run Ruff (Python) and Doc8/rstcheck (Docs)")
    p_lint.add_argument("--fix", action="store_true", help="Auto-fix linting/formatting where possible")

    p_typecheck = subs.add_parser("typecheck", help="Run MyPy strict type checking")
    p_typecheck.add_argument("--fix", action="store_true", help="Auto-inject missing return types using autotyping")

    subs.add_parser("security", help="Run SAST scanners (Bandit & Semgrep)")


def get_fractal_python_dirs():
    """Returns a list of valid Python source directories in the new architecture."""
    # We deliberately exclude 'api/src' because it contains auto-generated
    # Protobuf code which should not be subjected to strict human type-checking.
    candidates = ["domain/src", "service/src", "client/src", "tests"]
    return [d for d in candidates if os.path.exists(d)]


def run_cmd(name, cmd, cwd=".", allow_fail=False, env=None):
    """Helper to run a command and report status."""
    console.print(f"\n[bold blue]🔍 {name}...[/bold blue]")
    sys.stdout.flush()

    # Pass the env variable down to subprocess.run
    result = subprocess.run(cmd, cwd=cwd, env=env)

    if result.returncode != 0:
        if allow_fail:
            console.print(f"[bold yellow]⚠️  {name} found issues (Non-blocking).[/bold yellow]")
            return False
        console.print(f"[bold red]❌ {name} Failed.[/bold red]")
        return False

    console.print(f"[bold green]✅ {name} Passed.[/bold green]")
    return True


def check_lint(fix=False):
    """Runs Python and Documentation Linters."""
    success = True

    # 1. Python Linting & Formatting (Ruff)
    # Ruff is incredibly fast, so we run it on the whole root directory (it respects pyproject.toml excludes)
    ruff_check_cmd = ["ruff", "check", "."]
    ruff_fmt_cmd = ["ruff", "format", "."]

    if fix:
        ruff_check_cmd.append("--fix")
    else:
        ruff_fmt_cmd.append("--check")

    success &= run_cmd("Ruff Linting", ruff_check_cmd)
    success &= run_cmd("Ruff Formatting", ruff_fmt_cmd)

    # 2. Documentation Linting (Doc8 / rstcheck)
    if os.path.exists("docs/source"):
        success &= run_cmd("Doc8 (Style)", ["doc8", "source"], cwd="docs", allow_fail=True)
        success &= run_cmd("rstcheck (Syntax)", ["rstcheck", "-r", "source"], cwd="docs", allow_fail=True)

    return success


def check_typecheck(fix=False):
    """Runs MyPy Type Checking on specific Python directories."""
    target_dirs = get_fractal_python_dirs()
    if not target_dirs:
        console.print("⚠️  No Python source directories found. Skipping Typecheck.")
        return True

    if fix:
        console.print("\n[bold blue]🔧 Auto-fixing types with autotyping...[/bold blue]")
        # --safe ensures it only adds unambiguous types like `-> None`, `-> bool`, etc.
        subprocess.run(["autotyping"] + target_dirs + ["--safe"])

        # Clean up any formatting quirks introduced by autotyping
        subprocess.run(["ruff", "format"] + target_dirs, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Build MYPYPATH to map the src directories correctly to prevent namespace collisions
    env = os.environ.copy()
    src_paths = [os.path.abspath(d) for d in target_dirs if d.endswith("src")]
    if src_paths:
        existing = env.get("MYPYPATH", "")
        env["MYPYPATH"] = ":".join(src_paths) + (":" + existing if existing else "")

    cmd = ["mypy"] + target_dirs
    # Use the modified environment for the MyPy execution
    return run_cmd("MyPy Type Check", cmd, env=env)


def check_security():
    """Runs Bandit (Python SAST) and Semgrep (Multi-Language SAST)."""
    success = True

    # --- 1. Bandit (Python specific) ---
    target_dirs = get_fractal_python_dirs()
    if target_dirs:
        # A. Console Output (for the developer)
        cmd_console = ["bandit", "-r"] + target_dirs + ["-ll"]
        success &= run_cmd("Bandit Security Scan", cmd_console, allow_fail=True)

        # B. Report Generation (For Sphinx Docs)
        if HAS_REPORTER and os.path.exists("docs/source"):
            console.print("   [dim]Generating RST Security Report...[/dim]")
            reporter = RstReporter(".")
            json_report_path = "bandit_report.json"

            # Run silently to generate JSON
            subprocess.run(
                ["bandit", "-r"] + target_dirs + ["-f", "json", "-o", json_report_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            reporter.write_security_report(json_report_path)

            if os.path.exists(json_report_path):
                os.remove(json_report_path)
    else:
        console.print("⚠️  No Python source directories found. Skipping Bandit.")

    # --- 2. Semgrep (C++ & Python) ---
    # Semgrep filters by extension automatically, so targeting "." is safe for polyrepo components
    semgrep_cmd = ["semgrep", "scan", "--config=p/python", "--config=p/c", "--error", "."]

    # Disable io_uring to prevent OCaml out-of-memory crashes inside Docker containers
    env = os.environ.copy()
    env["EIO_BACKEND"] = "posix"

    # allow_fail=False ensures that if Semgrep finds a vulnerability, it hard-fails the CI pipeline.
    success &= run_cmd("Semgrep Multi-Language SAST", semgrep_cmd, allow_fail=False, env=env)

    return success


def execute(args):
    cmd = args.check_command
    success = True

    if cmd == "all":
        success &= check_lint(fix=args.fix)
        success &= check_typecheck(fix=args.fix)
        success &= check_security()

        if success:
            console.print("\n[bold green]🎉 All Static Analysis Checks Passed![/bold green]")
        else:
            console.print("\n[bold red]🛑 Static Analysis Failed. Please fix the issues above.[/bold red]")
            sys.exit(1)

    elif cmd == "lint":
        success = check_lint(fix=args.fix)
    elif cmd == "typecheck":
        success = check_typecheck(fix=args.fix)
    elif cmd == "security":
        success = check_security()

    if not success:
        sys.exit(1)
