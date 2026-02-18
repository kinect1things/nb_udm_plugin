# nb_udm_plugin

NetBox plugin for discovering and synchronizing devices, VLANs, and clients from UniFi controllers.

## Features

- Discover UniFi devices (APs, switches, gateways), clients, and VLANs
- Stage discovered objects for human review before committing to NetBox
- Track which NetBox objects were created by discovery (mappings)
- Detect orphaned objects no longer seen by the controller
- Scheduled and on-demand scanning
- Supports both UniFi API token and classic (username/password + MFA) authentication

## Installation

### Docker / Podman (netbox-docker)

1. Clone this repo alongside your netbox-docker directory:

```bash
cd /opt/netbox
git clone https://github.com/kinect1things/nb_udm_plugin.git
```

2. Create `Dockerfile.plugins`:

```dockerfile
FROM docker.io/netboxcommunity/netbox:v4.5-3.4.2

COPY ./nb_udm_plugin /opt/netbox-plugins/nb_udm_plugin

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | /opt/netbox/venv/bin/python && \
    /opt/netbox/venv/bin/python -m pip install --no-cache-dir /opt/netbox-plugins/nb_udm_plugin && \
    /opt/netbox/venv/bin/python -m pip uninstall -y pip
```

3. Add a `build` section to both `netbox` and `netbox-worker` in `docker-compose.override.yml`:

```yaml
services:
  netbox:
    build:
      context: .
      dockerfile: Dockerfile.plugins
    environment:
      NB_UDM_UNIFI_TOKEN: "your-api-token-here"
  netbox-worker:
    build:
      context: .
      dockerfile: Dockerfile.plugins
    environment:
      NB_UDM_UNIFI_TOKEN: "your-api-token-here"
```

4. Enable the plugin in `configuration/plugins.py`:

```python
PLUGINS = ["nb_udm_plugin"]
```

5. Build and restart:

```bash
podman-compose build netbox    # or docker compose build netbox
podman-compose down && podman-compose up -d
```

Migrations run automatically on startup. The plugin menu appears under **UniFi Discovery** in the NetBox navbar.

### Development (bare metal)

```bash
pip install -e .
```

Add to your NetBox `configuration.py`:

```python
PLUGINS = ['nb_udm_plugin']
```

Run migrations:

```bash
python manage.py migrate
```

## Configuration

Create a Discovery Source in the plugin UI. The source config JSON holds non-secret values:

```json
{
  "host": "192.168.1.1",
  "port": 443,
  "api_mode": "token",
  "site": "default",
  "site_mappings": {"Default": "My Site"},
  "verify_ssl": false,
  "roles": {
    "wireless": "Wireless AP",
    "lan": "Network Switch",
    "router": "Router"
  },
  "manufacturer": "Ubiquiti",
  "tenant": "",
  "client_prefix_length": 24,
  "vlan_group_pattern": "{site_slug}-vlans",
  "client_description_format": "{hostname} [{mac}] ({type})",
  "discovery_tag": "udm-discovered"
}
```

## Credentials

Credentials are loaded from environment variables — never stored in the database or committed to the repo.

| Variable | Description |
|----------|-------------|
| `NB_UDM_UNIFI_TOKEN` | UniFi API token (for token auth mode) |
| `NB_UDM_UNIFI_USERNAME` | UniFi username (for classic auth mode) |
| `NB_UDM_UNIFI_PASSWORD` | UniFi password (for classic auth mode) |
| `NB_UDM_UNIFI_MFA_SECRET` | TOTP MFA secret (optional, for classic auth) |

## Part of the nb_plugins family

- **nb_udm_plugin** — UniFi device discovery (this plugin)
- **nb_pve_plugin** — Proxmox VE discovery (planned)
- **nb_snmp_plugin** — SNMP/LLDP discovery (planned)
