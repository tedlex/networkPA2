from socket import *
from sys import argv
import threading
import re
import time
import random


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
        # self.th_display = threading.Thread(target=self.display_routing)

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
        for neighbor, _ in self.neighbors.items():
            t = time.time()
            msg = '[%s] DV' % t
            for dest, cost in self.dv[self.port].items():
                if self.mode == 'p' and dest != neighbor and self.next_hop.get(dest) == neighbor:
                    cost = INFTY
                    print('[%s] Message sent from Node %s to Node %s with distance to Node %s as inf' % (
                        t, self.port, neighbor, dest))
                msg += ' ' + str(dest) + ',' + str(cost)
            self.socket.sendto(msg.encode(), (self.ip, neighbor))
            print('[%s] Message sent from Node %s to Node %s' % (
                t, self.port, neighbor))

    def recv_DV(self, sender, message):
        self.dv[int(sender)] = {}
        change = False
        for m in re.findall('\d+,\d+', message):
            dest, cost = m.split(',')
            if int(dest) not in self.all_nodes:
                self.all_nodes.add(int(dest))
                # print('?????????node', int(dest))
                change = True  # if a new node is learned, then the dv must will be updated
            self.dv[int(sender)][int(dest)] = int(cost)
        t = re.findall('\[([0-9.]+)\]', message)
        print('[%s] Message received at Node %s from Node %s' % (
            t[0], self.port, sender))
        # print('DV', self.dv)
        self.update_routingTable(change)

    def recv_cost_change(self, sender, message):
        m = re.match('\[([0-9.]+)\] COST CHANGE (\d+)', message)
        t, cost = m.groups()
        print('[%s] Link value message received at Node %s from Node %s' % (t, self.port, sender))
        # self.dv[self.port][sender] = int(cost)
        self.neighbors[sender] = int(cost)
        print('[%s] Node %s cost updated to %s' % (t, sender, cost))
        self.update_routingTable()  # ????????????broadcast?????????

    def update_routingTable(self, change=False):
        # print('??????update')
        # print('dv', self.dv)
        # change = False
        for dest in self.all_nodes:
            if dest != self.port:  # cost from self to self is always 0
                # print('??????update???%s?????????' % dest)
                old_routing = (self.dv[self.port].get(dest), self.next_hop.get(dest))
                new_routing = (INFTY, None)  # find min using bellman equation. ??????????????????????????????node????????????????????????
                for nbr, cost in self.neighbors.items():
                    # print('????????????%s???dv: %s' % (nbr, self.dv.get(nbr)))
                    # ???????????????????????????dv?????????????????????dv?????????dest
                    if self.dv.get(nbr) is not None:
                        if self.dv[nbr].get(dest) is not None:  # ????????????is not None??? ??????????????????0
                            # print('dv???????????????dest?????????%s + %s' % (cost, self.dv[nbr][dest]))
                            if cost + self.dv[nbr][dest] < new_routing[0]:
                                new_routing = (cost + self.dv[nbr][dest], nbr)
                if new_routing != old_routing:
                    self.dv[self.port][dest] = new_routing[0]
                    self.next_hop[dest] = new_routing[1]
                    # print('routing to %s updated from' % dest, old_routing, 'to', new_routing)
                    change = True
        if change:
            # print('routing updated!')
            # i = input('continue to send')
            self.broad2neighbor()
        elif self.at_least_once == 0:
            self.at_least_once += 1
            # print('no updated, but first time')
            # i = input('continue to send')
            self.broad2neighbor()
        else:
            # print('no update')
            pass
        self.display_routing()
        # self.th_display.start()

    def display_routing(self):
        t = time.time()
        # print('[%s] Node %s Routing Table' % (t, self.port))
        s = '[%s] Node %s Routing Table' % (t, self.port)
        for n in sorted(list(self.all_nodes)):
            if n != self.port:
                s += '\n- (%s) -> n %s' % (self.dv[self.port][n], n)
                if self.next_hop[n] != n:
                    s += ' ; Next hop -> n %s' % self.next_hop[n]
                # print(r)
        # self.th_display.stop()
        print(s)

    def listening(self):
        # print('listening')
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            message = message.decode()
            # print('receive', clientAddress, message)
            if re.match('\[[0-9.]+\] DV( \d+,\d+)+', message):
                th = threading.Thread(target=self.recv_DV, args=(clientAddress[1], message))
                th.start()
            elif re.match('\[([0-9.]+)\] COST CHANGE (\d+)', message):
                th = threading.Thread(target=self.recv_cost_change, args=(clientAddress[1], message))
                th.start()

    def timer(self):
        time.sleep(30)
        # print('----------------------')
        target = max(self.neighbors)
        self.neighbors[target] = self.cost_change  # update table ?????????neighbors cost???????????????neighbors?????????dv[self]
        # self.dv[self.port][target] = self.cost_change
        t = time.time()
        print('[%s] Node %s cost updated to %s' % (t, target, self.cost_change))
        control = '[%s] COST CHANGE %s' % (t, self.cost_change)
        self.socket.sendto(control.encode(), (self.ip, target))
        print('[%s] Link value message sent from Node %s to Node %s' % (t, self.port, target))
        self.update_routingTable()  # ????????????broadcast?????????


