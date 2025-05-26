import configparser
import itertools
from pathlib import Path

import yaml

from utility.logger import logger

# Static defaults
DEFAULT_SETTINGS = {
    'name': 'HEPscore_GPU',
    'reference_machine': 'Unknown',
    'registry': [
        'oras://gitlab-registry.cern.ch/hep-benchmarks/hep-workloads-sif',
        'docker://gitlab-registry.cern.ch/hep-benchmarks/hep-workloads',
        'dir:///cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/hep-benchmarks/hep-workloads'
    ],
    'addarch': True,
    'scaling': 1,
    'method': 'geometric_mean',
    'container_exec': 'singularity',
}


def _parse_list(raw: str):
    """If comma in raw, split+strip into a list; else return a single-element list."""
    return [item.strip() for item in raw.split(',')]


def init_run_config(ini_path: str, base_out_dir: str = 'runs') -> dict:
    """
    Initializes and processes configuration scans based on the input INI file and parameters.

    This function reads configuration data from the provided INI file, prepares combinations
    of scanning and extra argument parameters, and generates corresponding YAML configuration
    files in organized directories within the specified base output directory. It supports
    iterating over multiple parameter combinations, creating subdirectories for each iteration.

    :param ini_path: Path to the INI configuration file containing all required settings
                     such as general workload, iterations, HEPscore information, and
                     optional scan or extra arguments.
    :type ini_path: str
    :param base_out_dir: Directory where the generated configuration and subsequent
                         folder structure will be stored. Defaults to 'runs'.
    :type base_out_dir: str, optional
    :return: config as read in for extracting general information, such as 'suite_version'
    :rtype: dict
    """
    logger.info(f'[init_config_scans] Initialize...')

    cfg = configparser.ConfigParser()

    ini_path = Path(ini_path)
    if not ini_path.is_file():
        logger.error(f'[init_config_scans] File not found: {ini_path}')
        return {}

    cfg.read(ini_path)
    logger.debug(f'[init_config_scans] Config: {cfg._sections}')

    # General
    workload = cfg["General"]["workload"]
    iterations = cfg.getint('General', 'iterations', fallback=1)

    # HEPscore
    repetitions = cfg.getint('General', 'repetitions', fallback=1)
    raw_rs = cfg["HEPscore"]["results_file"]
    results_file = raw_rs.replace('<workload>', workload)
    gpu = cfg["HEPscore"].getboolean('gpu')
    wl_version = cfg["HEPscore"]["wl_version"]

    # Scan parameters
    scan_params = {}
    if cfg.has_section('Scan'):
        for key, raw in cfg["Scan"].items():
            vals = _parse_list(raw)
            scan_params[key] = [int(v) if v.isdigit() else v for v in vals]
    else:
        logger.error('[init_config_scans] No Scan section found in config.ini. Using defaults instead.')
        exit(1)

    # ExtraArgs parameters
    extra_params = {}
    if cfg.has_section('ExtraArgs'):
        for key, raw in cfg["ExtraArgs"].items():
            vals = _parse_list(raw)
            extra_params[key] = [int(v) if v.isdigit() else v for v in vals]

    # Prepare combinations
    scan_keys, scan_combos = (zip(*scan_params.items()) if scan_params else ([], [()]))
    extra_keys, extra_combos = (zip(*extra_params.items()) if extra_params else ([], [()]))

    # Base output dir: 'runs'
    base_out = Path(base_out_dir)
    base_out.mkdir(parents=True, exist_ok=True)

    # Iterate over all parameter combinations
    for scan_vals in itertools.product(*scan_combos):
        scan_args = dict(zip(scan_keys, scan_vals)) if scan_keys else {}
        for extra_vals in itertools.product(*extra_combos):
            extra_dict = dict(zip(extra_keys, extra_vals)) if extra_keys else {}

            # Build extra-args string
            extra_args_str = ''
            if extra_dict:
                parts = [f'--{k} {v}' for k, v in extra_dict.items()]
                extra_args_str = ' '.join(parts)

            # Full config dict
            full_cfg = {
                'hepscore': {
                    'benchmarks': {
                        workload: {
                            'results_file': results_file,
                            'gpu': gpu,
                            'ref_scores': {workload: 1},
                            'version': wl_version,
                            'args': {**scan_args, 'extra-args': extra_args_str}
                        }
                    },
                    'settings': {**DEFAULT_SETTINGS, 'repetitions': repetitions}
                }
            }

            # Directory for this combination
            frag_parts = [f'{k}-{v}' for k, v in scan_args.items()]
            frag_parts += [f'{k}-{v}' for k, v in extra_dict.items()]
            frag = '_'.join(frag_parts) if frag_parts else workload
            combo_dir = base_out / (f'{workload}_{frag}' if frag else workload)
            combo_dir.mkdir(parents=True, exist_ok=True)

            # Write YAML in combo_dir
            filename = f'config.yaml'
            target = combo_dir / filename
            with target.open('w') as f:
                yaml.safe_dump(full_cfg, f, sort_keys=False)

            # Create iteration subfolders
            for i in range(iterations):
                iter_dir = combo_dir / f'run_{i}'
                iter_dir.mkdir(exist_ok=True)

            # Print relative path
            logger.debug(f'→ Wrote config and created {iterations} runs in {combo_dir}')
    return cfg

if __name__ == "__main__":
    import sys

    ini = sys.argv[1] if len(sys.argv) > 1 else "./config/config.ini"
    init_run_config(ini)
