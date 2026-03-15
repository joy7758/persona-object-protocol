from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def import_matching_modules(
    package_name: str,
    exact_names: tuple[str, ...] = (),
    prefixes: tuple[str, ...] = (),
) -> list[ModuleType]:
    package = importlib.import_module(package_name)
    module_names = set(exact_names)
    package_paths = getattr(package, "__path__", None)

    if package_paths is not None:
        for _, name, _ in pkgutil.iter_modules(package_paths):
            if name in exact_names or any(name.startswith(prefix) for prefix in prefixes):
                module_names.add(name)

    return [
        importlib.import_module(f"{package_name}.{module_name}")
        for module_name in sorted(module_names)
    ]


def collect_module_exports(
    package_name: str,
    export_name: str,
    exact_names: tuple[str, ...] = (),
    prefixes: tuple[str, ...] = (),
) -> tuple[object, ...]:
    exports: list[object] = []
    for module in import_matching_modules(package_name, exact_names, prefixes):
        exports.extend(getattr(module, export_name, ()))
    return tuple(exports)
