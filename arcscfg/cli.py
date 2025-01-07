# arcscfg/arcscfg/cli.py

import os
import argparse
from pathlib import Path
from arcscfg.utils.setup_workspace import setup_workspace

def get_available_workspaces():
    workspaces_dir = Path(os.path.join(Path(__file__).parent, "config/workspaces"))
    return [f.name for f in workspaces_dir.glob("*.yaml")]

def main():
    parser = argparse.ArgumentParser(description="ARCS environment configurator")
    parser.add_argument("command", choices=["setup", "install", "build"], help="Command to execute")
    parser.add_argument("--workspace", help="Path to the workspace configuration file", choices=get_available_workspaces())
    args = parser.parse_args()

    if args.command == "setup":
        if not args.workspace:
            print("Error: --workspace argument is required for the 'setup' command.")
            return
        workspace_config = Path(os.path.join(Path(__file__).parent, "config/workspaces", args.workspace))
        setup_workspace(workspace_config)
    elif args.command == "install":
        print("Installing dependencies")
    elif args.command == "build":
        print("Building workspace")

if __name__ == "__main__":
    main()
