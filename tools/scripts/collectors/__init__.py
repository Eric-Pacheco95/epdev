"""ISC Engine collector modules — stdlib only.

Each collector function takes (config_entry, root_dir, prev_snapshot) and returns:
    {"name": str, "value": <number|list|None>, "unit": str, "detail": str|None}

If a collector fails, it returns value=None with detail explaining why.
"""
