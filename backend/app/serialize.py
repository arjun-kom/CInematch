from bson import ObjectId


def clean(value):
    """Make MongoDB documents JSON-friendly: ObjectId -> str, _id -> id."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {("id" if k == "_id" else k): clean(v) for k, v in value.items()}
    return value
