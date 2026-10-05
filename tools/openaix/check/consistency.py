LISTS = ("bindings", "objects")


def binding_conflicts(entity):
    """(path, reason) for two references in `extensions.sim.<sim>` of one record that name the same simulator object
    with different attributes."""
    simulators = entity.get("extensions", {}).get("sim", {}) if isinstance(entity.get("extensions"), dict) else {}
    for sim, data in simulators.items() if isinstance(simulators, dict) else ():
        if not isinstance(data, dict):
            continue
        base = ("extensions", "sim", sim)
        entries = [((*base, key, index), value) for key in LISTS if isinstance(data.get(key), list)
                   for index, value in enumerate(data[key]) if isinstance(value, dict)]
        for index, (path, value) in enumerate(entries):
            if "kind" not in value:
                continue
            for _, previous in entries[:index]:
                if previous.get("kind") != value["kind"]:
                    continue
                if any(key in previous and key in value and previous[key] != value[key] for key in ("mission_id", "layer")):
                    continue
                if any(previous.get(key) is not None and previous.get(key) == value.get(key) for key in ("name", "object_id")):
                    for key in ("name", "object_id", "unit_type", "group_category"):
                        if previous.get(key) is not None and value.get(key) is not None and previous[key] != value[key]:
                            yield (*path, key), "conflicting bindings for the same simulator object"
