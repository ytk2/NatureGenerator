"""Autodesk Fusion 360 entry point for the NatureGenerator add-in.

The entry point delegates Autodesk-specific lifecycle work to the Fusion
Adapter layer so every ``adsk`` import remains below that boundary.
"""


def run(context):
    """Start the add-in inside Fusion 360."""
    from fusion.runtime import start

    start(context)


def stop(context):
    """Stop the add-in and release registered command resources."""
    from fusion.runtime import stop

    stop(context)
