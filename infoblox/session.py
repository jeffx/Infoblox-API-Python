"""session.py - contains the Session class."""
import requests
from six.moves import urllib

from . import exceptions


class Session(requests.Session):
    """Custom requests session for use with the Infoblox API."""

    #: Default page size
    DEFAULT_PAGE_SIZE = 1000

    # TODO: look up when to specify the API version
    def __init__(self, url, version, page_size=None):
        """Create a new Infoblox Session instance.

        :param str url: base URL for an Infoblox server
        :param str version: API version to use
        """
        super(Session, self).__init__()
        self.base_url = url, version
        self.page_size = page_size

    @property
    def base_url(self):
        """Return the session's base URL.

        :return: complete base URL
        :rtype: str
        """
        return self._base_url

    @base_url.setter
    def base_url(self, value):
        """Set the sessions's URL given a URL and an API version.

        :param tuple value: 2-tuple of base URL and API version
        """
        url, version = value
        path = 'wapi/v{0}/'.format(version)
        self._base_url = urllib.parse.urljoin(url, path)

    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, value):
        try:
            self._page_size = abs(value) or None
        except TypeError:
            self._page_size = None

    # This is necessary because some of the URL paths contain colons, which
    # urllib naively interprets as a division between scheme and netloc.
    def urljoin(self, base, path):
        PATH = 2
        components = list(urllib.parse.urlsplit(base))
        # Either the path is relative or absolute
        if path.startswith('/'):
            new_path = path
        else:
            old_path = components[PATH].rstrip('/')  # no double slashes
            new_path = '/'.join([old_path, path])
        components[PATH] = new_path
        return urllib.parse.urlunsplit(components)

    # This logic handles the use of the correct param for return fields while
    # also CSV'ing the given fields.
    def _get_fields(self, fields, fields_only):
        param = {}
        if fields is not None:
            if fields_only:
                field = '_return_fields'
            else:
                field = '_return_fields+'
            param = {field: ','.join(fields)}
        return param

    # Combine requests' raise_for_status and json methods for expediency.
    def _raise_for_status_or_get_json(self, response):
        try:
            response.raise_for_status()
        except Exception as original_exc:
            try:
                data = response.json()
            except ValueError:
                msg = 'An unexpected error occured during a request'
                raise exceptions.InfobloxException(msg) from original_exc
            raise exceptions.ApiError(**data)
        return response.json()

    def get(self, resource, page_id=None, return_fields=None,
            return_fields_only=False, **kwargs):
        """Get a resource.

        This implements the specifics of an Infoblox GET request. Note that
        additional keyword arguments are passed along to the underlying GET
        request(s) made.

        :param str resource: the relative path for a resource
        :param int page_id: initial page of results to request
        :param list return_fields: the fields to return
        :param bool return_fields_only: whether to exclude all fields not given
        :return: response data from JSON
        :rtype: list or dict
        :raises ApiError: if the status code of the response is greater than
                          or equal to 400
        """
        # Set the params for paging and return fields
        params = kwargs.pop('params', {})
        params['_return_as_object'] = 1
        if self.page_size is not None:
            params['_max_results'] = self.page_size
            params['_paging'] = 1
            params['_page_id'] = page_id
        fields = self._get_fields(return_fields, return_fields_only)
        params.update(fields)

        # Make the first request
        url = self.urljoin(self.base_url, resource)
        response = super(Session, self).get(url, params=params, **kwargs)
        data = self._raise_for_status_or_get_json(response)
        results = data['result']

        # Don't forget about additional result pages
        while 'next_page_id' in data and page_id is not None:
            params['_page_id'] = data['next_page_id']
            response = super(Session, self).get(url, params=params, **kwargs)
            data = self._raise_for_status_or_get_json(response)
            results.extend(data['result'])
        return results

    def post(self, resource, return_fields=None, return_fields_only=False,
             **kwargs):
        """Create a new object.

        This implements the specifics of an Infoblox POST request. Note that
        additional keyword arguments are passed along to the underlying POST
        request made. If additional return fields are requested, the object is
        returned instead of just the reference.

        :param str resource: the relative path for a resource
        :param list return_fields: list of fields to return
        :param bool return_fields_only: whether to exclude all fields not given
        :return: object reference of the object created or the object itself
        :rtype: str or dict
        :raises ApiError: if the status code of the response is greater than
                          or equal to 400
        """
        params = kwargs.pop('params', {})
        fields = self._get_fields(return_fields, return_fields_only)
        params.update(fields)

        url = self.urljoin(self.base_url, resource)
        response = super(Session, self).post(url, params=params, **kwargs)
        return self._raise_for_status_or_get_json(response)

    def put(self, resource, return_fields=None, return_fields_only=False,
            **kwargs):
        """Update an existing object.

        This implements the specifics of an Infoblox PUT request. Note that
        additional keyword arguments are passed along to the underlying PUT
        request made.

        :param str resource: the relative path for a resource
        :param list return_fields: list of fields to return
        :param bool return_fields_only: whether to exclude all fields not given
        :return: object reference of the object updated or the object itself
        :rtype: str or dict
        :raises ApiError: if the status code of the response is greater than
                          or equal to 400
        """
        params = kwargs.pop('params', {})
        fields = self._get_fields(return_fields, return_fields_only)
        params.update(fields)

        url = self.urljoin(self.base_url, resource)
        response = super(Session, self).put(url, params=params, **kwargs)
        return self._raise_for_status_or_get_json(response)

    def delete(self, resource, **kwargs):
        """Delete an existing object.

        :param str resource: the relative path for a resource
        :return: object reference of the object deleted
        :rtype: str
        :raises ApiError: if the status code of the response is greater than
                          or equal to 400
        """
        url = self.urljoin(self.base_url, resource)
        response = super(Session, self).delete(url, **kwargs)
        return self._raise_for_status_or_get_json(response)
