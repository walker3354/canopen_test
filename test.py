#!/usr/bin/python3
# sudo ifconfig can0 txqueuelen 10000
# sudo ip link set can0 up type can bitrate 1000000
import tomli
import time
import canopen
import socketio

import typing

sio = socketio.Client()


@sio.event
def connect():
    print('connection established')


@sio.event
def my_message(data):
    print('message received with', data)
    sio.emit('response', {"response": 'my response'})


@sio.event
def disconnect():
    print('disconnect from server')


class CsCanOpen:
    def __init__(self, can_interface, config_file):
        self.porx_node_list = []
        self.light_node_list = []

        self.control_id = 0
        self.pre_control_id = 0
        self.control_id_temp = 0

        self.led_change = False
        self.led_flag = False

        self.send_key = False
        self.start_time = 0
        self.map_control = False
        self.message_key = True

        self.config = self.load_config(config_file)
        self.can_network = self.canopen_init(can_interface)
        self.load_light_nodes(self.config["light"])
        self.load_prox_nodes(self.config["proximity"])
        self.prox_dict = {'right': 0, 'left': 0}

    def load_config(self, config_file):
        with open(config_file, "rb") as f:
            toml_dict = tomli.load(f)
            return toml_dict

    def canopen_init(self, can_interface="can0"):
        network = canopen.Network()
        network.connect(channel=can_interface, bustype='socketcan')
        return network

    def load_light_nodes(self, config):
        print('loading light nodes')
        for node in config["nodes"]:
            print("Wait for light_node {0:} ready...".format(node["node_id"]))
            can_node = self.can_network.add_node(
                node["node_id"], config["config_file"])
            can_node.rpdo.read()
            can_node.nmt.wait_for_heartbeat()
            self.light_node_list.append(can_node)
        print("\nCheck all light nodes completed!\tinitila all light nodes\n")
        for light_node in self.light_node_list:
            light_node.nmt.state = 'PRE-OPERATIONAL'
            light_node.rpdo[1][0x6001].phys = 0
            light_node.rpdo[1].start(0.5)
        print("initial complete!")

    def load_prox_nodes(self, config):
        print('\nloading prox_nodes\n')
        for node in config["nodes"]:
            print("Wait for prox_node {0:} ready...".format(node["node_id"]))
            can_node = self.can_network.add_node(
                node["node_id"], config["config_file"])
            can_node.tpdo.read()
            can_node.nmt.wait_for_heartbeat()
            self.porx_node_list.append(can_node)
        print("Check all prox nodes completed!")
        for node in self.porx_node_list:
            node.tpdo[1].add_callback(self.proximity_callback)

    def proximity_callback(self, msg):
        node_id = msg.cob_id - 384
        for var in msg:
            # print(node_id, " : ", var.raw)
            if var.raw < 15 and self.send_key == 0:
                self.control_id_temp = node_id
                self.send_key = 1
                self.start_time = time.time()
            elif var.raw > 15 and node_id == self.control_id_temp:
                self.send_key = 0

            if self.map_control == 1 and (time.time() - self.start_time) > 2 and self.send_key == 1:
                if self.control_id_temp == self.control_id + 1 or (self.control_id_temp == 43 and self.control_id == 10):
                    self.prox_dict['right'] = 1
                    self.send_key = 0
                elif self.control_id_temp == self.control_id - 1 or (self.control_id_temp == 10 and self.control_id == 43):
                    self.prox_dict['left'] = 1
                    self.send_key = 0
                elif self.control_id_temp == self.control_id and (time.time() - self.start_time) > 3:
                    self.send_key = 0
                    self.map_control = 0
                    self.control_id_temp = 0
                    print('release control')
                    for light_node in self.light_node_list:
                        light_node.rpdo[1][0x6001].phys = 0
                        light_node.rpdo[1].start(0.2)

            if self.send_key == 1 and (time.time() - self.start_time) > 3 and self.map_control == 0:
                self.control_id = self.control_id_temp
                self.send_key = 0
                print(self.control_id)
                self.led_change = not self.led_change
                self.map_control = True
                for light_node in self.light_node_list:
                    light_node.rpdo[1][0x6001].phys = self.control_id
                    light_node.rpdo[1].start(0.2)

    @sio.event
    def swap_event_watcher(self):
        while True:
            if self.prox_dict['left'] == 1:
                sio.emit('GESTURE', 'SWAP_LEFT')
                print('swap_left')
                self.prox_dict['left'] = 0

            if self.prox_dict['right'] == 1:
                sio.emit('GESTURE', 'SWAP_RIGHT')
                print('swap_right')
                self.prox_dict['right'] = 0

    def disconnect(self):
        self.can_network.disconnect()


def main():
    sio.connect('ws://10.100.1.51:5010')
    cs_canopen = CsCanOpen("can0", "./walker_tw_island.toml")
    cs_canopen.swap_event_watcher()


if __name__ == "__main__":
    main()
