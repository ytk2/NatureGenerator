"""Preview ownership isolated to one Procedural Lab command instance."""

from typing import Optional


def _valid(body: object) -> bool:
    try:
        return bool(getattr(body, "isValid", True))
    except Exception:
        return False


class ProceduralPreviewController:
    def __init__(self) -> None:
        self._body: Optional[object] = None

    @property
    def body(self) -> Optional[object]:
        return self._body

    def replace(self, create):
        self.cleanup()
        try:
            body = create()
            if body is None:
                raise RuntimeError("preview insertion returned no MeshBody")
            self._body = body
            return body
        except Exception:
            self.cleanup()
            raise

    def cleanup(self) -> None:
        body = self._body
        self._body = None
        if body is not None and _valid(body):
            delete = getattr(body, "deleteMe", None)
            if callable(delete):
                try:
                    delete()
                except Exception:
                    pass
