"""must_not_flag — Δ39/R32 state (2): wrong shape raises BEFORE the optional-key access."""


class ShapeError(TypeError):
    """probe_state is present but not the agreed envelope shape."""


def measure_surface(probe_state):
    if not isinstance(probe_state, dict):
        raise ShapeError(f"probe_state must be a dict, got {type(probe_state).__name__}")
    if "envelope" not in probe_state:
        raise ShapeError("probe_state has no 'envelope'")
    envelope = probe_state["envelope"]
    if not isinstance(envelope, dict):
        raise ShapeError("probe_state['envelope'] must be a dict")
    raw = envelope.get("raw_features")
    if raw is None:
        return {"observed": None, "reason": "raw_features absent"}
    return {"observed": len(raw), "reason": None}
