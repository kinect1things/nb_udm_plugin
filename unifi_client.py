"""
UniFi API client with support for both API token and classic (username/password) authentication.

Ported from ~/unifi2netbox/unifi/unifi.py — adapted to load credentials from
environment variables instead of constructor args.

Env vars:
    NB_UDM_UNIFI_TOKEN       - API token (for token auth)
    NB_UDM_UNIFI_USERNAME     - Username (for classic auth)
    NB_UDM_UNIFI_PASSWORD     - Password (for classic auth)
    NB_UDM_UNIFI_MFA_SECRET   - TOTP secret (optional, for classic auth)
"""
import logging
import os
import warnings

import requests
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore', InsecureRequestWarning)
logger = logging.getLogger('nb_udm_plugin.unifi_client')


class UnifiClient:
    """
    UniFi API client supporting both API token and classic authentication.

    API Token mode uses the X-API-KEY header (UniFi Integration API).
    Classic mode uses username/password with optional MFA (Legacy API).
    """

    def __init__(self, base_url, api_mode='token', site='default', verify_ssl=False):
        self.base_url = base_url.rstrip('/')
        self.api_mode = api_mode
        self.site = site
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.sites = {}
        self._connected = False

    def connect(self):
        """Establish connection and authenticate."""
        if self.api_mode == 'token':
            token = os.getenv('NB_UDM_UNIFI_TOKEN', '')
            if not token:
                raise ValueError('NB_UDM_UNIFI_TOKEN environment variable not set')
            self._api_token = token
            logger.info(f'Using API token authentication for {self.base_url}')
        else:
            username = os.getenv('NB_UDM_UNIFI_USERNAME', '')
            password = os.getenv('NB_UDM_UNIFI_PASSWORD', '')
            if not username or not password:
                raise ValueError('NB_UDM_UNIFI_USERNAME and NB_UDM_UNIFI_PASSWORD must be set')
            self._authenticate_classic(username, password)

        self.sites = self._get_sites()
        self._connected = True
        logger.info(f'Connected. Found {len(self.sites)} site(s)')

    def disconnect(self):
        """Close the session."""
        self.session.close()
        self._connected = False

    def _authenticate_classic(self, username, password):
        """Authenticate using username/password (classic mode)."""
        login_url = f'{self.base_url}/api/auth/login'
        payload = {
            'username': username,
            'password': password,
            'rememberMe': True,
        }

        mfa_secret = os.getenv('NB_UDM_UNIFI_MFA_SECRET', '')
        if mfa_secret:
            try:
                import pyotp
                otp = pyotp.TOTP(mfa_secret)
                payload['ubic_2fa_token'] = otp.now()
            except ImportError:
                logger.warning('pyotp not installed, skipping MFA')

        response = self.session.post(login_url, json=payload)
        if response.status_code == 200:
            logger.info('Classic authentication successful')
        else:
            raise Exception(f'Authentication failed: {response.status_code} - {response.text}')

    def _get_headers(self):
        """Get appropriate headers based on auth mode."""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if self.api_mode == 'token':
            headers['X-API-KEY'] = self._api_token
        return headers

    def _api_request(self, endpoint):
        """Make a GET API request."""
        url = f'{self.base_url}{endpoint}'
        headers = self._get_headers()
        logger.debug(f'GET {url}')

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'API request failed: {e}')
            return None

    def _get_sites(self):
        """Fetch all sites from the controller."""
        sites = {}

        if self.api_mode == 'token':
            result = self._api_request('/proxy/network/integration/v1/sites?limit=1000')
            if result and 'data' in result:
                for site in result['data']:
                    name = site.get('name', site.get('internalReference', 'unknown'))
                    sites[name] = {
                        'id': site.get('id'),
                        'name': name,
                        'internal_reference': site.get('internalReference'),
                        'desc': site.get('name', name),
                    }
        else:
            result = self._api_request('/api/self/sites')
            if result and result.get('meta', {}).get('rc') == 'ok':
                for site in result.get('data', []):
                    name = site.get('desc', site.get('name', 'unknown'))
                    sites[name] = {
                        'id': site.get('_id'),
                        'name': site.get('name'),
                        'desc': name,
                    }

        return sites

    def _resolve_site(self, site_name):
        """Find site info by name or internal reference."""
        for name, info in self.sites.items():
            if name == site_name or info.get('internal_reference') == site_name:
                return info
        return None

    def _get_site_key(self, site_name):
        """Get the site key for classic API endpoints."""
        for name, info in self.sites.items():
            if name == site_name:
                return info.get('name')
        return site_name

    def get_devices(self, site_name=None):
        """Fetch all network devices from a site."""
        site_name = site_name or self.site
        devices = []

        if self.api_mode == 'token':
            site_info = self._resolve_site(site_name)
            if not site_info:
                logger.warning(f"Site '{site_name}' not found")
                return devices
            result = self._api_request(
                f"/proxy/network/integration/v1/sites/{site_info['id']}/devices?limit=1000"
            )
            if result and 'data' in result:
                devices = result['data']
        else:
            site_key = self._get_site_key(site_name)
            result = self._api_request(f'/proxy/network/api/s/{site_key}/stat/device')
            if result and result.get('meta', {}).get('rc') == 'ok':
                devices = result.get('data', [])

        logger.info(f"Found {len(devices)} device(s) on site '{site_name}'")
        return devices

    def get_clients(self, site_name=None):
        """Fetch all connected clients from a site."""
        site_name = site_name or self.site
        clients = []

        if self.api_mode == 'token':
            site_info = self._resolve_site(site_name)
            if not site_info:
                return clients
            result = self._api_request(
                f"/proxy/network/integration/v1/sites/{site_info['id']}/clients?limit=1000"
            )
            if result and 'data' in result:
                clients = result['data']
        else:
            site_key = self._get_site_key(site_name)
            result = self._api_request(f'/proxy/network/api/s/{site_key}/stat/sta')
            if result and result.get('meta', {}).get('rc') == 'ok':
                clients = result.get('data', [])

        logger.info(f"Found {len(clients)} client(s) on site '{site_name}'")
        return clients

    def get_networks(self, site_name=None):
        """Fetch all networks (VLANs) from a site."""
        site_name = site_name or self.site
        networks = []

        if self.api_mode == 'token':
            site_info = self._resolve_site(site_name)
            if not site_info:
                return networks
            result = self._api_request(
                f"/proxy/network/integration/v1/sites/{site_info['id']}/networks?limit=1000"
            )
            if result and 'data' in result:
                networks = result['data']
        else:
            site_key = self._get_site_key(site_name)
            result = self._api_request(f'/proxy/network/api/s/{site_key}/rest/networkconf')
            if result and result.get('meta', {}).get('rc') == 'ok':
                networks = result.get('data', [])

        logger.info(f"Found {len(networks)} network(s) on site '{site_name}'")
        return networks
