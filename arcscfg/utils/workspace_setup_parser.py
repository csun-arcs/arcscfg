import re
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("arcscfg")

def parse_setup_bash(setup_bash_path: Path) -> Optional[str]:
    """
    Parse the setup.bash file to extract the last underlay in the build chain
    (the second-last COLCON_CURRENT_PREFIX entry in the setup file).

    Args:
        setup_bash_path (Path): Path to the setup.bash file.

    Returns:
        Optional[str]: The inferred underlay path if found, else None.
    """
    if not setup_bash_path.exists():
        logger.warning(f"Setup file does not exist: {setup_bash_path}")
        return None

    colcon_prefix_pattern = re.compile(r'^COLCON_CURRENT_PREFIX="(.+)"$')
    prefixes = []

    try:
        with setup_bash_path.open('r') as file:
            for line in file:
                match = colcon_prefix_pattern.match(line.strip())
                if match:
                    prefixes.append(match.group(1))

        if len(prefixes) >= 2:
            default_underlay = prefixes[-2]
            logger.debug(f"Inferred default underlay before stripping: "
                         f"{default_underlay}")

            # Strip '/install' or '/devel' only if present at the end
            if default_underlay.endswith(('/install', '/devel')):
                stripped_underlay = Path(default_underlay).parent
                default_underlay_str = str(stripped_underlay)
                logger.debug(f"Inferred default underlay after stripping: "
                             f"{default_underlay_str}")
            else:
                # Retain the original path if no stripping is needed
                default_underlay_str = default_underlay
                logger.debug(f"Inferred default underlay without stripping: "
                             f"{default_underlay_str}")

            return default_underlay_str
        else:
            logger.warning("Not enough COLCON_CURRENT_PREFIX entries found.")
            return None

    except Exception as e:
        logger.error(f"Error parsing setup.bash: {e}")
        return None
