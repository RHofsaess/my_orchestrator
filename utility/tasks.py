from shutil import copyfile
from pathlib import Path

from utility.lock import Lock
from utility.utils import get_run_command, run_command

try:
    from utility.logger import logger
except:
    print('++Using local logger.++')


class Task:
    def __init__(self, config, name, run_fn, dependencies=None, is_parent=False):
        """
        Initialize a task.

        Args:
            name (str): Name of the task: full path.
            run_fn (callable): Function to execute when the task is run. The function has to return an exit code.
            dependencies (list[Task]): List of other tasks that must be completed before this one.
        """
        # Check if 'name' is a configured task path
        if Path(name).exists() and str(Path(name)).startswith('runs/'):
            self.name = name
        else:
            raise ValueError(f'The "name" parameter must be a valid task path in "runs/". Received: {name}')

        if not callable(run_fn):
            raise ValueError('The "run_fn" must be a callable function.')
        else:
            self.run_fn = run_fn

        self.config = config
        self.is_parent=is_parent
        self.dependencies = dependencies if dependencies else []  # Here, all below and before should be listed
        self.exit_code = None
        self.status = None
        self.completed = False
        self.check_status()

    def __str__(self):
        return f'Task(name={self.name}, status={self.status}, completed={self.completed}, dependencies={self.dependencies})'

    def copy_config(self):
        """Copy configuration files from parent directory to run directory and HEPscore config directory.
    
        The method copies the config.yaml file from the parent directory to two locations:
        1. The task's run directory as 'used_cfg.yaml'
        2. The HEPscore configuration directory specified in the config
    
        Notes
        -----
        The method will log debug messages for successful copies and error messages for failed copies.
    
        Raises
        ------
        Exception
            If copying files fails due to file system errors or permissions
        """
        # copy from parent to run_X and cfg_dir
        parent_dir = Path(self.name).resolve().parent
        logger.debug(f'[Task:copy_config] Copying config from {parent_dir} to {self.name} and {self.config["HEPscore"]["cfg_dir"]}.')
        src = parent_dir / 'config.yaml'
        dst_run = Path(self.name)/'used_cfg.yaml'
        dst_hepscore = Path(self.config["HEPscore"]["cfg_dir"]) / self.config["HEPscore"]["run_config"]
        try:
            copyfile(src, dst_run)
            logger.debug(f'[Task:copy_config] Copied config: {src} -> {dst_run}.')
        except Exception as e:
            logger.error(f'[Task:copy_config] Failed to copy config from {src} to {dst_run}: {e}')
        try:
            copyfile(src, dst_hepscore)
            logger.debug(f'[Task:copy_config] Copied config: {src} -> {dst_hepscore}.')
        except Exception as e:
            logger.error(f'[Task:copy_config] Failed to copy config from {src} to {dst_hepscore}: {e}')

    def check_status(self):
        """
        Check the current status of a task and its dependencies based on the filesystem and set it accordingly in the task object.

        This method evaluates whether the task and its dependencies (if present) have
        been completed successfully or have failed. It uses file-based markers
        ("SUCCESS" or "FAILED") available in the task's directory to determine the
        status of each task. For a parent task, the status of each dependency influences
        the overall status of the parent task.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        None
        """
        logger.debug(f'[Task:check_status] Check status of >>{self.name}<<.')
        if self.is_parent:
            for dependency in self.dependencies:
                check_status(dependency)
                if not dependency.completed or dependency.status != 'SUCCESS':
                    logger.debug(f'[Task:check_status] Dependency >>{dependency.name}<< not completed.')
                    self.completed = False
                    break
                self.completed = True
        else:
            if self.completed:  # Avoid double-checking
                pass
            if Path(self.name, 'SUCCESS').exists():
                self.status = 'SUCCESS'
                self.completed = True
                logger.debug(f'[Task:check_status] Task >>{self.name}<< completed successfully.')
            elif Path(self.name, 'FAILED').exists():
                self.status = 'FAILED'
                self.completed = True
                logger.debug(f'[Task:check_status] Task >>{self.name}<< failed.')
            else:
                logger.debug(f'[Task:check_status] Task >>{self.name}<< not completed.')
                self.completed = False
        logger.debug(f'[Task:check_status] Full status of >>{self.name}<<: {self.__str__()}')


    def run(self):
        """
        Basic function to run a task.
        Run the task, ensuring it hasn't already been completed.
        After finishing, mark it as completed by creating SUCCESS or FAILED file in the task's directory.
        """
        if self.completed:
            if self.status == 'FAILED':
                logger.info(f'[Task:run] Task >>{self.name}<< already completed with status FAILED. Use --rerun to retry.') # TODO --rerun to be implemented
            else:
                logger.info(f'[Task:run] Task >>{self.name}<< already completed successfully. Skipping.')
            return

        logger.info(f'[Task:run] Starting task >>{self.name}<<...')
        try:
            # copy local config
            self.copy_config()
            
            # Execute the task's run function
            return_code = self.run_fn()
        except Exception as e:
            logger.error(f'Task >>{self.name}<< failed with exception: {e}. Exiting')
            exit(1)  # TODO: Check if necessary!

        if return_code != 0:
            logger.error(f'[Task:run] Task >>{self.name}<< failed.')
            self.completed = True
            self.status = 'FAILED'
            # Create file in run directory
            Path(self.name, 'FAILED').touch()
        else:
            logger.info(f'[Task:run] Task >>{self.name}<< ran successfully.')
            self.completed = True
            self.status = 'SUCCESS'
            # Create file in run directory
            Path(self.name, 'SUCCESS').touch()


