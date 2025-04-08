import datetime
import logging
import sys
from .console import console


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


class OnceOnlyWarningFilter(logging.Filter):
    """Filter that prevents the same warning from being emitted more than once
    from the same file and line number, regardless of message content.
    """
    # Set to track warnings that have already been seen by file:line
    _seen_warnings = set()

    def filter(self, record):
        # Only apply filtering to warning level logs
        if record.levelno == logging.WARNING:
            # Create a unique identifier for this warning location
            location = f"{record.pathname}:{record.lineno}"

            # If we've seen this warning before, filter it out
            if location in self._seen_warnings:
                return False

            # Mark this warning as seen
            self._seen_warnings.add(location)

        # Allow all non-warning messages and first-time warnings
        return True


class RichConsoleHandler(logging.Handler):
    """Custom logging handler that uses rich.console.Console's out method
    with protection against recursive exception handling.
    """

    # Keep track of active logging to prevent recursion
    _logging_in_progress = False

    def __init__(self):
        super().__init__()

    def emit(self, record):
        # Simple anti-recursion mechanism - if we're already in the middle of logging,
        # don't try to log again, which could cause an infinite loop
        if RichConsoleHandler._logging_in_progress:
            # Write directly to stderr as a last resort
            fallback_msg = f"RECURSIVE LOG PREVENTED: {record.name}: {record.getMessage()}\n"
            self._safe_stderr_write(fallback_msg)
            return

        # Set the flag to prevent recursion
        RichConsoleHandler._logging_in_progress = True

        try:
            msg = self.format(record)
            console.out(msg)
        except Exception as e:
            # If logging fails, use standard stderr as fallback
            self._safe_stderr_write(f"LOGGING ERROR: {str(e)}\n")
            self._safe_stderr_write(f"Original message: {record.getMessage()}\n")
        finally:
            # Always reset the flag when done
            RichConsoleHandler._logging_in_progress = False

    def _safe_stderr_write(self, message):
        """Write to stderr, handling BlockingIOError if stderr is non-blocking."""
        try:
            sys.stderr.write(message)
        except BlockingIOError:
            # If stderr is non-blocking and would block, handle it gracefully
            # We can't log the message now, but at least we won't crash
            pass


def init_logging(verbose: bool):
    """Initialize logging with safeguards against cascading errors."""

    # Create our handler with anti-recursion protection
    handler = RichConsoleHandler()
    handler.setFormatter(GlogFormatter())

    level = logging.DEBUG if verbose else logging.INFO

    # Configure basic logging with our handler
    # The force=True parameter ensures our configuration overrides any existing handlers
    logging.basicConfig(level=level, handlers=[handler], force=True)

    # Set the log level on the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Add the once-only warning filter to prevent duplicate warnings
    root_logger.addFilter(OnceOnlyWarningFilter())
