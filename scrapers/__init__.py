"""Venue scrapers. Every module here that doesn't start with '_' and isn't base/http is a scraper."""
import importlib
import pkgutil

NOT_SCRAPERS = {"base", "http"}


def all_scrapers():
    """Return all scraper modules, sorted by name."""
    mods = []
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_") or info.name in NOT_SCRAPERS:
            continue
        mods.append(importlib.import_module(f"{__name__}.{info.name}"))
    return sorted(mods, key=lambda m: m.__name__)
