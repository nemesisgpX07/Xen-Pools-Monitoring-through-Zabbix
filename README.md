# Xen-Pools-Monitoring-through-Zabbix

1. allow 80 and 443 communication from the master hosts to the proxy server.
2. The name which is given the pass_config.py file should be same as the name given in zabbix frontend.
3. attach the template 

IMPORTANT : Only communication from master host is needed to the proxy server all the slave hosts, datastores, vm's will be monitored

## Setup: Xen host and VM monitoring

This setup polls Xen/XCP-ng pools and sends host, storage, network, and VM metrics to Zabbix using the Zabbix sender protocol.

flowchart LR
	C[Cron] --> CH[cron_host.sh]
	C --> CV[cron_vm.sh]
	CH --> H[host.py + host ID]
	CV --> V[vm.py + host ID]
	H --> PC[pass_config.py]
	V --> PC
	H --> X[Xen/XCP-ng API]
	V --> X
	H --> Z[Zabbix server :10051]
	V --> Z
	PC --> X
```

### Requirements

- A Linux host with Python 3, Bash, `cron`, `flock`, and `timeout`.
- The XenAPI Python module installed and importable by the same Python interpreter used by the cron scripts.
- Network access from the poller to Xen pool masters over HTTPS (TCP 443) and to the Zabbix server (default TCP 10051).
- A Zabbix host configured to receive the item keys and discovery data emitted by these scripts.

### Configure and install

1. Place `host.py`, `vm.py`, `pass_config.py`, `cron_host.sh`, and `cron_vm.sh` together in `/root/scripts` (or update the absolute paths in both shell scripts).
2. Complete `pass_config.py` with the Zabbix server address and port, plus one `get_xen_config()` entry per pool. Each entry is keyed by the string host ID and supplies the Xen pool-master address, Xen username/password, and matching Zabbix host name. The checked-in file is only a placeholder and its example entry must be completed with valid Python syntax before use.
3. Keep real credentials out of public Git history. Store the populated config privately with restrictive permissions; if a real secret has already been committed, rotate it.
4. In both shell scripts, update the `IDS` array to the host IDs configured in `pass_config.py`. The current arrays contain only ID `50`, while the placeholder config example uses ID `1`; make these IDs match.
5. Ensure the scripts can write to `/var/log` and make the shell runners executable:

   ```bash
   chmod 750 /root/scripts/cron_host.sh /root/scripts/cron_vm.sh
   ```

### Test and schedule

Run each poller manually first, replacing `<host_id>` with an ID present in `pass_config.py`:

```bash
/usr/bin/python3 /root/scripts/host.py <host_id>
/usr/bin/python3 /root/scripts/vm.py <host_id>
```

After both succeed, add the batch runners to the root user's crontab (adjust the schedule as needed):

```cron
*/5 * * * * /root/scripts/cron_host.sh
*/7 * * * * /root/scripts/cron_vm.sh
```

The shell runners process IDs in parallel (up to `MAX_PARALLEL`), prevent overlapping runs with lock files, enforce per-poll timeouts, and write per-ID output to `/var/log/per<ID>.log` or `/var/log/vm<ID>.log`. Batch status goes to `/var/log/host_batch.log` and `/var/log/vm_batch.log`.



# Xen Pools Monitoring Through Zabbix

Automated monitoring solution for **XenServer/XCP-ng pools and virtual machines using Zabbix and Python**.

## Overview

This project provides scripts for monitoring Xen virtualization infrastructure through Zabbix.

It can be used to collect and monitor information from Xen pools, hosts, and virtual machines and expose the required metrics to Zabbix.

## Features

* Xen Pool monitoring
* Xen host monitoring
* Virtual machine monitoring
* VM discovery
* Host discovery
* Custom Zabbix metrics
* Python-based monitoring scripts
* Automated data collection
* Scheduled monitoring using Linux cron
* Integration with Zabbix

## Technologies

* Python
* Zabbix
* XenServer / Xen
* XCP-ng
* Linux
* XenAPI
* Bash
* Cron

## Repository Structure

```text
.
├── host.py
├── vm.py
├── pass_config.py
├── cron_host.sh
├── cron_vm.sh
```

## Requirements

Before deploying the monitoring scripts, ensure that:

* Zabbix Server/Proxy is available
* Python is installed
* XenAPI/Python Xen libraries are installed
* Network connectivity to the Xen infrastructure is available
* Required Zabbix configuration is completed
* Appropriate permissions are configured

## Monitoring Architecture

```text
Xen Pool
   │
   ├── Xen Host
   │
   ├── Xen Host
   │
   └── Virtual Machines
           │
           ▼
     Python Scripts
           │
           ▼
     Zabbix Proxy
           │
           ▼
      Zabbix Server
           │
           ▼
       Dashboard
```

## Scripts

### `host.py`

Collects Xen host/pool-related monitoring information.

### `vm.py`

Collects virtual-machine-related monitoring information.

### `pass_config.py`

Contains configuration used by the monitoring scripts.

> Do not store production passwords, API credentials, tokens, or other secrets directly in the repository.

### `cron_host.sh`

Used to schedule host-related monitoring operations.

### `cron_vm.sh`

Used to schedule VM-related monitoring operations.

## Deployment

Clone the repository:

```bash
git clone https://github.com/nemesisgpX07/Xen-Pools-Monitoring-through-Zabbix.git
```

Enter the directory:

```bash
cd Xen-Pools-Monitoring-through-Zabbix
```

Configure the required Xen and Zabbix parameters and then configure the required cron jobs.


