# arcscfg/arcscfg/cli.py

import os
import argparse
from pathlib import Path
from arcscfg.utils.workspace_setup import setup_workspace

def get_workspace_configs(full_paths=False):
    workspaces_dir = Path(os.path.join(Path(__file__).parent, "config/workspaces"))
    if full_paths:
        return [f for f in workspaces_dir.glob("*.yaml")]
    else:
        return [f.name for f in workspaces_dir.glob("*.yaml")]

def prompt_for_workspace_configs(workspace_configs):
    """Prompt the user to select an underlay."""
    print("Available workspace configs:")
    for i, workspace_config in enumerate(workspace_configs):
        print(f"{i}: {workspace_config}")

    choice = input("Select a workspace config (default: 0): ")
    if choice:
        return workspace_configs[int(choice)]
    return workspace_configs[0]

def main():
    parser = argparse.ArgumentParser(description="ARCS environment configurator")
    parser.add_argument("command", choices=["setup", "install", "build"], help="Command to execute")
    parser.add_argument("-w", "--workspace", help="ROS 2 workspace path.")
    parser.add_argument("-wc", "--workspace-config",
                        help=f"Workspace config. Select from available configs ({get_workspace_configs()}) or provide workspace config path.")
    args = parser.parse_args()

    if args.command == "setup":
        workspace_config = None
        if args.workspace_config:
            try:
                workspace_config = Path(args.workspace_config)
                assert(workspace_config.is_file())
            except Exception:
                try:
                    workspace_config = Path(os.path.join(Path(__file__).parent, "config/workspaces", args.workspace_config))
                    assert(workspace_config.is_file())
                except Exception:
                    try:
                        workspace_config = Path(os.path.join(Path(__file__).parent, "config/workspaces", args.workspace_config, ".yaml"))
                        assert(workspace_config.is_file())
                    except Exception:
                        workspace_config = None
                        print("Unable to resolve workspace config argument!")
        if not workspace_config:
            workspace_config = prompt_for_workspace_configs(get_workspace_configs(full_paths=True))
        
        if not args.workspace:
            # Derive workspace name from the YAML file name
            workspace_name = Path(workspace_config).stem + "_ws"
            workspace_name = input(f"Enter workspace name (default: {workspace_name}): ") or workspace_name
            workspace = str(os.path.join(Path.home(), workspace_name))
        else:
            workspace = args.workspace

        setup_workspace(workspace, workspace_config)
    elif args.command == "install":
        print("Installing dependencies")
    elif args.command == "build":
        print("Building workspace")

if __name__ == "__main__":
    main()
