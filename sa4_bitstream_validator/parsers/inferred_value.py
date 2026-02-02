class InferredValue:
    """
    A class to hold values with an inferred flag.

    This class is used to store parsed bitstream parameters and track whether
    they were inferred (not present in the bitstream) or explicitly parsed.
    """

    def __init__(self, value):
        """
        Initialize an InferredValue object.

        Args:
            value: The parsed value (can be any type - int, bool, str, etc.)
        """
        self.value = value
        self.inferred = True

    def __str__(self):
        """Return the string representation of the value."""
        # Convert boolean values to 1/0 for consistency with the codebase
        if isinstance(self.value, bool):
            return "1" if self.value else "0"
        return str(self.value)

    def __repr__(self):
        """Return a detailed representation of the InferredValue object."""
        return f"InferredValue(value={self.value}, inferred={self.inferred})"

    def __int__(self):
        """Convert the value to an integer if possible."""
        return int(self.value)

    def __bool__(self):
        """Convert the value to a boolean if possible."""
        return bool(self.value)
