import subprocess
from pathlib import Path

try:
    from utility.logger import logger
except:
    print('++Using local logger.++')


def get_run_command(script: str, config) -> list:
    """Function to generate the run command for hepscore"""
    return [
        script,
        '-s', config["HEPscore"]["site"],
        '-b ', config["HEPscore"]["plugins"],
        config["HEPscore"]["others"],  # to add other stuff/flags without code changes
        '-r'
    ]


def run_command(command: list) -> int:
    """Function to run the HEPscrore example script with the given command."""
    logger.debug(f'[run_command] Running command: {command}')
    try:
        result = subprocess.run(command, check=True, capture_output=True)
        logger.debug(f'[run_command] Command completed with exit code {result.returncode}.')
        return result.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f'[run_command] Command failed with exit code {e.returncode}.')


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

    :return: A tuple containing the path to the `run_HEPscore.sh` script and the configuration directory
        for the HEPscore benchmark suite or None if any of the checks fail.
    :rtype: set[str, str] or None
    """
    # Check if hepscore-benchmark-suite directory exists in parent directory
    # Check if workdir exists
    # Check installation

    parent_dir = Path(__file__).resolve().parent.parent  # relative to the script!!
    logger.debug(f'[identify_installation] Parent directory: {parent_dir}')
    suite_dir = parent_dir / 'hep-benchmark-suite'
    script_dir = parent_dir / 'hep-benchmark-suite' / 'examples' / 'hepscore' / 'run_HEPscore.sh'
    workdir = parent_dir / 'workdir'
    pydir = workdir / 'env_bmk' / 'lib'
    python_dirs = list(pydir.glob('python3.*'))
    if not python_dirs:
        logger.error(f'No Python version-specific directory (e.g., python3.x) found in {pydir}.')
        return None
    python_dir = python_dirs[0]  # Assume the first match is the correct Python directory
    install_dir = python_dir / 'site-packages' / 'hepscore'

    # Check if hep-benchmark-suite exists
    if not suite_dir.exists() or not suite_dir.is_dir():
        logger.error('[identify_installation] hep-benchmark-suite directory not found in the parent directory.')
        logger.error('[identify_installation] Please run --install first! Exiting...')
        return None
    else:
        logger.debug(f'[identify_installation] suite directory found: {suite_dir}')

    # Check if the workdir exists
    if not workdir.exists() or not workdir.is_dir():
        logger.error('[identify_installation] workdir not found in the parent directory.')
        logger.error('[identify_installation] Please run --install first! Exiting...')
        return None
    else:
        logger.debug(f'[identify_installation] workdir found: {workdir}')

    # Check if hepscore is installed
    if not install_dir.exists() or not install_dir.is_dir():
        logger.error('[identify_installation] env_bmk directory not found in the expected path.')
        return None
    else:
        logger.debug(f'[identify_installation] install_dir found: {install_dir}')

    # Both directories exist
    logger.debug(f'Hepscore installation identified in: {install_dir}')
    return str(script_dir), str(install_dir / 'etc')  # Returns script dir and hepscore cfg dir


if __name__ == "__main__":
    from logger import logger

    config = {'General': {'workload': 'TEST', 'iterations': '3', 'suite_version': 'BMK-1642'},
              'HEPscore': {'site': 'test', 'results_file': 'REPLACE_summary.json', 'gpu': 'true',
                           'wl_version': 'ci_v0.2', 'plugins': 'f,l,m,s,p,g,u,v', 'others': ''},
              'Scan': {'threads': '4', 'copies': '1,2'},
              'ExtraArgs': {'device': 'cuda', 'n-objects': '1000,5000,10000'}}

    script_dir, config_dir = verify_installation()
    print(get_run_command(script_dir, config))
