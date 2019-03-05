import logging
import os
logging.basicConfig(filename="soph.log",
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

class SophLogger:
    def __init__(self, fileName):
        os.makedirs("logs", exist_ok=True)
        self._logger = self.setup_logger(fileName, os.path.join("logs", fileName))

    def setup_logger(self, name, log_file, level=logging.INFO):
        """Function setup as many loggers as you want"""

        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)

        return logger

    def __call__(self, something):
        try:
            self._logger.info(something)
        except:
            pass