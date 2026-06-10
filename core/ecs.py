import esper


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
