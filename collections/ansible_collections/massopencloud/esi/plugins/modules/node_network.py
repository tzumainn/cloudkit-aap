#!/usr/bin/python

DOCUMENTATION = r'''
---
module: node_network
short_description: Attaches/detaches networks to/from a baremetal node
description:
  - Attach or detach Neutron networks to or from an Ironic node
  - When state is present, attaches the specified networks to the node
  - When state is absent with networks specified, detaches those specific networks
  - When state is absent with no networks specified, detaches all networks
options:
  networks:
    description:
      - List of network names or IDs to attach or detach
      - Required when state is present
      - Optional when state is absent (if not specified, all networks are detached)
    type: list
    elements: str
  node:
    description:
      - The name or ID of the node
    required: true
    type: str
  state:
    description:
      - Indicates whether the networks should be present or absent
    choices: ['present', 'absent']
    default: present
    type: str
extends_documentation_fragment:
  - openstack.cloud.openstack
'''

EXAMPLES = r'''
- name: Attach a single network to a node
  massopencloud.esi.node_network:
    cloud: "devstack"
    state: "present"
    node: "MOC-R4PAC67U12-S3"
    networks:
      - "hypershift"

- name: Attach multiple networks to a node
  massopencloud.esi.node_network:
    cloud: "devstack"
    state: "present"
    node: "MOC-R4PAC67U12-S3"
    networks:
      - "hypershift"
      - "provisioning"
      - "storage"

- name: Detach specific networks from a node
  massopencloud.esi.node_network:
    cloud: "devstack"
    state: "absent"
    node: "MOC-R4PAC67U12-S3"
    networks:
      - "hypershift"
      - "old-network"

- name: Detach all networks from a node
  massopencloud.esi.node_network:
    cloud: "devstack"
    state: "absent"
    node: "MOC-R4PAC67U12-S3"
'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import (
        OpenStackModule
)


class NodeNetworkModule(OpenStackModule):
    argument_spec = dict(
        networks=dict(type='list', elements='str'),
        node=dict(required=True),
        state=dict(default='present', choices=['present', 'absent']),
    )
    module_kwargs = dict(
        required_if=[
            ['state', 'present', ['networks']],
        ],
    )

    def run(self):
        node = self.conn.baremetal.find_node(self.params['node'],
                                             ignore_missing=False)
        networks = self.params['networks'] or []

        baremetal_ports = list(self.conn.baremetal.ports(
            details=True, node_id=node.id))

        changed = False

        if self.params['state'] == 'present':
            for network_name in networks:
                network_port = self._find_or_create_network_port(
                    node.name, network_name)

                baremetal_port = self._find_matching_baremetal_port(
                    baremetal_ports, network_port)
                if baremetal_port:
                    continue

                baremetal_port = self._find_free_baremetal_port(baremetal_ports)
                if not baremetal_port:
                    self.fail_json(msg='Node %s has no free ports \
                        for network %s' % (node.id, network_name))

                self.conn.baremetal.attach_vif_to_node(
                    node, network_port.id, port_id=baremetal_port.id)
                changed = True

        elif self.params['state'] == 'absent':
            if networks:
                for network_name in networks:
                    network_port = self._find_or_create_network_port(
                        node.name, network_name)
                    if not network_port:
                        continue

                    baremetal_port = self._find_matching_baremetal_port(
                        baremetal_ports, network_port)
                    if baremetal_port:
                        self.conn.baremetal.detach_vif_from_node(
                            node, network_port.id)
                        self.conn.network.delete_port(network_port.id)
                        changed = True
            else:
                for bp in baremetal_ports:
                    if 'tenant_vif_port_id' in bp.internal_info:
                        self.conn.baremetal.detach_vif_from_node(
                            node, bp.internal_info['tenant_vif_port_id'])
                        self.conn.network.delete_port(
                            bp.internal_info['tenant_vif_port_id'])
                        changed = True

        else:
            self.fail_json(
                msg='Invalid choice for "state": %s' % self.params['state'])

        self.exit_json(changed=changed)

    def _find_or_create_network_port(self, node_name, network):
        network = self.conn.network.find_network(network, ignore_missing=False)
        port_name = "%s-%s" % (node_name, network.name)
        existing_ports = list(self.conn.network.ports(name=port_name))

        if existing_ports:
            return existing_ports[0]

        elif self.params['state'] == 'present':
            return self.conn.network.create_port(
                name=port_name,
                network_id=network.id,
                device_owner='baremetal:none'
            )

        return None

    def _find_matching_baremetal_port(self, baremetal_ports, network_port):
        if network_port is None:
            return None

        for bp in baremetal_ports:
            if bp.internal_info.get('tenant_vif_port_id') == network_port.id:
                return bp

        return None

    def _find_free_baremetal_port(self, baremetal_ports):
        for bp in baremetal_ports:
            if "tenant_vif_port_id" not in bp.internal_info:
                return bp

        return None


def main():
    module = NodeNetworkModule()
    module()


if __name__ == "__main__":
    main()
