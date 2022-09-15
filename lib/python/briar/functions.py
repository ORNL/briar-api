import uuid

def new_uuid():
    """!
    Create and return a new, 36 character unique id

    @return: str
    """
    return str(uuid.uuid4())