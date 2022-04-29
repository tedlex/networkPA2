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
        self.cost_change = None
        self.neighbors = {}
        self.all_nodes = set()
        if self.parse_argv(argvs):
            self.socket = socket(AF_INET, SOCK_DGRAM)
            self.socket.bind(('', self.port))
        self.dv = {}  # distance vectors
        self.next_hop = {}
        self.vector_init()
        self.ip = '127.0.0.1'
        self.at_least_once = 0
        #self.th_display = threading.Thread(target=self.display_routing)

    def parse_argv(self, argvs):
        if argv[-1] == 'last':
            self.last = True
            neighbors = argvs[3:-1]
        elif argv[-2] == 'last':
            self.last = True
            self.cost_change = int(argv[-1])
            neighbors = argvs[3:-2]
        else:
            neighbors = argvs[3:]
        self.all_nodes.add(self.port)
        if len(neighbors) % 2 != 0:
            print('Wrong input of neighbors and costs!')
            return False
        else:
            for i in range(len(neighbors)):
                if i % 2 == 0:
                    self.neighbors[int(neighbors[i])] = int(neighbors[i + 1])
                    self.all_nodes.add(int(neighbors[i]))
        return True

    def vector_init(self):
        self.dv[self.port] = {}
        self.dv[self.port][self.port] = 0
        for neighbor, cost in self.neighbors.items():
            # initialize self distance vector
            self.dv[self.port][neighbor] = cost
            self.next_hop[neighbor] = neighbor
            # initialize neighbors' distance vector
            self.dv[neighbor] = {neighbor: 0}

    def broad2neighbor(self):
        t = time.time()
        # t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
        msg = '[%s] DV' % t
        # message of self distance vector
        for dest, cost in self.dv[self.port].items():
            msg += ' ' + str(dest) + ',' + str(cost)
        # send dv to all neighbors
        for neighbor, cost in self.neighbors.items():
            self.socket.sendto(msg.encode(), (self.ip, neighbor))
            print('[%s] Message sent from Node %s to Node %s' % (
                parse_time(t), self.port, neighbor))

    def recv_DV(self, sender, message):
        self.dv[int(sender)] = {}
        change = False
        for m in re.findall('\d+,\d+', message):
            dest, cost = m.split(',')
            if int(dest) not in self.all_nodes:
                self.all_nodes.add(int(dest))
                #print('收到新node', int(dest))
                change = True  # if a new node is learned, then the dv must will be updated
            self.dv[int(sender)][int(dest)] = int(cost)
        t = re.findall('\[([0-9.]+)\]', message)
        print('[%s] Message received at Node %s from Node %s' % (
            parse_time(float(t[0])), self.port, sender))
        #print('DV', self.dv)
        self.update_routingTable(change)

    def recv_cost_change(self, sender, message):
        m = re.match('\[([0-9.]+)\] COST CHANGE (\d+)', message)
        t, cost = m.groups()
        print('[%s] Link value message received at Node %s from Node %s' % (t, self.port, sender))
        #self.dv[self.port][sender] = int(cost)
        self.neighbors[sender] = int(cost)
        print('[%s] Node %s cost updated to %s' % (t, sender, cost))
        self.update_routingTable()  # 这里直接broadcast也行吧

    def update_routingTable(self, change=False):
        print('准备update')
        print('dv', self.dv)
        # change = False
        for dest in self.all_nodes:
            if dest != self.port:  # cost from self to self is always 0
                #print('准备update到%s的路径' % dest)
                old_routing = (self.dv[self.port].get(dest), self.next_hop.get(dest))
                new_routing = (INFTY, None)  # find min using bellman equation. 既然从某处获得了这个node，一定有一条路径
                for nbr, cost in self.neighbors.items():
                    #print('检查邻居%s的dv: %s' % (nbr, self.dv.get(nbr)))
                    # 可能没有收到邻居的dv，也可能邻居的dv里没有dest
                    if self.dv.get(nbr) is not None:
                        if self.dv[nbr].get(dest) is not None:  # 不能省略is not None， 因为可能值为0
                            #print('dv存在邻居到dest距离，%s + %s' % (cost, self.dv[nbr][dest]))
                            if cost + self.dv[nbr][dest] < new_routing[0]:
                                new_routing = (cost + self.dv[nbr][dest], nbr)
                if new_routing != old_routing:
                    self.dv[self.port][dest] = new_routing[0]
                    self.next_hop[dest] = new_routing[1]
                    print('routing to %s updated from' % dest, old_routing, 'to', new_routing)
                    change = True
        if change:
            #print('routing updated!')
            #i = input('continue to send')
            self.broad2neighbor()
        elif self.at_least_once == 0:
            self.at_least_once += 1
            #print('no updated, but first time')
            #i = input('continue to send')
            self.broad2neighbor()
        else:
            #print('no update')
            pass
        self.display_routing()
        #self.th_display.start()

    def display_routing(self):
        t = time.time()
        #print('[%s] Node %s Routing Table' % (t, self.port))
        s = '[%s] Node %s Routing Table' % (t, self.port)
        for n in sorted(list(self.all_nodes)):
            if n != self.port:
                s += '\n- (%s) -> n %s' % (self.dv[self.port][n], n)
                if self.next_hop[n] != n:
                    s += ' ; Next hop -> n %s' % self.next_hop[n]
                #print(r)
        #self.th_display.stop()
        print(s)

    def listening(self):
        print('listening')
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            message = message.decode()
            print('receive', clientAddress, message)
            if re.match('\[[0-9.]+\] DV( \d+,\d+)+', message):
                th = threading.Thread(target=self.recv_DV, args=(clientAddress[1], message))
                th.start()
            elif re.match('\[([0-9.]+)\] COST CHANGE (\d+)', message):
                th = threading.Thread(target=self.recv_cost_change, args=(clientAddress[1], message))
                th.start()

    def timer(self):
        time.sleep(10)
        print('----------------------')
        target = max(self.neighbors)
        self.neighbors[target] = self.cost_change
        #self.dv[self.port][target] = self.cost_change
        t = time.time()
        print('[%s] Node %s cost updated to %s' %(t, target, self.cost_change))
        control = '[%s] COST CHANGE %s' %(t, self.cost_change)
        self.socket.sendto(control.encode(), (self.ip, target))
        print('[%s] Link value message sent from Node %s to Node %s' %(t, self.port, target))
        self.update_routingTable()  # 这里直接broadcast也行吧



def parse_time(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


INFTY = 1E10

if argv[1] == 'dv':
    node = DvNode(argv[2:])
    print('neighbors', node.neighbors)
    if node.last:
        node.broad2neighbor()
    if node.cost_change is not None:
        th = threading.Thread(target=node.timer)
        th.start()
    node.listening()
