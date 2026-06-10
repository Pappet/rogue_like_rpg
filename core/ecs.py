import esper


def reset_world():
    """Clear the esper world state (entities, components, event handlers).

    esper 3.x is module-global: the module itself is the world. Code that
    needs the world should simply ``import esper`` directly.
    """
    esper.clear_database()
    if hasattr(esper, "event_registry"):
        esper.event_registry.clear()
