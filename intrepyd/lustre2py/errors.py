"""
What the Lustre front end refuses, said with where: a syntax error, a
construct it does not support, Kind2's contracts.
"""


class LustreError(ValueError):
    """A Lustre file that cannot be translated, with its line and column (1-based)."""

    def __init__(self, message, line=None, column=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def where(self, filename):
        """``file:line:column: message``, as compilers say it."""
        place = filename
        if self.line is not None:
            place += f':{self.line}'
            if self.column is not None:
                place += f':{self.column}'
        return f'{place}: {self.message}'
