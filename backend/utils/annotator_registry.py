# hot_registry.py
from __future__ import annotations
import importlib
import importlib.util
import importlib.metadata as imd
import importlib.util
import io
import os
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Type

import yaml  # pip install pyyaml

@dataclass
class AnnotatorSpec:
    domain: str
    module: str
    cls: str
    enabled: bool = True
    kwargs: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Config:
    version: int
    annotators: list[AnnotatorSpec]

def _parse_config(raw: dict) -> Config:
    specs: list[AnnotatorSpec] = []
    for item in raw.get("annotators", []):
        specs.append(
            AnnotatorSpec(
                domain=item["domain"],
                module=item["module"],
                cls=item.get("class") or item["cls"],
                enabled=item.get("enabled", True),
                kwargs=item.get("kwargs", {}) or {},
            )
        )
    return Config(version=int(raw["version"]), annotators=specs)

def _read_config(path: str) -> Config:
    with io.open(path, "r", encoding="utf-8") as f:
        return _parse_config(yaml.safe_load(f) or {})

def _module_origin_mtime(module_name: str) -> float:
    """
    Returns the source file mtime for a module, or 0 if not found (eg. namespace pkg).
    """
    spec = importlib.util.find_spec(module_name)
    if not spec or not spec.origin or spec.origin == "built-in":
        return 0.0
    try:
        return os.path.getmtime(spec.origin)
    except OSError:
        return 0.0

class HotAnnotatorRegistry:
    """
    Config-driven registry that hot-loads NEW modules and reloads CHANGED modules.
    No service restart required.
    """
    def __init__(self, config_path: str):
        self._config_path = os.path.abspath(config_path)
        self._lock = threading.RLock()
        self._cfg_mtime = 0.0
        self._class_by_domain: Dict[str, Type] = {}
        self._kwargs_by_domain: Dict[str, Dict[str, Any]] = {}
        self._module_mtime: Dict[str, float] = {}  # module -> last seen mtime
        # initial load
        self._maybe_reload(force=True)

    # ---------- public API ----------
    def get_annotator(self, domain: str, **overrides) -> Any:
        self._maybe_reload()
        with self._lock:
            try:
                cls = self._class_by_domain[domain]
            except KeyError as e:
                raise ValueError(f"Unknown annotator '{domain}'. "
                                 f"Available: {sorted(self._class_by_domain)}") from e
            kwargs = dict(self._kwargs_by_domain.get(domain, {}))
        kwargs.update(overrides)
        return cls(**kwargs)

    def available_domains(self) -> list[str]:
        self._maybe_reload()
        with self._lock:
            return sorted(self._class_by_domain)

    # ---------- internals ----------
    def _maybe_reload(self, force: bool = False):
        """
        1) If config changed, re-import/reload as needed.
        2) If any module files changed, reload them too.
        """
        with self._lock:
            importlib.invalidate_caches()

            cfg_changed = self._config_changed() or force
            if cfg_changed:
                cfg = _read_config(self._config_path)
                new_classes: Dict[str, Type] = {}
                new_kwargs: Dict[str, Dict[str, Any]] = {}
                for spec in cfg.annotators:
                    if not spec.enabled:
                        continue
                    cls = self._load_or_reload_class(spec.module, spec.cls)
                    new_classes[spec.domain] = cls
                    new_kwargs[spec.domain] = spec.kwargs
                # atomic swap
                self._class_by_domain = new_classes
                self._kwargs_by_domain = new_kwargs

            # Even without config edits, developer might edit code on disk:
            # if any module backing files changed, reload and rebuild classes.
            touched = self._reload_touched_modules()
            if touched:
                # rebuild classes for current config to bind to refreshed module objects
                cfg = _read_config(self._config_path)
                reb_classes: Dict[str, Type] = {}
                for spec in cfg.annotators:
                    if not spec.enabled:
                        continue
                    reb_classes[spec.domain] = self._get_class(spec.module, spec.cls)
                self._class_by_domain = reb_classes  # keep existing kwargs

    def _config_changed(self) -> bool:
        try:
            m = os.path.getmtime(self._config_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self._config_path}")
        if m > self._cfg_mtime:
            self._cfg_mtime = m
            return True
        return False

    def _load_or_reload_class(self, module_name: str, class_name: str) -> Type:
        mtime = _module_origin_mtime(module_name)
        mod = sys.modules.get(module_name)

        if mod is None:
            mod = importlib.import_module(module_name)  # first import (works for *newly added* files too)
            self._module_mtime[module_name] = mtime
        else:
            last = self._module_mtime.get(module_name, 0.0)
            if mtime > last:
                mod = importlib.reload(mod)             # code changed; refresh
                self._module_mtime[module_name] = mtime
            # else: unchanged

        try:
            return getattr(mod, class_name)
        except AttributeError as e:
            raise ImportError(f"{class_name} not found in {module_name}") from e

    def _get_class(self, module_name: str, class_name: str) -> Type:
        mod = sys.modules.get(module_name) or importlib.import_module(module_name)
        return getattr(mod, class_name)

    def _reload_touched_modules(self) -> bool:
        """
        Reload any modules we’re tracking whose source mtime has increased.
        Returns True if any module was reloaded.
        """
        changed = False
        for module_name, last_mtime in list(self._module_mtime.items()):
            current = _module_origin_mtime(module_name)
            if current > last_mtime:
                mod = sys.modules.get(module_name)
                if mod:
                    importlib.reload(mod)
                    self._module_mtime[module_name] = current
                    changed = True
        return changed
