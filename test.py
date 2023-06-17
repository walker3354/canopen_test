#!/usr/bin/python3
# sudo ifconfig can0 txqueuelen 10000
# sudo ip link set can0 up type can bitrate 1000000
import tomli
import time
import canopen


class CsCanOpen:
    def __init__(self, can_interface, config_file):
        self.porx_node_list = []
        self.light_node_list = []
        self.control_id
        self.pre_control_id
        self.config = self.load_config(config_file)
        self.can_network = self.canopen_init(can_interface)
        self.load_light_nodes(self.config["light"])
        self.load_prox_nodes(self.config["proximity"])

    def load_config(self, config_file):
        with open(config_file, "rb") as f:
            toml_dict = tomli.load(f)
            return toml_dict

    def canopen_init(self, can_interface="can0"):
        network = canopen.Network()
        network.connect(channel=can_interface, bustype='socketcan')
        return network

    def load_light_nodes(self, config):
        for node in config["nodes"]:
            can_node = self.can_network.add_node(
                node["node_id"], config["config_file"])
            can_node.nmt.wait_for_heartbeat()
            self.light_node_list.append(can_node)
        print("Check all light nodes completed!\n")

    def load_prox_nodes(self, config):
        # node_set = {}
        for node in config["nodes"]:
            print("Wait for node {0:} ready...".format(node["node_id"]))
            can_node = self.can_network.add_node(
                node["node_id"], config["config_file"])
            can_node.nmt.wait_for_heartbeat()
            self.porx_node_list.append(can_node)
            # node_set[node["node_id"]] = {"transform": node["transform"], "obj": can_node, "active_cnt": 0}
        print("Check all prox nodes completed!")
        for node in self.porx_node_list:
            node.tpdo.read()
            self.control_id = self.cnode.tpdo[1].add_callback(
                self.proximity_callback)
            if self.control_id != 0:
                for light_node in self.light_node_list:
                    light_node.rpdo.read()
                    light_node.nmt.state = 'PRE-OPERATIONAL'
                    node.rpdo[1][0x6001].phys = self.control_id
                    node.rpdo[1].start(1)
                    node.rpdo[1].stop()
                    self.pre_control_id = self.control_id
                    self.control_id = 0
            elif self.control_id == self.pre_control_id:
                for light_node in self.light_node_list:
                    light_node.rpdo.read()
                    light_node.nmt.state = 'PRE-OPERATIONAL'
                    node.rpdo[1][0x6001].phys = 0
                    node.rpdo[1].start(1)
                    node.rpdo[1].stop()
                    self.pre_control_id = 0
                    self.control_id = 0

    def proximity_callback(self, msg):
        node_id = msg.cob_id - 384
        for var in msg:
            self.gesture.update_prox(node_id, var.raw)
            if var.raw < 50:
                return node_id

    def disconnect(self):
        self.can_network.disconnect()


def main():
    cs_canopen = CsCanOpen("can0", "./tw-island-dev.toml")
    while True:
        time.sleep(1)
    return
    '''
    light_network = canopen.Network()
    light_network.connect(channel="can0", bustype='socketcan')
    node = light_network.add_node(
        25, 'DS301_profile_mcu.eds')
    node.rpdo.read()
    node.nmt.state = 'PRE-OPERATIONAL'
    # print(node.rpdo.len())
    node.rpdo[1][0x6001].phys = 0x01
    node.rpdo[1].start(0.1)
    node.nmt.state = 'OPERATIONAL'
    time.sleep(2)
    node.rpdo[1][0x6001].phys = 0x00
    time.sleep(2)
    node.rpdo[1].stop()
    return
    '''


if __name__ == "__main__":
    main()
