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

    def listening(self):
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            message = message.decode()
            print('receive', clientAddress, message)


if argv[1] == 'dv':
    node = DvNode(argv[2:])
    print('neighbors', node.neighbors)











