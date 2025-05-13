import argparse
import shutil
import subprocess
import os

from shutil import copyfile
from pathlib import Path

from utility.init_fw import init_run_config
from utility.logger import logger
from utility.tasks import Task, TaskRunner
from utility.utils import verify_installation, get_run_command, run_command, clone_repo


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
            logger.info(f'[install] Replaced run_HEPscore.sh with template from {src}.')
        except Exception as e:
            logger.error(f'[install] Failed to copy run_HEPscore.template: {e}')
            raise

    # Install hepscore
    install_cmd = [
        './hep-benchmark-suite/examples/hepscore/run_HEPscore.sh',
        '-s', config["HEPscore"]["site"],
        '-i'
    ]
    logger.info(f'[install] Installing hepscore.')
    try:
        subprocess.run(install_cmd, check=True)
        logger.info(f'[install] Done.')
    except subprocess.CalledProcessError as e:
        logger.error(f'[install] Error during hepscore installation: {e}')
        exit(e.returncode)


def delete(task) -> None:
    """Delete a certain task. Can also be used to start from scratch, if 'runs' is selected."""
    if Path(task).is_dir():
        logger.warning(f'[delete] ++WARNING++ {task} will be deleted.')
        inp = input('Are you sure you want to proceed? This may will require a new init! [y/N]')
        if inp.lower() == 'y':
            logger.info(f'[delete] Deleting {task}.')
            shutil.rmtree(task)
            logger.info('[delete] Deleting complete.')
    else:
        logger.error(f'[delete] {task} is not a valid task.')


def reset(task) -> None:
    """Reset the benchmark progress. Can be used to start from scratch, if 'runs' is selected."""

    def clean_dir(task_dir):
        for item in task_dir.iterdir():
            if item.is_file():
                # Delete log and status files, keep configs
                if str(item).split('/')[-1] == 'config.yaml':
                    logger.info(f'[reset] Preserving file: {item}')
                else:
                    logger.info(f'[reset] Deleting file: {item}')
                    item.unlink()
            elif item.is_dir():
                clean_dir(item)
                logger.info(f'[reset] Task {item} cleaned.')

    if task == 'runs':
        logger.warning('[reset] ++WARNING++ With this, every progress will be deleted.')
        inp = input('Are you sure you want to reset all benchmark runs? This will require a new init! [y/N]')
        if inp.lower() == 'y':
            logger.info('[reset] Benchmark runs will be reset.')
            # Remove 'runs' directory
            runs_dir = Path('./runs')
            logger.info(f'[reset] Resetting {runs_dir}.')
            clean_dir(runs_dir)
            logger.info('[reset] Reset complete.')
        else:
            logger.info('[reset] Aborting reset.')
    else:
        # Check if task is a directory
        if Path(task).is_dir():
            logger.warning(f'[reset] ++WARNING++ {task} progress will be deleted.')
            inp = input('Are you sure you want to proceed? [y/N]')
            if inp.lower() == 'y':
                logger.info(f'[reset] Resetting {task}.')
                task_dir = Path(task)
                # Iterate through the directory and apply the filter
                clean_dir(task_dir)
        else:
            logger.error(f'[reset] {task} is not a valid task.')
            logger.info('[reset] Aborting reset.')


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

    logger.info('[print_status] Printing status of benchmark runs.')
    logger.debug(f'[print_status] TaskRunner: {runner.tasks}')
    base_dir = Path('./runs')
    if not base_dir.exists():
        logger.error('No runs directory found (expected "runs"/).')
        return

    def show_status(task: Task, indent: str = '') -> None:
        if task.status == 'SUCCESS':
            print(f'{indent}✅ {task.name} (SUCCESS)')
        elif task.status == 'FAILED':
            print(f'{indent}❌ {task.name} (FAILED)')
        else:
            print(f'{indent}🕒 {task.name} (PENDING)')

    # Check for tasks in ./runs and print parent tasks and the subtasks as their dependencies
    for task in runner.tasks:
        if task.is_parent:
            show_status(task)
            for subtask in task.dependencies:
                show_status(subtask, '   |--- ')

    """
    logger.info('[print_status] Printing status of benchmark runs.')
    base_dir = Path('./runs')
    if not base_dir.exists():
        logger.error('No runs directory found (expected "runs"/).')
        return

    for combo in sorted(base_dir.iterdir()):
        if not combo.is_dir():
            continue
        print(f"Configuration: {combo.name}")
        # list iteration subdirs and their status
        run_dirs = [d for d in sorted(combo.iterdir()) if d.is_dir() and d.name.startswith('run_')]
        if not run_dirs:
            print("  (no iterations found)")
            continue
        for run_dir in run_dirs:
            success_file = run_dir / 'SUCCESS'
            failed_file = run_dir / 'FAILED'
            if success_file.exists():
                status = '✅  SUCCESS'
            elif failed_file.exists():
                status = '❌ FAILED'
            else:
                status = '🕒 PENDING'
            print(f"  {run_dir.name}: {status}")
    """

def push(config):
    # TODO: implement push to DB
    pass


def run(config, task: str = None, ) -> None:
    # Check that no run is ongoing # TODO HOW TO CHECK IF RUNNING?
    # If a task is specified to run, create this one task and run it without the task runner
    if task:
        # If a task is specified, create and run it
        t = Task(config=config, name=task, run_fn=lambda: run_command(get_run_command(config)))
        t.run()
    else:
        # No task specified; create tasks for entire 'runs' directory

        # Initialize TaskRunner

        # create_tasks('./runs')
        logger.info('[run] Created tasks and start full run.')
        # Start run
        # TODO


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
    parser.add_argument('--push', action='store_true', help='Push benchmark results')
    parser.add_argument('--rerun', action='store_true', help='Re-run benchmarks')
    parser.add_argument('--interactive', action='store_true', help='Run benchmarks interactively')
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
        const='',  # TODO check if logic works
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
        logger.error('Failed to initialize config. Exiting.')
        exit(1)

    # Install
    if args.install:
        install(cfg)
        logger.info('[install] Installed successfully. Exiting...')
        exit(0)  # Exit after installation

    # Verify installation and add directories to cfg
    script_dir, cfg_dir = verify_installation()
    cfg["HEPscore"]["script_dir"] = script_dir
    cfg["HEPscore"]["script"] = script_dir + '/run_HEPscore.sh'
    cfg["HEPscore"]["cfg_dir"] = cfg_dir
    cfg["HEPscore"]["cfg"] = cfg_dir + '/hepscore-run.yaml'
    logger.debug(f'[cli] Config: {cfg._sections}')

    # Initialize the TaskRunner
    runner = TaskRunner(cfg)

    if args.print_status:
        print_status(runner)
    elif args.reset:
        reset(args.reset)
    elif args.delete:
        delete(args.delete)
    elif args.run:
        run(config=cfg, task=args.run)
        pass
        # TODO
    else:
        logger.error('Nothing specified. Use --help for more information. Exiting.')


if __name__ == "__main__":
    cli()

# TODO: delete function should cleanup everything
