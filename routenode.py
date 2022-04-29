from socket import *
from sys import argv
import os
import csv
import threading
import re
import time
import datetime


class DvNode(object):
    def __init__(self, argvs):
        self.mode = argvs[0]
        self.port = int(argvs[2])
        self.last = False
        self.neighbors = {}
        if self.parse_argv(argvs):
            self.socket = socket(AF_INET, SOCK_DGRAM)
            self.socket.bind(('', self.port))
        self.dv = {}  # distance vectors
        self.next_hop = {}
        self.vector_init()
        self.ip = '127.0.0.1'

    def parse_argv(self, argvs):
        if argv[-1] == 'last':
            self.last = True
            neighbors = argvs[3:-1]
        elif argv[-2] == 'last':
            self.last = True
            neighbors = argvs[3:-2]
        else:
            neighbors = argvs[3:]
        if len(neighbors) % 2 != 0:
            print('Wrong input of neighbors and costs!')
            return False
        else:
            for i in range(len(neighbors)):
                if i % 2 == 0:
                    self.neighbors[int(neighbors[i])] = int(neighbors[i+1])
        return True

    def vector_init(self):
        self.dv[self.port] = {}
        for neighbor, cost in self.neighbors.items():
            # initialize self distance vector
            self.dv[self.port][neighbor] = cost
            self.next_hop[neighbor] = neighbor
            # initialize neighbors' distance vector
            self.dv[neighbor] = {}

    def broad2neighbor(self):
        msg = 'DV FROM ' + str(self.port)
        # message of self distance vector
        for dest, cost in self.dv[self.port].items():
            msg += ' ' + str(dest) + ' ' + str(cost)
        # send dv to all neighbors
        t = time.time()
        t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
        msg = 'TIME ' + str(t) + ' ' + msg
        for neighbor, cost in self.neighbors.items():
            self.socket.sendto(msg.encode(), (self.ip, neighbor))
            print('[%s] Message sent from Node %s to Node %s'%(t, self.port, neighbor))

    def listening(self):
        print('listening')
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            message = message.decode()
            print('receive', clientAddress, message)


if argv[1] == 'dv':
    node = DvNode(argv[2:])
    print('neighbors', node.neighbors)
    if node.last:
        node.broad2neighbor()
    node.listening()










