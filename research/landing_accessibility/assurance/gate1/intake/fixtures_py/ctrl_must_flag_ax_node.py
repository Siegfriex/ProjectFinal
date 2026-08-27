"""must_flag — Δ39/R32 violation: absent and wrong-shape task_control["ax_node"] both yield None silently."""


def bind_task(task_control):
    node = task_control.get("ax_node")
    if node is None:
        return None
    return {"role": node.get("role"), "name": node.get("name", "")}
