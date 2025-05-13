import os

from utility.logger import logger

LOCK_FILE = '/tmp/task_runner.lock'


class Lock:
    def __init__(self, task_name):
        self.running_process = task_name

    @staticmethod
    def acquire(self):
        """
        Acquire a global lock. Returns True if successful, False if lock exists.
        """
        logger.debug(f'[lock] Acquiring lock...')
        if os.path.exists(LOCK_FILE):
            logger.debug(f'[lock] Acquiring lock FAILED.')
            return False

        with open(LOCK_FILE, 'w') as lock:
            lock.write(self.running_process)
        return True

    @staticmethod
    def release():
        """
        Release the global lock by removing the lock file.
        """
        if os.path.exists(LOCK_FILE):
            logger.debug(f'[lock] Releasing lock...')
            os.remove(LOCK_FILE)
