# This iscript is copied from:
# https://github.com/cms-PdmV/mcm_scripts/blob/master/rest.py
#

import subprocess
import sys
import os
import json
import logging
import time

# Support for Python 2.7 and Python 3
# Some McM modules still use Python 2.7
try:
    import cookielib
except ImportError:
    import http.cookiejar as cookielib

try:
    import urllib2 as urllib
    from urllib2 import HTTPError as HTTPError
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
    import urllib.request as urllib
    from urllib.error import HTTPError as HTTPError


class MethodRequest(urllib.Request):
    """
    Custom request, so it would support different HTTP methods
    """
    def __init__(self, *args, **kwargs):
        self._method = kwargs.pop('method', None)
        urllib.Request.__init__(self, *args, **kwargs)

    def get_method(self, *args, **kwargs):
        if self._method is not None:
            return self._method

        return urllib.Request.get_method(self, *args, **kwargs)
    

class McM:
    """
    Initializes the API.

    Arguments:
        id: The authentication mechanism to use. Supported values are 'sso' to
            use auth-get-sso-cookie, 'oidc' for OIDC authentication
            ("new SSO"). Any other value results in no authentication being
            used.
        debug: Controls the amount of logging printed to the terminal.
        cookie: The path of a cookie JAR in Netscape format, to be used for
            authentication.
        dev: Whether to use the dev or production McM instance (default: dev).
    """
    SSO = 'sso'
    OIDC = 'oidc'
    CERN_OIDC_API = 'https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/'
    OIDC_DEVICE_ENDPOINT = 'auth/device'
    OIDC_TOKEN_ENDPOINT = 'token'
    COOKIE_ENV_VAR = 'MCM_COOKIE_PATH'


    def __init__(self, id=SSO, debug=False, cookie=None, dev=True):
        if dev:
            self.host = 'cms-pdmv-dev.web.cern.ch'
        else:
            self.host = 'cms-pdmv-prod.web.cern.ch'

        self.dev = dev
        self.server = 'https://' + self.host + '/mcm/'
        self.id = id

        # Set up logging
        if debug:
            logging_level = logging.DEBUG
        else:
            logging_level = logging.INFO
        
        # Set up logging
        logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s', level=logging_level)
        self.logger = logging.getLogger()

        cookie_from_env = os.getenv(McM.COOKIE_ENV_VAR)
        if cookie:
            self.cookie = cookie
        elif cookie_from_env:
            self.logger.info(
                "Setting cookie via '%s' environment variable", 
                McM.COOKIE_ENV_VAR
            )
            self.cookie = cookie_from_env
        else:
            home = os.getenv('HOME')
            if dev:
                self.cookie = '%s/private/mcm-dev-cookie.txt' % (home)
            else:
                self.cookie = '%s/private/mcm-prod-cookie.txt' % (home)

        # Request retries
        self.max_retries = 3
        
        # Create opener
        # Set a default opener to perform requests and change it 
        # when a cookie is available.
        self.opener = urllib.build_opener()
        self.__connect()

        # Give advice about Python version
        self.__check_python_version()


    def __check_python_version(self):
        """
        Raise some warning messages if the interpreter Python version
        has reached its end of life.
        """
        current_version = sys.version_info
        if (2, 7, 0) <= current_version < (3, 0, 0):
            self.logger.critical(
                (
                    'Python 2.X has been deprecated since January 1, 2020.\n'
                    'Please consider updating to the latest Python version or '
                    'at least one that is still maintained.\n'
                    'PdmV will drop Python 2.X support in the near future, hopefully, '
                    'before the end of December 2024.'
                    '\n'
                )
            )
        elif (3, 0) <= current_version <= (3, 10):
            self.logger.warning(
                (
                    'Python 3.X version currently used has reached its end of life '
                    'or it will reach it in the near future.\n'
                    'Please consider using a newer version. '
                    'Python version: %s \n' % sys.version
                )
            )

    def __verify_credential(self, display_help=True):
        """
        Send a HTTP request to a protected endpoint in McM to check
        if the provided credential is valid.

        Args:
            display_help (bool): If True, display some help messages
                about the situation.

        Returns:
            bool: True if the credential is valid, False otherwise.

        Raises:
            HTTPError: If the HTTP response has a status code different that 200 or 3XX
        """
        def __help_message__(help):
            """
            Logs some messages to give advice to the user if the authentication
            process failed.
            """
            self.logger.error('Verifying credential: HTTP response has a 3XX status code')
            self.logger.error('The provided credential is not valid')
            self.logger.info('Authentication mechanism: %s' % self.id)
            if self.id == McM.SSO and help:
                self.logger.info('Please remember that, if you have enabled 2FA, it is not possible to request')
                self.logger.info('session cookies. Please use the authentication mechanism "oidc" for using this client')

        # Use the index page
        protected_resource = ''
        authentication_required = McM.CERN_OIDC_API + 'auth'
        try:
            self.logger.debug('Verifying credential by consuming a resource in McM')
            response = self.__http_request(protected_resource, 'GET', parse_json=False, raise_on_redirection=True, raw_response=True)
            if response.url.startswith(authentication_required):
                __help_message__(display_help)
                return False
            return True
        except HTTPError as some_error:
            if (300 <= some_error.code <= 399):
                __help_message__(display_help)
                return False
            raise some_error

    def __request_token(self):
        """
        Request an ID token to the IdP server to authenticate the user.
        This authentication method requires human interaction to complete the flow.

        Returns:
            str: ID token to authenticate user requests.
            None: If there is an error requesting the token.
        """
        client_id = 'cms-ppd-pdmv-device-flow'
        client_secret = os.getenv('MCM_CLIENT_SECRET')
        data = {'client_id': client_id}
        if client_secret:
            data['client_secret'] = client_secret

        # Authorize the SDK to request a token
        self.logger.info('Requesting ID token via Device Authorization Grant')
        try:
            device_code_response = self.__http_request(
                McM.OIDC_DEVICE_ENDPOINT, 
                'POST',
                data=data, 
                server=McM.CERN_OIDC_API, 
                url_encoded=True
            )
        except HTTPError as http_error:
            if http_error.code == 401:
                self.logger.info('Please make sure the application: %s is configured as a public client' % client_id)
                self.logger.info('Otherwise, provide the client_secret')
            raise http_error

        device_code = device_code_response['device_code']
        verification_uri_complete = device_code_response['verification_uri_complete']

        self.logger.info('Please go to the following link and complete the authentication flow: ')
        self.logger.info(verification_uri_complete)

        try:
            input('Press Enter once you have authenticated...')
        except SyntaxError:
            # Python 2 tries to parse the value and raises an error
            # Just supress it 
            pass

        # Retrieve the ID token
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'device_code': device_code,
            'client_id': client_id
        }
        if client_secret:
            data['client_secret'] = client_secret

        try:
            device_completion_response = self.__http_request(
                McM.OIDC_TOKEN_ENDPOINT,
                'POST',
                data=data,
                server=McM.CERN_OIDC_API,
                url_encoded=True
            )
        except HTTPError as http_error:
            if http_error.code == 400:
                self.logger.info('Did you complete the authentication flow before pressing "Enter" right?')
            raise http_error

        id_token = device_completion_response.get('access_token')
        return id_token

    def __connect(self):
        """
        Verifies, retrieves or requests a valid credential to authenticate the user actions in
        McM. This handles the request for session cookies or ID tokens for sending them to the server.
        """
        def __load_cookie():
            """
            Loads a given cookie.
            """
            cookie_jar = cookielib.MozillaCookieJar(self.cookie)
            cookie_jar.load()
            for cookie in cookie_jar:
                self.logger.debug('Cookie %s', cookie)
            self.opener = urllib.build_opener(urllib.HTTPCookieProcessor(cookie_jar))

        if self.id == McM.SSO:
            if not os.path.isfile(self.cookie):
                self.logger.info('SSO cookie file is absent. Will try to make one for you...')
                self.__generate_cookie()
            else:
                # Load the provided cookie for checking it.
                __load_cookie()
                self.logger.info('Using SSO cookie file %s' % (self.cookie))
                display_help = False
                if not self.__verify_credential(display_help):
                    self.__generate_cookie()

            if not os.path.isfile(self.cookie):
                self.logger.error('Missing cookie file %s, quitting', self.cookie)
                sys.exit(1)

            # Load the created or renewed it cookie.
            __load_cookie()

        elif self.id == McM.OIDC:
            self.token = self.__request_token()
            self.opener = urllib.build_opener()
        else:
            self.logger.warning('Using McM client without providing authentication')
            self.opener = urllib.build_opener()

        # Verify the credential before allow the user to perform further requests
        if self.id in (McM.SSO, McM.OIDC):
            if not self.__verify_credential():
                self.logger.error('Available credential is not valid, closing client')
                sys.exit(1)


    def __generate_cookie(self):
        """
        Request a session cookie by using the package `auth-get-sso-cookie` and Kerberos
        credentials.
        """
        # use env to have a clean environment
        current_version = sys.version_info
        command = 'rm -f %s; REQUESTS_CA_BUNDLE="/etc/pki/tls/certs/ca-bundle.trust.crt"; auth-get-sso-cookie -u %s -o %s' % (self.cookie, self.server, self.cookie)
        self.logger.debug(command)
        if (3, 6, 0) <= current_version:
            # Use subprocess.run() to execute the command and avoid
            # leaking resources.
            output = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        else:
            output = os.popen(command).read()
            
        self.logger.debug(output)
        if not os.path.isfile(self.cookie):
            self.logger.error('Could not generate SSO cookie.\n%s', output)


    # Generic methods for GET, PUT, DELETE HTTP methods
    def __http_request(
            self, 
            url, 
            method, 
            data=None, 
            parse_json=True, 
            server=None,
            url_encoded=False,
            raise_on_redirection=False,
            raw_response=False
        ):
        """
        Performs an HTTP request to the server to consume the desired resource.

        Args:
            url (str): Resource to consume in the web server
            method (str): HTTP request method
            data (dict): Data to include in the HTTP request
            parse_json (bool): Parse the HTTP response content as a dict.
            server(str | None): If provided, this overwrites the domain name
                set by the server attribute
            url_encoded (bool): Parse the data argument to be used in x-www-form-urlencoded
                requests
            raise_on_redirection (bool): Instead of retrying an HTTP request renewing the credentials
                if its required, it will raise the HTTP 3XX response as an exception.
            raw_response (bool): Returns the HTTP response with all its attributes.
        Returns:
            dict | str | None: HTTP Response
        """
        domain = server if server else self.server
        url = domain + url
        self.logger.debug('[%s] %s', method, url)
        headers = {'User-Agent': 'McM Scripting'}
        if data:
            if url_encoded:
                data = urlencode(data).encode('utf-8')
                headers['Content-type'] = 'application/x-www-form-urlencoded'
            else:
                data = json.dumps(data).encode('utf-8')
                headers['Content-type'] = 'application/json'

        retries = 0
        response = None
        while retries < self.max_retries:
            request = MethodRequest(url, data=data, headers=headers, method=method)
            if self.id == McM.OIDC and hasattr(self, "token"):
                request.add_header('Authorization', 'Bearer %s' % self.token)
            try:
                retries += 1
                response = self.opener.open(request)
                
                # Return the HTTP response with all its attributes
                if raw_response:
                    return response
                
                # Return the HTTP response body
                response = response.read()
                response = response.decode('utf-8')
                self.logger.debug(response)
                self.logger.debug('Response from %s length %s', url, len(response))
                if parse_json:
                    return json.loads(response)
                else:
                    return response

            except (ValueError, HTTPError) as some_error:
                if isinstance(some_error, HTTPError):
                    if (300 <= some_error.code <= 399):
                        if raise_on_redirection:
                            raise some_error
                    else:
                        raise some_error

                wait_time = retries ** 3
                if self.id == McM.SSO:
                    self.logger.warning(
                        'Your session cookie seems to be expired, will remake it after %s seconds',
                        wait_time
                    )
                    time.sleep(wait_time)
                    self.__connect()
                elif self.id == McM.OIDC:
                    self.logger.warning('Your ID token seems to be expired, the interactive flow will start again')
                    self.__connect()
                    request.add_header('Authorization', 'Bearer %s' % self.token)
                else:
                    self.logger.warning('Error getting response, will retry after %s seconds', wait_time)
                    time.sleep(wait_time)

        self.logger.error('Error while making a %s request to %s. Response: %s',
                          method,
                          url,
                          response)
        return None

    def __get(self, url, parse_json=True):
        return self.__http_request(url, 'GET', parse_json=parse_json)

    def __put(self, url, data, parse_json=True):
        return self.__http_request(url, 'PUT', data, parse_json=parse_json)

    def __post(self, url, data, parse_json=True):
        return self.__http_request(url, 'POST', data, parse_json=parse_json)

    def __delete(self, url, parse_json=True):
        return self.__http_request(url, 'DELETE', parse_json=parse_json)

    # McM methods
    def get(self, object_type, object_id=None, query='', method='get', page=-1):
        """
        Get data from McM
        object_type - [chained_campaigns, chained_requests, campaigns, requests, flows, etc.]
        object_id - usually prep id of desired object
        query - query to be run in order to receive an object, e.g. tags=M17p1A, multiple parameters can be used with & tags=M17p1A&pwg=HIG
        method - action to be performed, such as get, migrate or inspect
        page - which page to be fetched. -1 means no paginantion, return all results
        """
        object_type = object_type.strip()
        if object_id:
            object_id = object_id.strip()
            self.logger.debug('Object ID %s provided, method is %s, database %s',
                              object_id,
                              method,
                              object_type)
            url = 'restapi/%s/%s/%s' % (object_type, method, object_id)
            result = self.__get(url).get('results')
            if not result:
                return None

            return result
        elif query:
            if page != -1:
                self.logger.debug('Fetching page %s of %s for query %s',
                                  page,
                                  object_type,
                                  query)
                url = 'search/?db_name=%s&limit=50&page=%d&%s' % (object_type, page, query)
                results = self.__get(url).get('results', [])
                self.logger.debug('Found %s %s in page %s for query %s',
                                  len(results),
                                  object_type,
                                  page,
                                  query)
                return results
            else:
                self.logger.debug('Page not given, will use pagination to build response')
                page_results = [{}]
                results = []
                page = 0
                while page_results:
                    page_results = self.get(object_type=object_type,
                                            query=query,
                                            method=method,
                                            page=page)
                    results += page_results
                    page += 1

                return results
        else:
            self.logger.error('Neither object ID, nor query is given, doing nothing...')

    def update(self, object_type, object_data):
        """
        Update data in McM
        object_type - [chained_campaigns, chained_requests, campaigns, requests, flows, etc.]
        object_data - new JSON of an object to be updated
        """
        return self.put(object_type, object_data, method='update')

    def put(self, object_type, object_data, method='save'):
        """
        Put data into McM
        object_type - [chained_campaigns, chained_requests, campaigns, requests, flows, etc.]
        object_data - new JSON of an object to be updated
        method - action to be performed, default is 'save'
        """
        url = 'restapi/%s/%s' % (object_type, method)
        res = self.__put(url, object_data)
        return res

    def approve(self, object_type, object_id, level=None):
        if level is None:
            url = 'restapi/%s/approve/%s' % (object_type, object_id)
        else:
            url = 'restapi/%s/approve/%s/%d' % (object_type, object_id, level)

        return self.__get(url)

    def clone_request(self, object_data):
        return self.put('requests', object_data, method='clone')

    def get_range_of_requests(self, query):
        res = self.__put('restapi/requests/listwithfile', data={'contents': query})
        return res.get('results', None)

    def delete(self, object_type, object_id):
        url = 'restapi/%s/delete/%s' % (object_type, object_id)
        self.__delete(url)

    def forceflow(self, prepid):
        """
        Forceflow a chained request with given prepid
        """
        res = self.__get('restapi/chained_requests/flow/%s/force' % (prepid))
        return res.get('results', None)
    
    def reset(self, prepid):
        """
        Reset a request
        """
        res = self.__get('restapi/requests/reset/%s' % (prepid))
        return res.get('results', None)
    
    def soft_reset(self, prepid):
        """
        Soft reset a request
        """
        res = self.__get('restapi/requests/soft_reset/%s' % (prepid))
        return res.get('results', None)

    def option_reset(self, prepid):
        """
        Option reset a request
        """
        res = self.__get('restapi/requests/option_reset/%s' % (prepid))
        return res.get('results', None)

    def ticket_generate(self, ticket_prepid):
        """
        Generate chains for a ticket
        """
        res = self.__get('restapi/mccms/generate/%s' % (ticket_prepid))
        return res.get('results', None)
        
    def ticket_generate_reserve(self, ticket_prepid):
        """
        Generate and reserve chains for a ticket
        """
        res = self.__get('restapi/mccms/generate/%s/reserve' % (ticket_prepid))
        return res.get('results', None)
    
    def rewind(self, chained_request_prepid):
        """
        Rewind a chained request
        """
        res = self.__get('restapi/chained_requests/rewind/%s' % (chained_request_prepid))
        return res.get('results', None)
    
    def flow(self, chained_request_prepid):
        """
        Flow a chained request
        """
        res = self.__get('restapi/chained_requests/flow/%s' % (chained_request_prepid))
        return res.get('results', None)
    
    def root_requests_from_ticket(self, ticket_prepid):
        """
        Return list of all root (first ones in the chain) requests of a ticket
        """
        mccm = self.get('mccms', ticket_prepid)
        query = ''
        for root_request in mccm.get('requests', []):
            if isinstance(root_request, str):
                query += '%s\n' % (root_request)
            elif isinstance(root_request, list):
                # List always contains two elements - start and end of a range
                query += '%s -> %s\n' % (root_request[0], root_request[1])
            else:
                self.logger.error('%s is of unsupported type %s', root_request, type(root_request))

        requests = self.get_range_of_requests(query)
        return requests
