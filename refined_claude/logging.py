import datetime
import logging


class GlogFormatter(logging.Formatter):
    # Map Python log levels to glog letters.
    LEVEL_MAP = {
        logging.DEBUG: "D",
        logging.INFO: "I",
        logging.WARNING: "W",
        logging.ERROR: "E",
        logging.CRITICAL: "F",
    }

    def __init__(self):
        super().__init__(
            fmt="%(glog_level)s%(asctime)s %(process)d %(filename)s:%(lineno)d] %(message)s"
        )

    def formatTime(self, record, datefmt=None):
        # Create a datetime object from the record's created time.
        dt = datetime.datetime.fromtimestamp(record.created)
        # Format time as MMDD HH:MM:SS.microseconds (as glog does)
        s = dt.strftime("%m%d %H:%M:%S")
        s += ".%06d" % dt.microsecond
        return s

    def format(self, record):
        # Add the glog level letter to the record.
        record.glog_level = self.LEVEL_MAP.get(record.levelno, "I")
        return super().format(record)


def init_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(GlogFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
