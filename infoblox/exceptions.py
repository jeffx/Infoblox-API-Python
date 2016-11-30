"""exceptions.py - contains all custom exceptions."""


class InfobloxException(Exception):
    """Base exception for all exceptions raised."""
    pass


class ApiError(InfobloxException):
    """General purpose Infoblox API error."""

    def __init__(self, Error, code, text, trace=None):
        """Create an instance of an ApiError.

        :param str Error: error type (followed by an explanation after ":")
        :param str code: symbolic error code
        :param str text: explanation of the error
        :param str trace: debug trace from the server if debug is enabled
        """
        self.error = Error
        self.code = code
        self.text = text
        self.trace = trace
        super(ApiError, self).__init__(text)


class NotFoundError(InfobloxException):
    """Error to indicate the requested resource could not be found."""

    def __init__(self, resource, value):
        """Create an instance of a NotFoundError exception.

        :param str resource: type of resource that could not be found
        :param str value: the value used to find the resource
        """
        self.resource = resource
        self.value = value
        msg = 'No such {resource} called {value} could be found.'
        super(NotFoundError, self).__init__(msg.format(**vars(self)))


class BadAddressError(ValueError, InfobloxException):
    """Error to indicate a bad address has been given."""

    def __init__(self, address):
        """Create an instance of a BadAddressError.

        :param address: the bad address
        """
        self.address = address
        msg = ('The given address ({!r}) was not one of the following address '
               'types: CIDR, IP range, or static IP.')
        super(BadAddressError, self).__init__(msg.format(address), address)
