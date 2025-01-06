# arcscfg/arcscfg/cli.py

import argparse

def main():
    parser = argparse.ArgumentParser(description="ARCS environment configurator")
    parser.add_argument("command", choices=["setup", "install", "build"], help="Command to execute")
    parser.add_argument("--workspace", help="Path to the workspace configuration file")
    args = parser.parse_args()

    if args.command == "setup":
        print(f"Setting up workspace using {args.workspace}")
    elif args.command == "install":
        print("Installing dependencies")
    elif args.command == "build":
        print("Building workspace")

if __name__ == "__main__":
    main()
