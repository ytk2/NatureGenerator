"""Autodesk Fusion 360 entry point for the NatureGenerator add-in.

The entry point delegates lifecycle work to the Fusion Adapter layer and makes
startup and shutdown failures visible in Fusion.
"""

import traceback
from pathlib import Path
import sys


def _bootstrap_addin_path():
    """Ensure sibling add-in packages are importable under Fusion's loader."""
    addin_root = str(Path(__file__).resolve().parent)
    if addin_root not in sys.path:
        sys.path.insert(0, addin_root)
    return addin_root


def _report_failure(title, details):
    """Best-effort reporting through Fusion's log and user interface."""
    app = None
    ui = None
    try:
        import adsk.core  # type: ignore[import-not-found]

        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
    except Exception:
        pass
    if app:
        try:
            app.log(details)
        except Exception:
            pass
    if ui:
        try:
            ui.messageBox(details, title)
        except Exception:
            pass
    # The original exception is re-raised by the caller. Reporting failures must
    # never replace or hide it when Fusion is only partially initialized.


def run(context):
    """Start the add-in inside Fusion 360."""
    try:
        _bootstrap_addin_path()
        from fusion.runtime import start
        from fusion.procedural_runtime import start as start_procedural

        start(context)
        start_procedural(context)
    except Exception:
        details = traceback.format_exc()
        _report_failure("NatureGenerator Startup Error", details)
        raise


def stop(context):
    """Stop the add-in and release registered command resources."""
    try:
        _bootstrap_addin_path()
        from fusion.runtime import stop
        from fusion.procedural_runtime import stop as stop_procedural

        try:
            stop(context)
        finally:
            # Procedural previews must still be released if teardown of the
            # independent Nature Library command reports an error.
            stop_procedural(context)
    except Exception:
        details = traceback.format_exc()
        _report_failure("NatureGenerator Stop Error", details)
        raise
