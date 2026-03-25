import argparse
import sys

from novaeco_cli.commands import audit, build, bump, check, clean, deps, docs, export, test, workspace


def main():
    parser = argparse.ArgumentParser(prog="novaeco", description="NovaEco Developer Tools")

    subparsers = parser.add_subparsers(dest="main_command", help="Available commands")

    # Register subcommands
    bump.register_subcommand(subparsers)
    workspace.register_subcommand(subparsers)
    audit.register_subcommand(subparsers)
    export.register_subcommand(subparsers)
    build.register_subcommand(subparsers)
    test.register_subcommand(subparsers)
    check.register_subcommand(subparsers)
    docs.register_subcommand(subparsers)
    deps.register_subcommand(subparsers)
    clean.register_subcommand(subparsers)

    args = parser.parse_args()

    # Dispatch Logic
    if args.main_command == "bump":
        bump.execute(args)
    elif args.main_command == "init":
        workspace.execute(args)
    elif args.main_command == "audit":
        audit.execute(args)
    elif args.main_command == "export":
        export.execute(args)
    elif args.main_command == "build":
        build.execute(args)
    elif args.main_command == "test":
        test.execute(args)
    elif args.main_command == "check":
        check.execute(args)
    elif args.main_command == "docs":
        docs.execute(args)
    elif args.main_command == "deps":
        deps.execute(args)
    elif args.main_command == "clean":
        clean.execute(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
