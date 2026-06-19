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


class ResumeLengthError(Exception):
    """Exception for when resume is longer than the acceptable length"""

    def __init__(self, length):
        super().__init__(f"Resume length exceeds limit. Pages: {length}")


class PDFGenerationError(Exception):
    """Exception for when resume is longer than the acceptable length"""

    def __init__(self, filename: str):
        super().__init__(f"Resume pdf could not be generated. Filename: {filename}")


class PDFRendererConfigurationError(Exception):
    def __init__(self):
        super().__init__("PDF Renderer configuration is incorrect")


class PDFReaderError(Exception):
    def __init__(self):
        super().__init__("PDF Reader could not parse pdf bytes")


class RenderCapacityError(Exception):
    def __init__(self):
        super().__init__("Insufficient render capacity.")


class PDFRenderError(Exception):
    def __init__(self):
        super().__init__("PDF render failed")


class PDFRenderTimeoutError(Exception):
    def __init__(self):
        super().__init__("PDF render timed out")
