__all__ = ['ScorepTrace']

import sys
from scorep.instrumenters.utils import get_module_name, get_file_name
from scorep.instrumenters.scorep_instrumenter import ScorepInstrumenter

try:
    import threading
except ImportError:
    _settrace = sys.settrace

    def _unsettrace():
        sys.settrace(None)

else:
    def _settrace(func):
        threading.settrace(func)
        sys.settrace(func)

    def _unsettrace():
        sys.settrace(None)
        threading.settrace(None)


class ScorepTrace(ScorepInstrumenter):
    def _enable_instrumenter(self):
        _settrace(self._globaltrace)

    def _disable_instrumenter(self):
        _unsettrace()

    def _globaltrace(self, frame, why, arg):
        """Handler for call events.
        @return self.localtrace or None
        """
        if why == 'call':
            code = frame.f_code
            modulename = get_module_name(frame)
            if not code.co_name == "_unsettrace" and not modulename[:6] == "scorep":
                full_file_name = get_file_name(frame)
                line_number = code.co_firstlineno
                self._scorep_bindings.region_begin(modulename, code.co_name, full_file_name, line_number)
                return self._localtrace
        return None

    def _localtrace(self, frame, why, arg):
        if why == 'return':
            code = frame.f_code
            modulename = get_module_name(frame)
            self._scorep_bindings.region_end(modulename, code.co_name)
        return self._localtrace