class TaskRunner:
    def __init__(self, config, tasks_directory='./runs'):
        if 'runs/' not in tasks_directory:
            exit('Not a valid task directory. Please specify a task withing "runs/". Exiting.')
        else:
            self.tasks_dir = tasks_directory
        self.config = config
        self.tasks = []
        self.running_task = None

        # Create the tasks dynamically from the task directory structure
        self.create_tasks()

    def create_tasks(self) -> None:
        """
        Creates tasks dynamically from the given directory structure using pathlib.

        Returns:
            None
        """
        if not Path(self.tasks_dir).exists():
            raise ValueError(f"Tasks directory {self.tasks_dir} does not exist.")
        logger.debug(f'[TaskRunner:create_tasks] Creating tasks for: {self.tasks_dir}')

        # Check if single task
        if not any(Path(self.tasks_dir).rglob("*")) and 'run' in self.tasks_dir:
            logger.debug(f'[TaskRunner:create_tasks] Creating task: {self.tasks_dir}')
            task = Task(
                config=self.config,
                name=self.tasks_dir,
                run_fn=lambda: run_command(get_run_command(self.config)),
            )
            self.tasks.append(task)
        else:  # Parent task
            logger.debug(f'[TaskRunner:create_tasks] Creating parent tasks')
            task = Task(
                config=self.config,
                name=self.tasks_dir,
                run_fn=lambda: None,
                is_parent=True,
            )

        # Walk through directories
        for task_path in Path(self.tasks_dir).rglob("*"):
            logger.debug(f'[TaskRunner:create_tasks] Checking task: {task_path}')
            # If subdirs exist, create parent task
            if task_path.is_dir():  # Ensure task_path is a directory
                if any(sub_task.is_dir() for sub_task in task_path.iterdir()):
                    logger.debug(f'[TaskRunner:create_tasks] Creating parent task: {task_path}')
                    task = Task(
                        config=self.config,
                        name=str(task_path),
                        run_fn=lambda: None,
                        is_parent=True,
                    )
                else:
                    logger.debug(f'[TaskRunner:create_tasks] Creating task: {task_path}')
                    task = Task(
                        config=self.config,
                        name=str(task_path),
                        run_fn=lambda: run_command(get_run_command(self.config)),
                    )
                logger.debug(f'Appending: {task}')
                self.tasks.append(task)

        # Set dependencies
        logger.info(f'[TaskRunner:create_tasks] Creating dependencies...')
        for task in self.tasks:
            logger.debug(f'[TaskRunner:create_tasks] Task is parent: {task.is_parent}')
            if task.is_parent:
                logger.debug(f'[TaskRunner:create_tasks] Generating dependencies for {task.name}...')
                # Set dependencies for parent task
                subdirectories = [sub for sub in Path(task.name).iterdir() if sub.is_dir()]
                task.dependencies = [subtask for subtask in self.tasks if Path(subtask.name) in subdirectories]

        logger.info(f'[TaskRunner:create_tasks] Created {len(self.tasks)} tasks.')
        logger.debug(f'[TaskRunner:create_tasks] Task list:\n{[str(task) for task in self.tasks]}')

        return None

    def run(self) -> int:
        if not Lock.acquire():
            logger.error(f'[TaskRunner] Another instance is already running. Exiting.')
            return 1

        try:
            for task in self.tasks:
                if not task.dependencies:
                    self.running_task = task
                    task.run()
                    self.running_task = None
                else:  # Parent tasks
                    for dependency in task.dependencies:
                        if not dependency.completed:
                            logger.info(f'Running dependent task: {dependency.name}')
                            dependency.run()
        finally:
            Lock.release()

        return 0



if __name__ == "__main__":
    config = {'General': {'workload': 'TEST', 'iterations': '3', 'suite_version': 'BMK-1642'}, 'HEPscore': {'site': 'test', 'results_file': 'REPLACE_summary.json', 'gpu': 'true', 'wl_version': 'ci_v0.2', 'plugins': 'f,l,m,s,p,g,u,v', 'others': ''}, 'Scan': {'threads': '4', 'copies': '1,2'}, 'ExtraArgs': {'device': 'cuda', 'n-objects': '1000,5000,10000'}}
    run_tasks = TaskRunner(config)
    run_tasks.run()






