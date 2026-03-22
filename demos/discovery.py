from __future__ import annotations

import importlib
import importlib.util
import json
import os
import pkgutil
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PACKAGES_ENV = "POP_PLUGIN_PACKAGES"
PLUGIN_PACKAGE_PATHS_ENV = "POP_PLUGIN_PACKAGE_PATHS"
PLUGIN_CONFIG_FILE_ENV = "POP_PLUGIN_CONFIG_FILE"
DEFAULT_PLUGIN_CONFIG_PATH = PROJECT_ROOT / "plugin_config.json"
PLUGIN_CONFIG_SCHEMA_PATH = PROJECT_ROOT / "plugin_config.schema.json"


@dataclass(frozen=True)
class PluginDiscoveryConfig:
    config_path: Path | None
    package_names: tuple[str, ...]
    package_paths: tuple[Path, ...]


def split_package_names(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def split_search_paths(value: str) -> tuple[Path, ...]:
    return tuple(
        Path(part).expanduser().resolve()
        for part in value.split(os.pathsep)
        if part.strip()
    )


def unique_strings(values: tuple[str, ...]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)


def unique_paths(values: tuple[Path, ...]) -> tuple[Path, ...]:
    ordered: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)


def resolve_plugin_config_path(config_file: str | Path | None = None) -> Path | None:
    if config_file is not None:
        candidate = Path(config_file).expanduser().resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Plugin config file does not exist: {candidate}")
        return candidate

    env_value = os.environ.get(PLUGIN_CONFIG_FILE_ENV, "").strip()
    if env_value:
        candidate = Path(env_value).expanduser().resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Plugin config file does not exist: {candidate}")
        return candidate

    if DEFAULT_PLUGIN_CONFIG_PATH.exists():
        return DEFAULT_PLUGIN_CONFIG_PATH

    return None


def resolve_relative_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def normalize_plugin_paths(
    payload: dict[str, Any],
    base_dir: Path,
) -> tuple[Path, ...]:
    paths: list[Path] = []
    for raw_path in payload.get("plugin_package_paths", ()):
        if str(raw_path).strip():
            paths.append(resolve_relative_path(str(raw_path), base_dir))

    for entry in payload.get("plugin_paths", ()):
        if isinstance(entry, str):
            if entry.strip():
                paths.append(resolve_relative_path(entry, base_dir))
            continue
        if isinstance(entry, dict):
            raw_path = str(entry.get("path", "")).strip()
            if raw_path:
                paths.append(resolve_relative_path(raw_path, base_dir))

    return unique_paths(tuple(paths))


def normalize_plugin_packages(payload: dict[str, Any]) -> tuple[str, ...]:
    package_names: list[str] = []
    for package_name in payload.get("plugin_packages", ()):
        normalized = str(package_name).strip()
        if normalized:
            package_names.append(normalized)

    for entry in payload.get("plugin_paths", ()):
        if isinstance(entry, dict):
            package_name = str(entry.get("package_name", "")).strip()
            if package_name:
                package_names.append(package_name)

    return unique_strings(tuple(package_names))


def load_plugin_config(
    config_file: str | Path | None = None,
) -> PluginDiscoveryConfig:
    config_path = resolve_plugin_config_path(config_file)
    if config_path is None:
        return PluginDiscoveryConfig(None, (), ())

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Plugin config must be a JSON object.")
    validate_plugin_config_payload(payload)

    base_dir = config_path.parent
    package_paths = normalize_plugin_paths(payload, base_dir)
    package_names = normalize_plugin_packages(payload)
    return PluginDiscoveryConfig(config_path, package_names, package_paths)


def load_plugin_config_schema() -> dict[str, Any]:
    return json.loads(PLUGIN_CONFIG_SCHEMA_PATH.read_text(encoding="utf-8"))


def validation_error_path(error: Any) -> str:
    parts = [str(part) for part in getattr(error, "absolute_path", ())]
    return ".".join(parts) if parts else "<root>"


def validate_plugin_config_payload(payload: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Plugin config validation requires `jsonschema`. "
            "Install `pop-persona[schema]` or add `jsonschema` to your environment."
        ) from exc

    schema = load_plugin_config_schema()
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except jsonschema.ValidationError as exc:
        path = validation_error_path(exc)
        raise ValueError(f"Invalid plugin config at {path}: {exc.message}") from exc


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


def configured_plugin_sources(
    default_packages: tuple[str, ...] = ("demos",),
    extra_packages: tuple[str, ...] = (),
    config_file: str | Path | None = None,
) -> PluginDiscoveryConfig:
    file_config = load_plugin_config(config_file)
    env_paths = split_search_paths(os.environ.get(PLUGIN_PACKAGE_PATHS_ENV, ""))
    configured_paths = configure_plugin_search_paths(
        unique_paths((*file_config.package_paths, *env_paths))
    )
    env_packages = split_package_names(os.environ.get(PLUGIN_PACKAGES_ENV, ""))
    package_names = unique_strings(
        (*default_packages, *extra_packages, *file_config.package_names, *env_packages)
    )
    return PluginDiscoveryConfig(file_config.config_path, package_names, configured_paths)


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
