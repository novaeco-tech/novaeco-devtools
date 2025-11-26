import argparse
import sys
from nova_cli.commands import version, workspace

def main():
    parser = argparse.ArgumentParser(
        prog="nova", 
        description="Nova Ecosystem Developer Tools"
    )
    
    subparsers = parser.add_subparsers(dest="main_command", help="Available commands")

    # Register subcommands
    version.register_subcommand(subparsers)
    workspace.register_subcommand(subparsers)

    args = parser.parse_args()

    if args.main_command == "version":
        version.execute(args)
    elif args.main_command == "init":
        workspace.execute(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()