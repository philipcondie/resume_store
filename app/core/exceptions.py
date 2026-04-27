class DuplicateFilenameError(Exception):
    """Excpection for when a user tries to add a duplicate filename"""

    def __init__(self, filename):
        super().__init__(f"Filename ({filename}) already exists")


class ResourceNotFoundError(Exception):
    """Exception for when items are not found in database"""

    def __init__(self, resource, identifier):
        super().__init__(f"Resource ({resource}) not found for {identifier}")


class IncompleteResumeInputError(Exception):
    """Exception for if required info is missing for resume generation"""

    def __init__(self, identifier, input):
        super().__init__(f"Cannot generate resume for {identifier}: missing {input}")
