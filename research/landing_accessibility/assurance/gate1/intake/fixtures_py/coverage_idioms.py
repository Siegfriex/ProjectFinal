"""Predicate-coverage fixtures: one function per idiom named in CI-19 r3/r4. Each is a named control in
r32_inventory.CONTROLS (must_flag / must_not_flag) so the predicate cannot silently narrow."""
from typing import Optional


class ShapeError(TypeError):
    pass


def getattr_default_silent(planned_action):
    return getattr(planned_action, "target_selector", None)


def or_empty_dict_default(scroll_states):
    states = scroll_states or {}
    return len(states)


def try_keyerror_default(binder_output):
    try:
        family = binder_output["family_id"]
    except KeyError:
        family = None
    return family


def try_keyerror_reraise(binder_output):
    try:
        family = binder_output["family_id"]
    except KeyError as exc:
        raise ShapeError("binder_output lacks family_id") from exc
    return family


def in_guard_else_raise(terminal):
    if "status" in terminal:
        status = terminal["status"]
    else:
        raise ShapeError("terminal classifier return lacks 'status'")
    return status


def in_guard_no_else(terminal):
    status = "NOT_OBSERVED"
    if "status" in terminal:
        status = terminal["status"]
    return status


def optional_param_none_return(ax_node: Optional[dict] = None):
    if ax_node is None:
        return "AX_NODE_ABSENT"
    return ax_node.get("role", "unknown")


def pipe_none_param_raises(ax_node: dict | None):
    if ax_node is None:
        raise ShapeError("ax_node must be passed")
    return ax_node["role"]


def kwargs_read(**kwargs):
    return kwargs.get("ax_node")


def get_on_call_return(task_id):
    return _lookup(task_id).get("ax_node")


def get_chain(probe_state):
    return probe_state.get("envelope", {}).get("raw_features")


def derived_alias(probe_state):
    env = probe_state["envelope"]
    return env.get("scroll_states")


def _lookup(task_id):
    return {"task_id": task_id}
