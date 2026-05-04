# Bare Metal Agent Import

This is a temporary solution for importing bare metal servers as Assisted
Installer agents using BareMetalHost CRs (OpenShift Baremetal Operator / Ironic).
It will be replaced by the OSAC Bare Metal management operators: BM Pool Operator,
Host Inventory Operator, and Host Management Operator.

## Overview

The `playbook_osac_import_agents.yml` playbook reconciles a file-based server
inventory against BareMetalHost and Agent CRs on the cluster. It:

1. Creates an InfraEnv if one does not exist
2. Creates a BareMetalHost CR for each server in the inventory
3. Deletes BareMetalHost and Agent CRs for servers removed from the inventory
4. Waits for each server to boot the discovery ISO and register as an Agent
5. Labels agents with resource class and Netris server name metadata

The playbook is idempotent and designed to run periodically via an AAP schedule.

## How It Works

```
Inventory File (ConfigMap)
        |
        v
  playbook_osac_import_agents.yml
        |
        v
  BareMetalHost CR  --->  Baremetal Operator (Ironic)
        |                         |
        |                   boots server with
        |                   discovery ISO via
        |                   virtual media
        |                         |
        v                         v
  BMAC Controller  <---  Agent registers with
  (assisted-service)      assisted-service
        |
        v
  Agent CR (labeled with resource_class, netris server name)
```

The Bare Metal Agent Controller (BMAC) in assisted-service handles the
coordination between BareMetalHost and Agent CRs:

- When a BMH is created with the `infraenvs.agent-install.openshift.io` label,
  BMAC sets `customDeploy.method: start_assisted_install` on the BMH
- Ironic boots the server using the InfraEnv discovery ISO via virtual media
- The discovery agent on the server registers with assisted-service, creating
  an Agent CR
- BMAC links the Agent to the BMH via the `agent-install.openshift.io/bmh` label
- The playbook then labels the Agent with resource class and Netris metadata

## Prerequisites

### Baremetal Operator with watchAllNamespaces

The Baremetal Operator (BMO) must be configured to watch BareMetalHost CRs
outside the default `openshift-machine-api` namespace. The playbook creates
BMHs in the agent namespace (`hardware-inventory` by default).

Patch the Provisioning CR:

```bash
kubectl patch provisioning provisioning-configuration \
  --type merge -p '{"spec":{"watchAllNamespaces": true}}'
```

### Agent Namespace

The agent namespace (default `hardware-inventory`) must exist. All BMH CRs,
Agent CRs, InfraEnv, BMC secrets, and the pull secret live in this namespace.

```bash
kubectl create namespace hardware-inventory
```

### Pull Secret

A pull secret must exist in the agent namespace for the InfraEnv to generate
a discovery ISO. The playbook references this via the `import_agents_pull_secret_name`
variable (default `pull-secret`).

```bash
kubectl create secret docker-registry pull-secret \
  -n hardware-inventory \
  --from-file=.dockerconfigjson=pull-secret.json
```

### BMC Secrets

Each server needs a Kubernetes Secret with its BMC credentials in the agent
namespace. The secret name must match the `bmc_secret` field in the server
inventory.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: <server-name>-bmc-secret
  namespace: hardware-inventory
type: Opaque
data:
  username: <base64-encoded>
  password: <base64-encoded>
```

### BMC Network Access

The cluster must have network access to the BMC endpoints of the servers.
The BMC address in the inventory uses the Redfish virtual media protocol
(e.g., `redfish-virtualmedia+https://192.168.111.1:8000/redfish/v1/Systems/<uuid>`).

### Server Inventory ConfigMap

For AAP scheduled runs, the server inventory is mounted from a ConfigMap
named `import-agents-inventory` in the AAP namespace. The ConfigMap must
contain a `servers.yml` key:

```bash
kubectl create configmap import-agents-inventory \
  -n <aap-namespace> \
  --from-file=servers.yml=my-servers.yml
```

## Server Inventory Format

```yaml
servers:
  - name: node001
    bmc_url: "redfish-virtualmedia+https://192.168.1.21:8000/redfish/v1/Systems/<uuid>"
    bmc_secret: "node001-bmc-secret"
    boot_mac: "AA:BB:CC:DD:EE:01"
    netris_server_name: "server-01"
    resource_class: "fc430"
  - name: node002
    bmc_url: "redfish-virtualmedia+https://192.168.1.22:8000/redfish/v1/Systems/<uuid>"
    bmc_secret: "node002-bmc-secret"
    boot_mac: "AA:BB:CC:DD:EE:02"
    netris_server_name: "server-02"
    resource_class: "fc430"
```

| Field | Description |
|-------|-------------|
| `name` | Server name, used as the BMH CR name and Agent hostname |
| `bmc_url` | Redfish BMC address for virtual media boot |
| `bmc_secret` | Name of the K8s Secret with BMC credentials (in agent namespace) |
| `boot_mac` | Boot NIC MAC address, used to match Agent to server |
| `netris_server_name` | Netris server name label for the Agent |
| `resource_class` | Resource class label for the Agent (e.g., hardware type) |
| `disable_bmc_cert_verification` | (Optional) Per-server override for BMC TLS certificate verification (default: `true`) |

## Running Locally

```bash
ansible-playbook playbook_osac_import_agents.yml \
  -e @samples/import_agents_extra_vars.yml
```

Sample files are provided in `samples/`:
- `import_agents_extra_vars.yml` - server inventory
- `import_agents_bmc_secrets.yml` - BMC secrets (apply with `kubectl apply -f`)

## AAP Scheduled Runs

The playbook is configured in AAP config-as-code with a periodic schedule
(every 10 minutes). The schedule is controlled by the `OSAC_IMPORT_AGENTS_ENABLED`
environment variable, set in the `config-as-code-ig` Secret. It defaults to
disabled.

To enable:
1. Set `OSAC_IMPORT_AGENTS_ENABLED=true` in the config-as-code-ig Secret
2. Create the `import-agents-inventory` ConfigMap in the AAP namespace
3. Create BMC secrets in the agent namespace
4. Run config-as-code to apply the schedule

The playbook runs in the `cluster-fulfillment-ig` instance group, which
mounts the `import-agents-inventory` ConfigMap at `/var/config/import-agents/`.

## Playbook Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `import_agents_namespace` | `hardware-inventory` | Namespace for BMH, Agent, InfraEnv, and BMC secrets |
| `import_agents_infraenv_name` | `infraenv` | InfraEnv CR name |
| `import_agents_inventory_path` | `/var/config/import-agents/servers.yml` | Path to the server inventory file |
| `import_agents_pull_secret_name` | `pull-secret` | Pull secret name for InfraEnv |
| `import_agents_disable_bmc_cert_verification` | `true` | Default BMC TLS cert verification skip (can be overridden per-server) |

## Removing Servers

To remove a server, delete its entry from the inventory file (or ConfigMap)
and run the playbook. The playbook will:

1. Find the Agent CR linked to the stale BMH (via `agent-install.openshift.io/bmh` label)
2. Delete the Agent CR
3. Delete the BareMetalHost CR

The agent must be deleted before the BMH because assisted-service removes the
BMH-to-Agent link label when the BMH is deleted.
