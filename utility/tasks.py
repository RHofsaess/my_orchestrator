from shutil import copyfile
from pathlib import Path

from utility.lock import Lock

try:
    from utility.logger import logger
except:
    print('++Using local logger.++')


class Task:
    def __init__(self, config, name, run_fn, dependencies=None):
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
        # If in task directory SUCCESS or FAILED file exists, set status accordingly and completed=true
        logger.debug(f'[Task:check_status] Check status of >>{self.name}<<.')
        if Path(self.name, 'SUCCESS').exists() or Path(self.name, 'FAILED').exists():
            self.completed = True
            if Path(self.name, 'SUCCESS').exists():
                self.status = 'SUCCESS'
            else:
                self.status = 'FAILED'
        logger.info(f'[Task:check_status] Full status of >>{self.name}<<: {self.__str__()}')

    def run(self):
        """
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
            self.status == 'FAILED'
            # Create file in run directory
            Path(self.name, 'FAILED').touch()
        else:
            logger.info(f'[Task:run] Task >>{self.name}<< ran successfully.')
            self.completed = True
            self.status = 'SUCCESS'
            # Create file in run directory
            Path(self.name, 'SUCCESS').touch()


class TaskRunner:
    def __init__(self):
        self.tasks = []
        self.running_task = None

    def add_task(self, task):
        self.tasks.append(task)

    def run(self):
        if not Lock.acquire():
            logger.error(f'[TaskRunner] Another instance is already running. Exiting.')
            return

        try:
            for task in self.tasks:
                for dependency in task.dependencies:
                    if not dependency.completed:
                        print(f"Waiting for dependency `{dependency.name}` to complete...")
                        dependency.run()

                self.running_task = task
                task.run()
                self.running_task = None
        finally:
            Lock.release()


def create_tasks(base_directory: str):
    """
    Creates tasks dynamically from the given directory structure using pathlib.

    Args:
        base_directory (str): The base directory to scan for task creation.

    Returns:
        list[Task]: A list of dynamically created Task objects.
    """
    # To store tasks by directory (for dependency resolution)
    tasks = {}

    # Convert base_directory to a Path object
    base_dir = Path(base_directory)

    # Walk through directories
    # TODO: only bottom directories should be tasks (run_0, run_1, etc)
    for dir_path in base_dir.rglob("*"):
        if dir_path.is_dir():
            task_name = dir_path

            # Define what the task will do (this can be customized as needed)
            def run_fn(working_dir=dir_path):
                # Copy config file to cfg_dir
                # TODO
                print(f"Processing directory: {working_dir}")
                for file_path in working_dir.iterdir():
                    if file_path.is_file():
                        print(f"Handling file: {file_path}")

            # Identify dependencies (a directory's dependencies could be its parent directory)
            parent_dir = dir_path.parent
            dependencies = []
            if str(parent_dir) in tasks:  # Link to the parent's task
                dependencies.append(tasks[str(parent_dir)])

            # Create the task and add it to the dictionary
            tasks[str(dir_path)] = Task(name=task_name, run_fn=run_fn, dependencies=dependencies)

    return list(tasks.values())  # Return all tasks as a list



def setup_runner(tasks):
    runner = TaskRunner(tasks)
    return runner

#     for task in tasks:
#         runner.add_task(task)



if __name__ == "__main__":
    from logger import logger
    config = {'General': {'workload': 'TEST', 'iterations': '3', 'suite_version': 'BMK-1642'}, 'HEPscore': {'site': 'test', 'results_file': 'REPLACE_summary.json', 'gpu': 'true', 'wl_version': 'ci_v0.2', 'plugins': 'f,l,m,s,p,g,u,v', 'others': ''}, 'Scan': {'threads': '4', 'copies': '1,2'}, 'ExtraArgs': {'device': 'cuda', 'n-objects': '1000,5000,10000'}}
    print(create_tasks('../runs'))
