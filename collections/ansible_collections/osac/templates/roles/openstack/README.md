# openstack

Provisions networking resources using OpenStack Neutron.

## Resources

### VirtualNetwork


### Subnet


### SecurityGroup


## Implementation Strategy

This role implements the `openstack` NetworkClass strategy using OpenStack Neutron. The implementation follows these patterns:


## Task Files

- `tasks/create_virtual_network.yaml` - Creates ClusterUserDefinedNetwork CR from VirtualNetwork resource
- `tasks/delete_virtual_network.yaml` - Removes ClusterUserDefinedNetwork CR
- `tasks/create_subnet.yaml` - Creates namespace with CUDN labels from Subnet resource
- `tasks/delete_subnet.yaml` - Removes namespace
- `tasks/create_security_group.yaml` - Creates NetworkPolicy resources from SecurityGroup rules
- `tasks/delete_security_group.yaml` - Removes NetworkPolicy resources

## Usage

### Example: VirtualNetwork Provisioning

```yaml
- name: Create VirtualNetwork
  ansible.builtin.include_role:
    name: openstack
    tasks_from: create_virtual_network
  vars:
    virtual_network: "{{ ansible_eda.event.payload }}"
    virtual_network_name: "{{ ansible_eda.event.payload.metadata.name }}"
```

### Example: Subnet Provisioning

```yaml
- name: Create Subnet
  ansible.builtin.include_role:
    name: openstack
    tasks_from: create_subnet
  vars:
    subnet: "{{ ansible_eda.event.payload }}"
    subnet_name: "{{ ansible_eda.event.payload.metadata.name }}"
```

### Example: SecurityGroup Provisioning

```yaml
- name: Create SecurityGroup
  ansible.builtin.include_role:
    name: openstack
    tasks_from: create_security_group
  vars:
    security_group: "{{ ansible_eda.event.payload }}"
```
