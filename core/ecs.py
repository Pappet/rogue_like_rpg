import esper


def _fixed_get_components(*component_types):
    """Bug-free replacement for esper 3.7's private ``_get_components``.

    esper 3.7 (pinned in ``requirements.txt``) ships a faulty smallest-set
    optimisation: while scanning the requested component types for the
    smallest set, it builds its ``other_types`` filter list with
    ``other_types.append(component_types[len(other_types)])`` instead of
    appending the *previous* minimum type. When the smallest set changes
    mid-scan a requested type can drop out of the membership check, yet it
    is still dereferenced when the result tuple is built — raising
    ``KeyError`` for any entity that happens to lack that type.

    In this game it surfaced as a crash in ``NeedsSystem.process`` after the
    player killed town guards: a live ``guard`` carries AIBehaviorState +
    Activity + Position but no ``Needs``, and with the right set sizes
    (``|AIBehaviorState| < |Needs| < |Activity| < |Position|``) it slipped
    through the broken filter and ``KeyError: Needs`` was raised. The query
    order is irrelevant — any multi-component query can trip it — so we
    replace the private generator wholesale rather than patch one call site.

    This reimplementation keeps the same smallest-set optimisation but
    checks membership of *every* requested type before yielding. Remove it
    once esper ships a fix (see esper #... upstream).
    """
    if not component_types:
        return

    entity_db = esper._entities
    comp_db = esper._components
    try:
        comp_sets = [comp_db[ct] for ct in component_types]
    except KeyError:
        # At least one component type has no entities at all.
        return

    smallest = min(comp_sets, key=len)
    for entity in smallest:
        entity_comps = entity_db[entity]
        if all(ct in entity_comps for ct in component_types):
            yield entity, tuple(entity_comps[ct] for ct in component_types)


def apply_esper_compat_patches():
    """Install fixes for known esper bugs. Idempotent; safe to call repeatedly.

    Applied at import time (so tests pick it up via ``conftest``) and again
    explicitly from ``bootstrap`` for the game runtime, which never imports
    this module otherwise. ``esper.get_components`` resolves ``_get_components``
    as a module global on every call, so reassigning it takes effect for all
    existing call sites.
    """
    esper._get_components = _fixed_get_components


apply_esper_compat_patches()


def reset_world():
    """Clear the esper world state (entities, components, handlers, processors).

    esper 3.x is module-global: the module itself is the world. Code that
    needs the world should simply ``import esper`` directly.

    Processors must be cleared as a pair (_processors + _processors_dict):
    clearing only one desyncs esper's registry and makes a later
    remove_processor() raise ValueError.
    """
    esper.clear_database()
    if hasattr(esper, "event_registry"):
        esper.event_registry.clear()
    if hasattr(esper, "_processors"):
        esper._processors.clear()
    if hasattr(esper, "_processors_dict"):
        esper._processors_dict.clear()
