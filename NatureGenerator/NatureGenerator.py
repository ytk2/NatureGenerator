"""Autodesk Fusion 360 entry point for the NatureGenerator add-in.

Fusion imports are intentionally local to lifecycle functions so ordinary Python
tools can inspect this module without requiring Autodesk's runtime.
"""


def run(context):
    """Start the add-in inside Fusion 360."""
    import adsk.core  # type: ignore[import-not-found]

    app = adsk.core.Application.get()
    if app:
        app.log("NatureGenerator foundation loaded.")


def stop(context):
    """Stop the add-in and release future command resources."""
    import adsk.core  # type: ignore[import-not-found]

    app = adsk.core.Application.get()
    if app:
        app.log("NatureGenerator foundation stopped.")
