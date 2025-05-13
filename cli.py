import argparse
import shutil
import subprocess

from shutil import copyfile
from pathlib import Path

from utility.init_fw import init_run_config
from utility.logger import logger
from utility.tasks import Task, TaskRunner
from utility.utils import verify_installation, clone_repo


def install(config) -> None:
    """
    Install HEPscore benchmark suite and configure it based on the provided configuration.

    Parameters
    ----------
    config : dict
        Configuration dictionary containing installation settings.
        Must include 'General' and 'HEPscore' sections with required parameters.

    Returns
    -------
    None

    Notes
    -----
    This function performs the following steps:
    1. Clones the HEP benchmark repository if not present
    2. Optionally replaces the run script with a template
    3. Installs HEPscore with site-specific configuration

    If the installation fails, the function will exit with an error code.

    The config dictionary must contain:
    - config["General"]["replace_script"] : bool, optional
        Whether to replace the run script with a template
    - config["HEPscore"]["site"] : str
        Site configuration name for HEPscore installation
    """
    if not Path('./hep-benchmark-suite').is_dir():
        clone_repo(config=config)

    # Replace the run_HEPscore.sh script with a template, if configured
    if config["General"].get('replace_script', False):
        src = Path('./config/run_HEPscore.template')
        dst = Path('./hep-benchmark-suite/examples/hepscore/run_HEPscore.sh')
        try:
            copyfile(src, dst)
            logger.info(f'[cli:install] Replaced run_HEPscore.sh with template from {src}.')
        except Exception as e:
            logger.error(f'[cli:install] Failed to copy run_HEPscore.template: {e}')
            raise

    # Install hepscore
    install_cmd = [
        './hep-benchmark-suite/examples/hepscore/run_HEPscore.sh',
        '-s', config["HEPscore"]["site"],
        '-i'
    ]
    logger.info(f'[cli:install] Installing hepscore.')
    try:
        subprocess.run(install_cmd, check=True)
        logger.info(f'[cli:install] Done.')
    except subprocess.CalledProcessError as e:
        logger.error(f'[cli:install] Error during hepscore installation: {e}')
        exit(e.returncode)


def delete(task) -> None:
    """Delete a certain task. Can also be used to start from scratch, if 'runs' is selected."""
    if Path(task).is_dir():
        logger.warning(f'[cli:delete] ++WARNING++ {task} will be deleted.')
        inp = input('Are you sure you want to proceed? This may will require a new init! [y/N]')
        if inp.lower() == 'y':
            logger.info(f'[cli:delete] Deleting {task}.')
            shutil.rmtree(task)
            logger.info('[cli:delete] Deleting complete.')
    else:
        logger.error(f'[cli:delete] {task} is not a valid task.')


def reset(task) -> None:
    """Reset the benchmark progress. Can be used to start from scratch, if 'runs' is selected."""

    def clean_dir(task_dir):
        for item in task_dir.iterdir():
            if item.is_file():
                # Delete log and status files, keep configs
                if str(item).split('/')[-1] == 'config.yaml':
                    logger.info(f'[cli:reset] Preserving file: {item}')
                else:
                    logger.info(f'[cli:reset] Deleting file: {item}')
                    item.unlink()
            elif item.is_dir():
                clean_dir(item)
                logger.info(f'[cli:reset] Task {item} cleaned.')

    if task == 'runs':
        logger.warning('[cli:reset] ++WARNING++ With this, every progress will be deleted.')
        inp = input('Are you sure you want to reset all benchmark runs? This will require a new init! [y/N]')
        if inp.lower() == 'y':
            logger.info('[cli:reset] Benchmark runs will be reset.')
            # Remove 'runs' directory
            runs_dir = Path('./runs')
            logger.info(f'[cli:reset] Resetting {runs_dir}.')
            clean_dir(runs_dir)
            logger.info('[cli:reset] Reset complete.')
        else:
            logger.info('[cli:reset] Aborting reset.')
    else:
        # Check if task is a directory
        if Path(task).is_dir():
            logger.warning(f'[cli:reset] ++WARNING++ {task} progress will be deleted.')
            inp = input('Are you sure you want to proceed? [y/N]')
            if inp.lower() == 'y':
                logger.info(f'[cli:reset] Resetting {task}.')
                task_dir = Path(task)
                # Iterate through the directory and apply the filter
                clean_dir(task_dir)
        else:
            logger.error(f'[cli:reset] {task} is not a valid task.')
            logger.info('[cli:reset] Aborting reset.')


