import argparse
import sys
from novaeco_cli.commands import version, workspace, audit, export

def main():
    parser = argparse.ArgumentParser(
        prog="novaeco", 
        description="NovaEco Developer Tools"
    )
    
    subparsers = parser.add_subparsers(dest="main_command", help="Available commands")

    # Register subcommands
    version.register_subcommand(subparsers)
    workspace.register_subcommand(subparsers)
    audit.register_subcommand(subparsers)
    export.register_subcommand(subparsers)

    args = parser.parse_args()

    if args.main_command == "version":
        version.execute(args)
    elif args.main_command == "init":
        workspace.execute(args)
    elif args.main_command == "audit":
        audit.execute(args)
    elif args.main_command == "export":
        export.execute(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()