import esper

def get_world():
    """
    In esper 3.x, the module itself handles the default world state.
    We return the module to maintain a consistent interface if needed,
    although calling esper functions directly is also valid.
    """
    return esper

def reset_world():
    """
    Clears the current world state.
    """
    esper.clear_database()
