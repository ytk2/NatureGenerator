"""Small command-instance preview state and ownership controller."""

from typing import Any, Callable, Optional, Tuple

from generators import GenerationRequest, GeneratorResult


RequestSignature = Tuple[str, Tuple[Tuple[str, str, Any], ...], int]


def request_signature(request: GenerationRequest) -> RequestSignature:
    """Return a deterministic, non-hashed signature for *request*."""

    if not isinstance(request, GenerationRequest):
        raise TypeError("request must be a GenerationRequest")
    parameters = tuple(sorted(
        (key, type(value).__name__, value)
        for key, value in request.parameter_overrides.items()
    ))
    return (request.preset_id, parameters, request.resolution)


def preview_request(
    request: GenerationRequest,
    resolution_cap: int,
    resolution_candidates: Tuple[int, ...] = (),
) -> GenerationRequest:
    """Return a deterministic density-capped request for explicit Preview."""

    if isinstance(resolution_cap, bool) or not isinstance(resolution_cap, int):
        raise TypeError("preview resolution cap must be an integer")
    if not isinstance(resolution_candidates, tuple):
        raise TypeError("preview resolution candidates must be a tuple")
    preview_resolution = min(request.resolution, resolution_cap)
    previous = None
    for candidate in resolution_candidates:
        if isinstance(candidate, bool) or not isinstance(candidate, int):
            raise TypeError("preview resolution candidates must be integers")
        if candidate <= 0 or (previous is not None and candidate <= previous):
            raise ValueError(
                "preview resolution candidates must be positive and increasing"
            )
        # Keep Preview below a higher requested Final tier. When the request is
        # already at the safe default, the initial cap preserves exact density.
        if candidate < request.resolution:
            preview_resolution = max(preview_resolution, candidate)
        previous = candidate
    return GenerationRequest(
        request.preset_id,
        request.parameter_overrides,
        min(request.resolution, preview_resolution),
    )


def _body_is_valid(body: object) -> bool:
    try:
        validity = getattr(body, "isValid", True)
        return bool(validity)
    except Exception:
        return False


class PreviewController:
    """Own one command's temporary body and preview lifecycle state."""

    def __init__(self, log: Optional[Callable[[str], None]] = None) -> None:
        self._signature: Optional[RequestSignature] = None
        self._preview_request: Optional[GenerationRequest] = None
        self._body: Optional[object] = None
        self._last_result: Optional[GeneratorResult] = None
        self._state = "idle"
        self._log = log

    @property
    def state(self) -> str:
        return self._state

    @property
    def body(self) -> Optional[object]:
        return self._body

    @property
    def last_result(self) -> Optional[GeneratorResult]:
        return self._last_result

    @property
    def is_dirty(self) -> bool:
        return self._state == "stale"

    def mark_dirty(self) -> None:
        if self._state == "current":
            self._state = "stale"

    def is_current_for(self, request: GenerationRequest) -> bool:
        return (
            self._state == "current"
            and self._signature == request_signature(request)
            and self._body is not None
            and _body_is_valid(self._body)
        )

    def generate_preview(
        self,
        source_request: GenerationRequest,
        actual_request: GenerationRequest,
        generate: Callable[[GenerationRequest], GeneratorResult],
        insert: Callable[[GeneratorResult], object],
    ) -> Tuple[GeneratorResult, object, bool]:
        """Create or reuse a current preview; return result, body, created."""

        if self._state == "generating":
            raise RuntimeError("preview generation is already in progress")
        if self.is_current_for(source_request):
            if self._preview_request == actual_request:
                return self._last_result, self._body, False  # type: ignore[return-value]

        self.cleanup()
        self._state = "generating"
        try:
            result = generate(actual_request)
            body = insert(result)
            if body is None:
                raise RuntimeError("preview adapter did not return a MeshBody")
        except Exception:
            self.cleanup()
            self._state = "failed"
            raise

        self._signature = request_signature(source_request)
        self._preview_request = actual_request
        self._body = body
        self._last_result = result
        self._state = "current"
        return result, body, True

    def can_promote(self, request: GenerationRequest) -> bool:
        return (
            self.is_current_for(request)
            and self._preview_request == request
            and self._last_result is not None
        )

    def promote(self, request: GenerationRequest, final_name: str):
        """Rename an exact current preview and relinquish ownership."""

        if not self.can_promote(request):
            raise RuntimeError("current preview cannot be promoted")
        body = self._body
        result = self._last_result
        body.name = final_name  # type: ignore[union-attr]
        self._body = None
        self._signature = None
        self._preview_request = None
        self._last_result = None
        self._state = "finalized"
        return result, body

    def cleanup(self) -> None:
        """Delete only this controller's directly owned preview body."""

        body = self._body
        self._body = None
        self._signature = None
        self._preview_request = None
        self._last_result = None
        if body is not None and _body_is_valid(body):
            delete = getattr(body, "deleteMe", None)
            if callable(delete):
                try:
                    delete()
                except Exception:
                    # Invalidated Fusion entities can throw during teardown.
                    pass
        if body is not None and self._log is not None:
            self._log("Preview removed")
        self._state = "idle"
