import ctypes
import sys
import contextlib
import signal


@contextlib.contextmanager
def interrupt_futures(futures):  # pragma: no cover
    """Allows a list of futures to be interrupted.

    If an interrupt happens, they will all have their exceptions set to KeyboardInterrupt
    """

    # this has to be manually tested for now, because the tests interfere with the test runner

    def do_interr(*_):
        print("Stopping all functions.")
        for ent in reversed(futures):
            try:
                if not ent.cancelled():
                    ent.cancel()
            except:
                # if the future is already resolved or cancelled, ignore it
                pass
        return 1

    if sys.platform == "win32":
        from ctypes import wintypes  # pylint: disable=import-outside-toplevel

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        CTRL_C_EVENT = 0
        CTRL_BREAK_EVENT = 1

        HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

        @HANDLER_ROUTINE
        def handler(ctrl):
            if ctrl == CTRL_C_EVENT:
                handled = do_interr()
            elif ctrl == CTRL_BREAK_EVENT:
                handled = do_interr()
            else:
                handled = False
            # If not handled, call the next handler.
            return handled

        if not kernel32.SetConsoleCtrlHandler(handler, True):
            raise ctypes.WinError(ctypes.get_last_error())

        was = signal.signal(signal.SIGINT, do_interr)

        yield

        signal.signal(signal.SIGINT, was)

        # restore default handler
        kernel32.SetConsoleCtrlHandler(handler, False)
    else:
        was = signal.signal(signal.SIGINT, do_interr)
        yield
        signal.signal(signal.SIGINT, was)