def print_status(runner: TaskRunner) -> None:
    """
    Prints the status of configurations and their respective runs contained within
    a 'runs/' directory. It checks each run's directory for specific status files
    ('SUCCESS', 'FAILED') to determine the overall status of that run. The statuses
    are categorized as 'SUCCESS', 'FAILED', or 'PENDING'.

    This function expects a specific directory structure within 'runs/' where each
    subdirectory represents a configuration, containing subsequent subdirectories
    with run information.

    :return: None
    """

    logger.info('[cli:print_status] Printing status of benchmark runs.')
    logger.debug(f'[cli:print_status] TaskRunner: {runner.tasks}')
    if not Path(runner.tasks_dir).exists():
        logger.error('No runs directory found (expected "runs"/).')
        return

    def show_status(task: Task, indent: str = '') -> None:
        if task.status == 'SUCCESS':
            print(f'{indent}✅  {str(task.name)} (SUCCESS)')
        elif task.status == 'FAILED':
            print(f'{indent}❌  {str(task.name)} (FAILED)')
        else:
            print(f'{indent}🕒 {str(task.name)} (PENDING)')

    # Check for tasks in ./runs and print parent tasks and the subtasks as their dependencies
    for task in runner.tasks:
        if task.is_parent:
            show_status(task)
            for subtask in task.dependencies:
                show_status(subtask, '   |--- ')


def push(config):
    # TODO: implement push to DB
    pass


def run(runner, dry_run) -> int:
    status_code = 1
    logger.info('[cli:run] Starting TaskRunner.')
    if dry_run:
        logger.info('[cli:run] Dry-run mode enabled. No actual runs will be performed.')
        return 0
    try:
        status_code = runner.run()
    except Exception as e:
        logger.error(f'[cli:run] Error starting TaskRunner.run(): {e}')

    return status_code


def rerun(task: str = '') -> None:
    """Rerun the specified task."""
    # TODO: implement
    # Check that no run is ongoing
    # Reset the directory
    # Run task

    # if no task is specified: rerun all failed
    # Check directories for failed runs
    # reset the directory
    pass


def cli():
    parser = argparse.ArgumentParser(
        description='Manage and run hepscore benchmark workflows'
    )
    parser.add_argument('--print-status', action='store_true', help='Print benchmarks status')
    parser.add_argument('--dry-run', action='store_true', help='Starting without running benchmarks. For debugging purposes only.')
    parser.add_argument('--push', action='store_true', help='Push benchmark results')
    parser.add_argument('--rerun', action='store_true', help='Re-run benchmarks')
    parser.add_argument('--interactive', action='store_true', help='Run benchmarks interactively')
    parser.add_argument(
        '--task',
        nargs='?',
        default='runs',
        const='runs',
        help='Specify a task to run. If no task is specified, all tasks will be run.',
    )
    parser.add_argument(
        '--config',
        nargs='?',
        default='./config/config.ini',
        const='./config/config.ini',
        help='Initialize the specified config.',
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install the HEPscore benchmark suite with the specified version.',
    )
    parser.add_argument(
        '--run',
        nargs='?',  # optional
        default='',
        const='1',  # TODO check if logic works
        help='Run benchmarks sequentially. If a task is specified, only that task will be run.',
    )
    parser.add_argument(
        '--delete',
        nargs='?',
        default='',
        const='runs',
        help='Deletes EVERYTHING or a certain task, if specified.',
    )
    parser.add_argument(
        '--reset',
        nargs='?',  # optional
        default='',  # Default value when the argument is not provided
        const='runs',
        help='Reset benchmarks state or task. Optionally specify the task to reset.',
    )

    args = parser.parse_args()

    # Initialize based on config
    cfg = init_run_config(args.config)
    if not cfg:
        logger.error('[cli] Failed to initialize config. Exiting.')
        exit(1)

    # Install
    if args.install:
        install(cfg)
        logger.info('[cli] Installed successfully. Exiting...')
        exit(0)  # Exit after installation

    # Verify installation and add directories to cfg
    script_dir, cfg_dir = verify_installation()
    cfg["HEPscore"]["script_dir"] = script_dir
    cfg["HEPscore"]["script"] = script_dir + '/run_HEPscore.sh'
    cfg["HEPscore"]["cfg_dir"] = cfg_dir
    cfg["HEPscore"]["cfg"] = cfg_dir + '/hepscore-run.yaml'
    logger.debug(f'[cli] Config: {cfg._sections}')

    # Initialize the TaskRunner
    runner = TaskRunner(cfg, args.task)

    if args.print_status:
        print_status(runner)
    elif args.reset:
        reset(args.reset)
    elif args.delete:
        delete(args.delete)
    elif args.run:
        logger.info(f'[cli] Starting run...')
        run(runner, dry_run=args.dry_run)
    else:
        logger.error('[cli] Nothing specified. Use --help for more information. Exiting.')


if __name__ == "__main__":
    cli()

# TODO: delete function should cleanup everything
