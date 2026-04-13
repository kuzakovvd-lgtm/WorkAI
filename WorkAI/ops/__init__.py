"""Operations layer public API."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "cost_rollup_to_dict",
    "cutover_readiness_to_dict",
    "healthcheck_exit_code",
    "healthcheck_to_dict",
    "parallel_diff_to_dict",
    "run_cost_rollup",
    "run_cutover_readiness",
    "run_healthcheck",
    "run_parallel_diff",
    "run_stale_sweeper",
    "run_verify_units",
    "stale_sweeper_to_dict",
    "verify_units_to_dict",
]

_SYMBOL_TO_MODULE: dict[str, tuple[str, str]] = {
    "cost_rollup_to_dict": ("WorkAI.ops.cost_rollup", "cost_rollup_to_dict"),
    "run_cost_rollup": ("WorkAI.ops.cost_rollup", "run_cost_rollup"),
    "cutover_readiness_to_dict": ("WorkAI.ops.cutover_readiness", "cutover_readiness_to_dict"),
    "run_cutover_readiness": ("WorkAI.ops.cutover_readiness", "run_cutover_readiness"),
    "healthcheck_exit_code": ("WorkAI.ops.healthcheck", "healthcheck_exit_code"),
    "healthcheck_to_dict": ("WorkAI.ops.healthcheck", "healthcheck_to_dict"),
    "run_healthcheck": ("WorkAI.ops.healthcheck", "run_healthcheck"),
    "parallel_diff_to_dict": ("WorkAI.ops.parallel_diff", "parallel_diff_to_dict"),
    "run_parallel_diff": ("WorkAI.ops.parallel_diff", "run_parallel_diff"),
    "run_stale_sweeper": ("WorkAI.ops.stale_sweeper", "run_stale_sweeper"),
    "stale_sweeper_to_dict": ("WorkAI.ops.stale_sweeper", "stale_sweeper_to_dict"),
    "run_verify_units": ("WorkAI.ops.verify_units", "run_verify_units"),
    "verify_units_to_dict": ("WorkAI.ops.verify_units", "verify_units_to_dict"),
}


def __getattr__(name: str) -> Any:
    target = _SYMBOL_TO_MODULE.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, symbol_name = target
    module = import_module(module_name)
    symbol = getattr(module, symbol_name)
    globals()[name] = symbol
    return symbol
