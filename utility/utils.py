import subprocess
import os
from pathlib import Path

try:
    from utility.logger import logger
except:
    print('++Using local logger.++')


def clone_repo(config: dict, depth: int = 1) -> None:
    """Clone HEP benchmark suite repository with specified configuration.

    Parameters
    ----------
    config : dict
        Configuration dictionary containing General settings with suite_version
    depth : int, optional
        Git clone depth parameter, by default 1 for shallow clone

    Returns
    -------
    None

    Raises
    ------
    subprocess.CalledProcessError
        If git clone operation fails
    SystemExit
        If clone operation fails, exits with git command return code

    Notes
    -----
    Uses environment variables to prevent git from prompting for credentials:
    - GIT_TERMINAL_PROMPT=0
    - GIT_ASKPASS=echo
    """
    repo_url = 'https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite.git'

    clone_cmd = ['git', 'clone', '--branch', config["General"]["suite_version"]]
    if depth is not None:
        clone_cmd += ["--depth", str(depth)]
    clone_cmd += [repo_url]
    logger.debug(f'[install] Cloning {repo_url}@{config["General"]["suite_version"]} with command: {clone_cmd}')

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"  # never prompt on TTY
    env["GIT_ASKPASS"] = "echo"  # a no-op askpass program

    try:
        subprocess.run(clone_cmd, check=True, env=env)
        logger.info(f'[install] Cloned {repo_url}@{config["General"]["suite_version"]}.')
    except subprocess.CalledProcessError as e:
        logger.error(f'[install] Error during git clone: {e}')
        exit(e.returncode)


def get_run_command(config) -> list:
    """Function to generate the run command for hepscore."""
    return [
        config["HEPscore"]["script"],
        '-s', config["HEPscore"]["site"],
        '-r',
        '-b ', config["HEPscore"]["plugins"],
        config["HEPscore"]["others"],  # to add other stuff/flags without code changes
    ]


def run_command(command: list) -> int:
    """Function to run a given command as subprocess. Returns the exit code"""
    logger.debug(f'[run_command] Running command: {command}')
    try:
        result = subprocess.run(command, check=True, capture_output=True)
        logger.debug(f'[run_command] Command completed with exit code {result.returncode}.')
        return result.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f'[run_command] Command failed with exit code {e.returncode}.')
        return e.returncode


def verify_installation() -> set[str, str] or None:
    """
    Verifies the installation of the HEPscore benchmark suite by checking the existence of necessary
    directories and files. This function checks if the required suite directory, work directory, and
    installation directory for the HEPscore package exist in the parent directory relative to the
    script's location. If any checks fail, it logs appropriate error messages and returns None. If all
    checks succeed, it returns paths to the script directory and the HEPscore configuration directory.

    :raises FileNotFoundError: Raised if specific directories (suite, workdir, or installation) are
        missing but not explicitly described in detail here.
    :raises ValueError: Raised if no Python version-specific directory is found within the work directory.

    :return: A tuple containing the path to the `run_HEPscore.sh` script and the hepscore configuration
        for the HEPscore benchmark suite.
    :rtype: set[str, str] or None
    """
    parent_dir = Path(__file__).resolve().parent.parent  # relative to the script!!
    logger.debug(f'[verify_installation] Parent directory: {parent_dir}')
    suite_dir = parent_dir / 'hep-benchmark-suite'
    script_dir = parent_dir / 'hep-benchmark-suite' / 'examples' / 'hepscore'
    workdir = parent_dir / 'workdir'
    pydir = workdir / 'env_bmk' / 'lib'
    python_dirs = list(pydir.glob('python3.*'))
    if not python_dirs:
        logger.error(f'[verify_installation] No Python version-specific directory (e.g., python3.x) found in {pydir}.')
        logger.error('[verify_installation] Please run --install first! Exiting...')
        exit(1)
    python_dir = python_dirs[0]  # Assume the first match is the correct Python directory
    install_dir = python_dir / 'site-packages' / 'hepscore'

    # Check if hep-benchmark-suite exists in parent directory
    if not suite_dir.exists() or not suite_dir.is_dir():
        logger.error('[verify_installation] hep-benchmark-suite directory not found in the parent directory.')
        logger.error('[verify_installation] Please run --install first! Exiting...')
        exit(1)
    else:
        logger.debug(f'[verify_installation] suite directory found: {suite_dir}')

    # Check if the workdir exists
    if not workdir.exists() or not workdir.is_dir():
        logger.error('[verify_installation] workdir not found in the parent directory.')
        logger.error('[verify_installation] Please run --install first! Exiting...')
        exit(1)
    else:
        logger.debug(f'[verify_installation] workdir found: {workdir}')

    # Check if hepscore is installed
    if not install_dir.exists() or not install_dir.is_dir():
        logger.error('[verify_installation] env_bmk directory not found in the expected path.')
        logger.error('[verify_installation] Please run --install first! Exiting...')
        exit(1)
    else:
        logger.debug(f'[verify_installation] install_dir found: {install_dir}')

    # Both directories exist
    logger.debug(f'[verify_installation] Hepscore installation identified in: {install_dir}')
    return str(script_dir), str(install_dir / 'etc')  # Returns script and hepscore cfg
    # TODO: maybe generalize the config?


if __name__ == "__main__":
    from logger import logger

    config = {'General': {'workload': 'TEST', 'iterations': '3', 'suite_version': 'BMK-1642'},
              'HEPscore': {'site': 'test', 'results_file': 'REPLACE_summary.json', 'gpu': 'true',
                           'wl_version': 'ci_v0.2', 'plugins': 'f,l,m,s,p,g,u,v', 'others': ''},
              'Scan': {'threads': '4', 'copies': '1,2'},
              'ExtraArgs': {'device': 'cuda', 'n-objects': '1000,5000,10000'}}

    script, config_dir = verify_installation()
    print(get_run_command(script, config_dir))
