from __future__ import annotations

import importlib
import os
import pkgutil
import sys
from pathlib import Path
from types import ModuleType

PLUGIN_PACKAGES_ENV = "POP_PLUGIN_PACKAGES"
PLUGIN_PACKAGE_PATHS_ENV = "POP_PLUGIN_PACKAGE_PATHS"


def split_package_names(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def split_search_paths(value: str) -> tuple[Path, ...]:
    return tuple(
        Path(part).expanduser().resolve()
        for part in value.split(os.pathsep)
        if part.strip()
    )


def configure_plugin_search_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    configured: list[Path] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Plugin package path does not exist: {path}")
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.append(path_str)
        configured.append(path)
    return tuple(configured)


def configured_package_names(
    default_packages: tuple[str, ...] = ("demos",),
    extra_packages: tuple[str, ...] = (),
) -> tuple[str, ...]:
    plugin_paths = split_search_paths(os.environ.get(PLUGIN_PACKAGE_PATHS_ENV, ""))
    configure_plugin_search_paths(plugin_paths)
    env_packages = split_package_names(os.environ.get(PLUGIN_PACKAGES_ENV, ""))

    ordered_packages: list[str] = []
    seen: set[str] = set()
    for package_name in (*default_packages, *extra_packages, *env_packages):
        if package_name and package_name not in seen:
            ordered_packages.append(package_name)
            seen.add(package_name)
    return tuple(ordered_packages)


def import_matching_modules(
    package_names: str | tuple[str, ...],
    exact_names: tuple[str, ...] = (),
    prefixes: tuple[str, ...] = (),
) -> list[ModuleType]:
    if isinstance(package_names, str):
        package_names = (package_names,)

    imported_modules: list[ModuleType] = []
    seen_module_names: set[str] = set()

    for package_name in package_names:
        package = importlib.import_module(package_name)
        module_names: set[str] = set()
        package_paths = getattr(package, "__path__", None)

        if package_paths is not None:
            for _, name, _ in pkgutil.iter_modules(package_paths):
                if name in exact_names or any(name.startswith(prefix) for prefix in prefixes):
                    module_names.add(name)
        else:
            for name in exact_names:
                qualified_name = f"{package_name}.{name}"
                if importlib.util.find_spec(qualified_name) is not None:
                    module_names.add(name)

        for module_name in sorted(module_names):
            qualified_name = f"{package_name}.{module_name}"
            if qualified_name in seen_module_names:
                continue
            imported_modules.append(importlib.import_module(qualified_name))
            seen_module_names.add(qualified_name)

    return imported_modules


def collect_module_exports(
    package_names: str | tuple[str, ...],
    export_name: str,
    exact_names: tuple[str, ...] = (),
    prefixes: tuple[str, ...] = (),
) -> tuple[object, ...]:
    exports: list[object] = []
    for module in import_matching_modules(package_names, exact_names, prefixes):
        exports.extend(getattr(module, export_name, ()))
    return tuple(exports)
