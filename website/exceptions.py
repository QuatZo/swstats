class ProfileDoesNotExist(Exception):
    """Raised when Profile does NOT exists in database"""
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return f'ProfileDoesNotExists has been raised with message: {self.message}'
        else:
            return 'ProfileDoesNotExists has been raised'