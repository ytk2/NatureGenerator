"""Autodesk Fusion 360 entry point for the NatureGenerator add-in.

The entry point delegates lifecycle work to the Fusion Adapter layer and makes
startup and shutdown failures visible in Fusion.
"""

import traceback


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
        from fusion.runtime import start

        start(context)
    except Exception:
        details = traceback.format_exc()
        _report_failure("NatureGenerator Startup Error", details)
        raise


def stop(context):
    """Stop the add-in and release registered command resources."""
    try:
        from fusion.runtime import stop

        stop(context)
    except Exception:
        details = traceback.format_exc()
        _report_failure("NatureGenerator Stop Error", details)
        raise
