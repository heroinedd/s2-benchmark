import os

import networkx as nx


def createDirectory(fname):
    if not os.path.exists(fname):
        os.mkdir(fname)


directory_name = "networks"
createDirectory(directory_name)


def interface_ips(i):
    x = i // 256
    y = i % 256

    z = x // 256
    x = x % 256
    ret = str(10 + z) + "." + str(x) + "." + str(y) + "."
    return (ret + "0", ret + "1")


def network(i, k):
    if k >= 256:
        raise ValueError('k must be < 256')
    x = i // 256
    y = i % 256
    ret = "70." + str(x) + "." + str(y)
    subnets = [ret + "." + str(j * 2) + "/31" for j in range(k)]
    ret = ret + ".0/24"
    return (ret, subnets)


def fat_tree_topology(k):
    if type(k) is not int:
        raise TypeError('k argument must be of int type')
    if k < 1 or k % 2 == 1:
        raise ValueError('k must be a positive even integer')

    topo = nx.DiGraph()
    topo.graph['k'] = k

    # Create core nodes
    n_core = (k // 2) ** 2

    counter = 0
    counter_net = 0

    dest = ""
    src = ""

    # Add core nodes
    for v in range(int(n_core)):
        (net, subnets) = network(counter_net, 0)
        counter_net += 1
        name = 'core-' + str(v)
        topo.add_node(v, layer='core', type='switch', name=name, net=net, subnets=subnets)

    # Create aggregation and edge nodes and connect them
    for pod in range(k):
        aggr_start_node = topo.number_of_nodes()
        aggr_end_node = aggr_start_node + k // 2
        edge_start_node = aggr_end_node
        edge_end_node = edge_start_node + k // 2
        aggr_nodes = range(aggr_start_node, aggr_end_node)
        edge_nodes = range(edge_start_node, edge_end_node)

        # Create aggregation nodes
        for i in range(aggr_start_node, aggr_end_node):
            (net, subnets) = network(counter_net, 0)
            counter_net += 1
            name = 'aggregation-' + str(i)
            topo.add_node(i, layer='aggregation', type='switch', pod=pod, name=name, net=net, subnets=subnets)

        # Create edge nodes
        for i in range(edge_start_node, edge_end_node):
            (net, subnets) = network(counter_net, 2)
            counter_net += 1
            name = 'edge-' + str(i)
            topo.add_node(i, layer='edge', type='switch', pod=pod, name=name, net=net, subnets=subnets)

            if pod == 0 and i == edge_start_node:
                dest = name
            elif pod == k - 1 and i == edge_end_node - 1:
                src = name

        # Add edges between them
        for u in aggr_nodes:
            for v in edge_nodes:
                (ip1, ip2) = interface_ips(counter)
                counter = counter + 1
                topo.add_edge(u, v, type="aggregation_edge", ips=(ip1, ip2))
                topo.add_edge(v, u, type="aggregation_edge", ips=(ip2, ip1))

    # Connect core switches to aggregation switches
    for core_node in range(n_core):
        for pod in range(k):
            aggr_node = n_core + (core_node // (k // 2)) + (k * pod)
            (ip1, ip2) = interface_ips(counter)
            counter = counter + 1
            topo.add_edge(core_node, aggr_node, type='core_aggregation', ips=(ip1, ip2))
            topo.add_edge(aggr_node, core_node, type='core_aggregation', ips=(ip2, ip1))

    return (topo, dest, src)


def makeDirected(g, i):
    g = nx.DiGraph(g)
    ifacemap = {}
    netmap = {}
    subnetmap = {}
    namemap = {}
    counter = 0
    for n in g.nodes():
        (net, subnets) = network(counter, i)
        namemap[n] = "R" + str(counter)
        netmap[n] = net
        subnetmap[n] = subnets
        counter += 1
    counter = 0
    seen = set()
    for (x, y) in g.edges():
        if (x, y) in seen:
            continue
        seen.add((x, y))
        seen.add((y, x))
        (ip1, ip2) = interface_ips(counter)
        counter += 1
        ifacemap[(x, y)] = (ip1, ip2)
        ifacemap[(y, x)] = (ip2, ip1)
    nx.set_node_attributes(g, 'name', namemap)
    nx.set_node_attributes(g, 'net', netmap)
    nx.set_node_attributes(g, 'subnets', subnetmap)
    nx.set_edge_attributes(g, 'ips', ifacemap)
    return g


def jellyFish(n):
    seed = 1
    g = nx.random_regular_graph(3, n, seed)
    return makeDirected(g, 1)


def fullMesh(n):
    g = nx.complete_graph(n)
    return makeDirected(g, 1)


def ring(n):
    seed = 1
    prob_rewiring = 0.0
    g = nx.watts_strogatz_graph(n, 2, prob_rewiring, seed)
    return makeDirected(g, 1)


def createScriptAllSrc(dir_name, idx):
    # dname = directory_name + os.path.sep + dir_name
    # createDirectory(dname)
    dname = directory_name + os.path.sep + dir_name + str(idx)
    createDirectory(dname)
    fname = dname + os.path.sep + "commands-allsrc"
    f = open(fname, 'w')
    f.write('init-testrig ' + dname + '\n')
    f.write('get ai-reachability finalIfaceRegex="Ethernet.*", useAbstraction=True \n')
    f.close()


def createScriptSingleSrc(dir_name, dest, src):
    print("Single src reachability")
    createDirectory(dir_name)
    fname = dir_name + os.path.sep + "commands-singlesrc"
    f = open(fname, 'w')
    f.write('init-testrig ' + dir_name + '\n')
    f.write('get ai-reachability ingressNodeRegex="{}", finalNodeRegex="{}", useAbstraction=True \n'.format(src, dest))
    f.close()


def createConfigs(topo, dir_name, dest, bgp=True, valleyfree=False):
    createDirectory(dir_name)
    config_name = dir_name + os.path.sep + "configs"
    createDirectory(config_name)
    for n in topo.nodes():
        data = topo.nodes[n]
        name = data['name']
        net = data['net']
        subnets = data['subnets']
        fname = config_name + os.path.sep + name + '.cfg'
        f = open(fname, 'w')
        f.write('!\n')
        f.write('! Last configuration change at 14:32:22 UTC Wed Oct 11 2017 by demo\n')
        f.write('!\n')
        f.write('version 15.2\n')
        f.write('service timestamps debug datetime msec\n')
        f.write('service timestamps log datetime msec\n')
        f.write('!\n')
        f.write('hostname ' + name + '\n')
        f.write('!\n')
        f.write('boot-start-marker\n')
        f.write('boot-end-marker\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('aaa new-model\n')
        f.write('!\n')
        f.write('!\n')
        f.write('aaa authorization exec default local\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('aaa session-id common\n')
        f.write('no ip icmp rate-limit unreachable\n')
        f.write('ip cef\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('no ip domain lookup\n')
        f.write('ip domain name demo.com\n')
        f.write('no ipv6 cef\n')
        f.write('!\n')
        f.write('!\n')
        f.write('multilink bundle-name authenticated\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('username demo privilege 15 password 0 demo\n')
        f.write('!\n')
        f.write('!\n')
        f.write('ip tcp synwait-time 5\n')
        f.write('ip ssh source-interface GigabitEthernet0/0\n')
        f.write('ip ssh rsa keypair-name lhr-fw-02.demo.com\n')
        f.write('ip ssh version 2\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write("interface Loopback0\n")
        f.write("  ip address " + net[:-3] + "/32\n")
        f.write("!\n")

        counter = 0
        for (m, edge) in topo[n].items():
            # print(topo[n])
            (iface, p_iface) = edge['ips']
            f.write("interface Serial" + str(counter) + "\n")
            counter = counter + 1
            f.write("  ip address " + iface + "/31\n")
            f.write('  media-type gbic\n')
            f.write('  speed 1000\n')
            f.write('  duplex full\n')
            f.write('  no negotiation auto\n')
            f.write('  no cdp enable\n')
            f.write("!\n")

        counter = 0
        for sub in subnets:
            f.write("interface Ethernet" + str(counter) + "\n")
            counter = counter + 1
            f.write("  ip address " + sub + "\n")
            f.write('  media-type gbic\n')
            f.write('  speed 1000\n')
            f.write('  duplex full\n')
            f.write('  no negotiation auto\n')
            f.write('  no cdp enable\n')
            f.write("!\n")

        if bgp:
            f.write("router bgp " + str(n + 1) + "\n")  # use str(n + 1) to avoid AS Number 0
            f.write("  maximum-paths 64 \n")
            f.write("  bgp bestpath as-path multipath-relax\n")

            if len(subnets) > 0:
                f.write("  network " + net + "\n")

            # print("node", n, "name", name)
            for (m, edge) in topo[n].items():
                (iface, p_iface) = edge['ips']
                # use str(m + 1) to avoid AS Number 0
                f.write("  neighbor " + p_iface + " remote-as " + str(m + 1) + "\n")
                f.write("  neighbor " + p_iface + " send-community\n")

                nbr_name = topo.nodes[m]["name"]
                # print("m", m, "m_name", nbr_name)
                # print("edge", edge)

                if valleyfree:
                    if "aggregation" in name and "edge" in nbr_name:
                        # print("aggr -> edge")
                        f.write("  neighbor " + p_iface + " route-map " + " set_communities " + "out\n")

                    elif "aggregation" in name and "core" in nbr_name:
                        # print("aggr -> core")
                        f.write("  neighbor " + p_iface + " route-map " + " filter_comm " + "out\n")

                    elif "edge" in name and "aggregation" in nbr_name:
                        # print("edge -> aggr")
                        if name == dest:
                            # print("found dest")
                            f.write("  neighbor " + p_iface + " route-map " + " init_dest " + "out\n")
                        else:
                            f.write("  neighbor " + p_iface + " route-map " + " filter_comm1 " + "out\n")

                    else:
                        # print("default")
                        pass

            f.write("!\n")
            if len(subnets) > 0:
                f.write("ip route " + net + " Null0\n")
                f.write('!\n')

            if valleyfree:
                # define route-maps
                if "aggregation" in name:
                    # define community lists
                    f.write('!\n')
                    f.write("ip bgp-community new-format\n")
                    f.write("ip community-list 1 permit " + "650:100\n")
                    f.write("ip community-list 2 permit " + "650:200\n")
                    f.write('!\n')

                    # define route-map set_communities
                    f.write("route-map set_communities permit 10\n")
                    f.write("  match community 1\n")
                    f.write("  set community 650:200\n")
                    f.write("route-map set_communities permit 20\n")
                    f.write("  match community 2\n")
                    f.write("  set community 650:300\n")
                    f.write("route-map set_communities permit 30\n")
                    f.write("  set community 650:400\n")
                    f.write('!\n')

                    # define route-map filter_comm
                    f.write("route-map filter_comm permit 10\n")
                    f.write("  match community 1\n")
                    f.write("  set community 650:200\n")
                    # implicit deny drops all other routes
                    f.write('!\n')

                elif "edge" in name:
                    if name == dest:
                        f.write("ip bgp-community new-format\n")
                        f.write('!\n')
                        f.write("route-map init_dest permit 10\n")
                        f.write(" set community 650:100\n")
                    else:
                        # define community lists
                        f.write("ip bgp-community new-format\n")
                        f.write("ip community-list 1 permit " + "650:100\n")
                        f.write('!\n')

                        f.write("route-map filter_comm1 permit 10\n")
                        f.write("  match community 1\n")
                        f.write(" set community 650:100\n")  # no change in comm
                        # implicit deny drops all other routes
                        f.write('!\n')
        else:
            f.write("router ospf 1\n")
            f.write("  router-id " + net[:-3] + "\n")

            if len(subnets) > 0:
                # redistribute static routes into ospf
                f.write("  redistribute static subnets\n")

            f.write("  network 10.0.0.0 0.255.255.255 area 1\n")
            f.write("  passive-interface Loopback0\n")

            for counter in range(len(subnets)):
                f.write("  passive-interface Ethernet" + str(counter) + "\n")

            f.write("!\n")

            # write static routes
            if len(subnets) > 0:
                f.write("ip route " + net + " Null0\n")
                f.write('!\n')

        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('ip forward-protocol nd\n')
        f.write('!\n')
        f.write('!\n')
        f.write('no ip http server\n')
        f.write('no ip http secure-server\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('!\n')
        f.write('control-plane\n')
        f.write('!\n')
        f.write('!\n')
        f.write('line con 0\n')
        f.write(' exec-timeout 0 0\n')
        f.write(' privilege level 15\n')
        f.write(' logging synchronous\n')
        f.write(' stopbits 1\n')
        f.write('line aux 0\n')
        f.write(' exec-timeout 0 0\n')
        f.write(' privilege level 15\n')
        f.write(' logging synchronous\n')
        f.write(' stopbits 1\n')
        f.write('line vty 0 4\n')
        f.write(' transport input ssh\n')
        f.write('!\n')
        f.write('!\n')
        f.write('end')


def create(k: int, policy: str, proto: str):
    dir_name = os.path.sep.join(['networks', proto, "ecmp", policy])

    createDirectory(dir_name)
    print('\t'.join([policy, proto, 'fattree' + str(k)]))

    topo, dest, src = fat_tree_topology(k)
    print("k: {}, dest: {}, src: {}".format(k, dest, src))

    dir_name = dir_name + os.path.sep + "fattree" + str(k)
    createConfigs(topo, dir_name, dest, bgp=(proto == "bgp"), valleyfree=(policy == "vf"))
    createScriptSingleSrc(dir_name, dest, src)


if __name__ == '__main__':
    for k in [40, 50]:
        for proto in ["bgp"]:
            createDirectory('networks' + os.path.sep + proto)
            for policy in ["sp"]:
                create(k, policy, proto)