class LsNode(object):
    def __init__(self, argvs):
        self.mode = argvs[0]
        self.UPDATE_INTERVAL = int(argvs[1])
        self.port = int(argvs[2])
        self.last = False
        self.cost_change = None
        self.neighbors = {}  # neighbors of every node and costs {node1: {nbr1:cost}, node2: {}}
        self.LStable = {}  # {(node1, node2): cost, ...}
        self.routing_table = {}  # {destination:(cost, next_hop), ...}
        self.ROUTING_INTERVAL = 30  # ??????30
        self.first_routing = False  # After first routing, only compute routing if LStable changes
        # self.all_nodes = set()
        if self.parse_argv(argvs):
            self.socket = socket(AF_INET, SOCK_DGRAM)
            self.socket.bind(('', self.port))
        self.build_table()
        self.ip = '127.0.0.1'
        self.next_sequence = 0
        self.activation = False
        self.last_seq = {}  # each nodes' LSA seq that have been sent or forwarded by self

    def parse_argv(self, argvs):
        if argvs[-1] == 'last':
            self.last = True
            neighbors = argvs[3:-1]
        elif argvs[-2] == 'last':
            self.last = True
            self.cost_change = int(argvs[-1])
            neighbors = argvs[3:-2]
        else:
            neighbors = argvs[3:]
        # self.all_nodes.add(self.port)
        if len(neighbors) % 2 != 0:
            print('Wrong input of neighbors and costs!')
            return False
        else:
            self.neighbors[self.port] = {}
            for i in range(len(neighbors)):
                if i % 2 == 0:
                    self.neighbors[self.port][int(neighbors[i])] = int(neighbors[i + 1])
                    # self.all_nodes.add(int(neighbors[i]))
        return True

    def build_table(self):
        # construct table based on self.neighbors
        change = False
        if not self.check_neighbors():
            return False
        for n, nbrs in self.neighbors.items():
            for nbr, cost in nbrs.items():
                link = (n, nbr) if n < nbr else (nbr, n)
                if cost != self.LStable.get(link):
                    self.LStable[link] = cost
                    change = True
        if change:
            self.display_table()
            if self.first_routing:
                self.compute_routing()

    def broadLSA(self):
        t = time.time()
        msg = '[%s] LSA FROM %s SEQ %s' % (t, self.port, self.next_sequence)
        for nbr, cost in self.neighbors[self.port].items():
            msg += ' %s,%s' % (nbr, cost)
        for nbr, _ in self.neighbors[self.port].items():
            self.socket.sendto(msg.encode(), (self.ip, nbr))
            print('[%s] LSA of Node %s with sequence number %s sent to Node %s' % (
                t, self.port, self.next_sequence, nbr))
        self.last_seq[self.port] = self.next_sequence
        self.next_sequence += 1

    def display_table(self):
        t = time.time()
        s = '[%s] Node %s Network topology' % (t, self.port)
        links = sorted(list(self.LStable))
        for link in links:
            s += '\n- (%s) from Node %s to Node %s' % (self.LStable[link], link[0], link[1])
        print(s)

    def check_neighbors(self):
        # ??????????????????neighbors???????????????????????????????????????
        # ????????? ab ??????????????????ba??????????????????????????????None????????????????????????b???LSA
        flag = True
        for n, nbrs in self.neighbors.items():
            for nbr, cost in nbrs.items():
                if self.neighbors.get(nbr) is not None and self.neighbors[nbr].get(n) is not None:
                    if self.neighbors[nbr][n] != cost:
                        flag = False
                        print('???????????????,(%s, %s) = %s, (%s, %s) = %s' % (
                            n, nbr, cost, nbr, n, self.neighbors[nbr][n]))
        return flag

    def listening(self):
        # print('listening')
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            message = message.decode()
            #print('receive', clientAddress, message)
            if re.match('\[[0-9.]+\] LSA FROM (\d+) SEQ (\d+) .+', message):
                th = threading.Thread(target=self.recv_LSA, args=(clientAddress[1], message))
                th.start()
            elif re.match('\[([0-9.]+)\] COST CHANGE (\d+)', message):
                th = threading.Thread(target=self.recv_cost_change, args=(clientAddress[1], message))
                th.start()

    def recv_cost_change(self, sender, message):
        m = re.match('\[([0-9.]+)\] COST CHANGE (\d+)', message)
        t, cost = m.groups()
        print('[%s] Link value message received at Node %s from Node %s' % (t, self.port, sender))
        # self.dv[self.port][sender] = int(cost)
        self.neighbors[self.port][sender] = int(cost)
        self.neighbors[sender][self.port] = int(cost)
        print('[%s] Node %s cost updated to %s' % (t, sender, cost))
        self.build_table()
        self.broadLSA()

    def recv_LSA(self, sender, msg):
        m = re.match('\[([0-9.]+)\] LSA FROM (\d+) SEQ (\d+) .+', msg)
        t, source, seq = m.groups()
        source, seq = int(source), int(seq)
        print('[%s] LSA of Node %s with sequence number %s received from Node %s' % (
            t, source, seq, sender))
        if self.last_seq.get(source) is not None and self.last_seq[source] >= seq:
            # duplicate LSA
            print('[%s] DUPLICATE LSA packet Received, AND Dropped:\n- LSA of Node'
                  ' %s\n- Sequence number %s\n- Received from %s ' % (
                      time.time(), source, seq, sender))
        else:  # new LSA from source
            if self.neighbors.get(source) is None:  # 1st LSA from source
                self.neighbors[source] = {}
            for m in re.findall('\d+,\d+', msg):
                nbr, cost = m.split(',')
                self.neighbors[source][int(nbr)] = int(cost)
                if self.neighbors.get(int(nbr)) is None:
                    self.neighbors[int(nbr)] = {}
                self.neighbors[int(nbr)][source] = int(cost)  # ????????????
            if self.check_neighbors():
                self.build_table()
            # forward LSA
            for nbr, _ in self.neighbors[self.port].items():
                if nbr != sender and nbr != source:
                    self.socket.sendto(msg.encode(), (self.ip, nbr))
                    print('[%s] LSA of Node %s with sequence number %s sent to Node %s' % (
                        time.time(), source, seq, nbr))
            self.last_seq[source] = seq
            #print('seq ??????', self.last_seq)
        # activate
        if not self.activation:
            self.activate()

    def period_LSA(self):
        while True:
            time.sleep(self.UPDATE_INTERVAL + random.random())
            self.broadLSA()

    def activate(self):
        self.activation = True
        #print('Node %s activate!' % self.port)
        self.broadLSA()
        th = threading.Thread(target=self.period_LSA)
        th.start()
        if self.last and self.cost_change is not None:
            th2 = threading.Thread(target=self.link_change)
            th2.start()
        time.sleep(self.ROUTING_INTERVAL)
        self.compute_routing()
        self.first_routing = True

    def link_change(self):
        time.sleep(1.2*self.ROUTING_INTERVAL)
        target = max(self.neighbors[self.port])
        self.neighbors[self.port][target] = self.cost_change
        self.neighbors[target][self.port] = self.cost_change
        t = time.time()
        print('[%s] Node %s cost updated to %s' % (t, target, self.cost_change))
        control = '[%s] COST CHANGE %s' % (t, self.cost_change)
        self.socket.sendto(control.encode(), (self.ip, target))
        print('[%s] Link value message sent from Node %s to Node %s' % (t, self.port, target))
        self.build_table()
        self.broadLSA()

    def compute_routing(self):
        all_nodes = set()
        for link, cost in self.LStable.items():
            all_nodes.add(link[0])
            all_nodes.add(link[1])
        # initilization
        N = set()
        N.add(self.port)
        D = {}
        prev = {}
        for v in all_nodes:
            if v != self.port:
                if self.neighbors[self.port].get(v) is not None:
                    D[v] = self.neighbors[self.port][v]
                    prev[v] = self.port
                else:
                    D[v] = INFTY
        # loop
        while N != all_nodes:
            min_v = (None, INFTY)
            for w, Dw in D.items():
                if w not in N and Dw < min_v[1]:
                    min_v = (w, Dw)
            w = min_v[0]
            N.add(w)
            for v, cost in self.neighbors[w].items():
                if v not in N:
                    if D[w] + cost < D[v]:
                        prev[v] = w
                        D[v] = D[w] + cost
        # routing table
        for v, Dv in D.items():
            next_hop = v
            while prev[next_hop] != self.port:
                next_hop = prev[next_hop]
            self.routing_table[v] = (Dv, next_hop)
        # print routing table
        s = '[%s] Node %s Routing Table' % (time.time(), self.port)
        for dest in sorted(list(self.routing_table)):
            s += '\n-(%s) -> Node %s' % (self.routing_table[dest][0], dest)
            if self.routing_table[dest][1] != dest:
                s += ' ; Next hop -> Node %s' % self.routing_table[dest][1]
        print(s)


INFTY = 1E10

if argv[1] == 'dv':
    node = DvNode(argv[2:])
    # print('neighbors', node.neighbors)
    if node.last:
        node.broad2neighbor()
    if node.cost_change is not None:
        thd = threading.Thread(target=node.timer)
        thd.start()
    node.listening()
elif argv[1] == 'ls':
    node = LsNode(argv[2:])
    if node.last:
        thd = threading.Thread(target=node.activate)
        thd.start()
    node.listening()
