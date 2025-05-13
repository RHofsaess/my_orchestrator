import os

from utility.logger import logger

LOCK_FILE = '/tmp/task_runner.lock'


class Lock:
    @staticmethod
    def acquire(running: str):
        """
        Acquire a global lock. Returns True if successful, False if lock exists.
        """
        logger.debug(f'[lock:acquire] Acquiring lock...')
        if os.path.exists(LOCK_FILE):
            logger.debug(f'[lock:acquire] Acquiring lock FAILED.')
            return False

        logger.debug(f'[lock:acquire] Running process: {running}.')
        with open(LOCK_FILE, 'w') as lock:
            lock.write(running)
        return True

    @staticmethod
    def release():
        """
        Release the global lock by removing the lock file.
        """
        if os.path.exists(LOCK_FILE):
            logger.debug(f'[lock] Releasing lock...')
            os.remove(LOCK_FILE)
