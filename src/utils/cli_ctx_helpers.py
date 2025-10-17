from typing import Any, Callable, Dict, Optional
import click


def set_global_prop(ctx: click.Context, name: str, value: Any) -> None:
    """
    Store exactly what the user provided (including None) for a given global property.
    """
    ctx.ensure_object(dict)
    globals_dict: Dict[str, Any] = ctx.obj.setdefault("_globals", {})
    globals_dict[name] = value


def get_global_prop(ctx: click.Context, name: str) -> Any:
    """
    Retrieve a previously stored global property (or None if not set).
    """
    if not ctx.obj or "_globals" not in ctx.obj:
        return None
    return ctx.obj["_globals"].get(name, None)


def resolve_prop(
    *,
    name: str,
    local_value: Any,
    global_value: Any,
    default: Any,
    conflict_message: Optional[str] = None,
    formatter: Optional[Callable[[Any], str]] = None,
) -> Any:
    """
    Resolve an option/property that can be set at the global (group) level or at the
    local (command) level, with an explicit default and conflict detection.

    Precedence:
      - If local_value is not None -> use local_value
      - Else if global_value is not None -> use global_value
      - Else -> use default

    Conflict rule:
      - If both local and global are explicitly provided and differ -> raise UsageError

    Args:
        name: Logical name of the property (for error messages).
        local_value: Value passed to the subcommand (may be None).
        global_value: Value captured at the group level (may be None).
        default: Fallback when neither level specifies a value.
        conflict_message: Optional explicit error message. If not provided, a generic one is created.
        formatter: Optional function to pretty-print values in messages.

    Returns:
        The effective resolved value.
    """
    if (global_value is not None) and (local_value is not None) and (global_value != local_value):
        fmt = formatter or (lambda v: repr(v))
        msg = conflict_message or (
            f"Conflicting {name!r} values: global is {fmt(global_value)}, "
            f"but subcommand is {fmt(local_value)}."
        )
        raise click.UsageError(msg)

    if local_value is not None:
        return local_value
    if global_value is not None:
        return global_value
    return default


def resolve_bool_flag(
    *,
    name: str,
    local_value: Optional[bool],
    global_value: Optional[bool],
    default: bool,
    true_label: str,
    false_label: str,
) -> bool:
    """
    Convenience wrapper for tri-state boolean flags (None/True/False) that uses
    resolve_prop but formats values with flag-like labels (e.g., '--repo'/'--no-repo').
    """
    def _fmt(v: Optional[bool]) -> str:
        if v is None:
            return "unspecified"
        return true_label if v else false_label

    return resolve_prop(
        name=name,
        local_value=local_value,
        global_value=global_value,
        default=default,
        formatter=_fmt,
        conflict_message=(
            f"Conflicting {name!r} settings: global is "
            f"{_fmt(global_value)}, but subcommand is {_fmt(local_value)}."
        ),
    )
