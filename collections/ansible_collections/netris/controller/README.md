# netris.controller

Ansible collection for managing Netris controller resources via the REST API (V2).

## Requirements

- Netris controller deployed and reachable
- Valid Netris credentials (username/password)
- `ansible.builtin.uri` for HTTP calls

## CRUD Task Pattern

Each role follows a consistent CRUD pattern with task files:

- `create.yaml` — Create the resource
- `read.yaml` — Query / read the resource
- `delete.yaml` — Delete the resource
- `main.yaml` — Dispatcher that includes the correct task file based on a `<role>_state` variable

## Roles

### auth

Obtain a session cookie for the Netris API (`POST /api/auth`).

**Variables:**
- `netris_controller_url` (required) — Base URL of the Netris controller
- `netris_username` (required) — API username
- `netris_password` (required) — API password (use `no_log`)
- `netris_validate_certs` (default: `true`) — Whether to validate SSL certificates

**Output:** `netris_session_cookie`

### server_cluster

Create or delete a server cluster with attached servers.

**State variable:** `server_cluster_state` (`present` | `absent`)

**Variables:**
- `server_cluster_name` (required) — Name of the server cluster
- `server_cluster_site_id` (required) — Netris site ID
- `server_cluster_servers` — List of server names (strings) or objects with `id`/`name`
- `server_cluster_template_id` — Server cluster template ID
- `server_cluster_tags` — List of tags
- `server_cluster_admin_id` / `server_cluster_admin_name` — Admin tenant

**Output:** `server_cluster_id`, `server_cluster_vpc_id`, `server_cluster_vpc_name`

### server_cluster_template

Read server cluster template details.

**State variable:** `server_cluster_template_state` (default: `read`)

**Variables:**
- `server_cluster_template_id` (required) — ID of the server cluster template

**Output:** `server_cluster_template_data` (full template object), `server_cluster_template_server_nics` (deduplicated list of server NIC names across all vnets)

### nat

Create or delete DNAT/SNAT rules.

**State variable:** `nat_state` (`present` | `absent`)

**Variables:**
- `nat_name` (required) — Name of the NAT rule
- `nat_site_id` (required) — Netris site ID
- `nat_action` — `dnat` or `snat` (default: `dnat`)
- `nat_vpc_id` / `nat_vpc_name` — VPC for the rule
- `nat_protocol` — Protocol (default: `tcp`)
- `nat_source_address`, `nat_destination_address` — Addresses
- `nat_source_port`, `nat_destination_port` — Ports
- DNAT-specific: `nat_dnat_to_ip`, `nat_dnat_to_port`
- SNAT-specific: `nat_snat_to_ip`, `nat_snat_to_pool`

**Output:** `nat_id`

### l4lb

Create or delete L4 load balancers.

**State variable:** `l4lb_state` (`present` | `absent`)

See `meta/argument_specs.yaml` for the full variable list.

### ipam

Query the Netris IPAM for available IPs by subnet purpose.

**State variable:** `ipam_state` (default: `read`)

**Variables:**
- `ipam_site_id` (required) — Netris site ID to filter subnets by
- `ipam_purpose` (default: `nat`) — Subnet purpose to filter by (e.g. `nat`, `load-balancer`)
- `ipam_count` (default: `1`) — Number of IPs to allocate

**Output:** `ipam_allocated_ips` (list of allocated IP addresses)

## Common Variables

Set in group_vars or extra vars:

- `netris_controller_url` — Base URL of the Netris controller (e.g. `https://netris.example.com`)
- `netris_username` — Netris API username
- `netris_password` — Netris API password (use `no_log`)
- `netris_validate_certs` — Set to `false` to skip SSL verification (dev only)

## License

Apache-2.0
