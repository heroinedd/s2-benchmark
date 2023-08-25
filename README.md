# Overview

This project is used to generate benchmarks (large fattree topologies configured with bgp/ospf with shortest-path or valley-free routing policy) for distributed-batfish testing.

## OSPF fattrees
For OSPF fattrees, there's no difference between shortest-path and valley-free.

In the following, we use *x* to represent the id of each router (i.e., the number after '-' in the router name. For example, the id of core-0 is 0).

### Edge routers

For each <u>edge</u> router:

#### Interfaces

1. One <u>Loopback</u> interface (70.0.*x*.0/32).
2. Several <u>Serial</u> interfaces (10.0.*x*.?) to connect to aggregation routers.
3. Several <u>Ethernet</u> interfaces (70.0.*x*.?) towards hosts.

#### Static routes
One static route against 70.0.*x*.0/24.

#### OSPF

Passive interfaces: Loopback and Ethernet interfaces.

Network: 10.0.0.0/8

Redistribute: static routes

### Aggregation routers

For each <u>aggregation</u> router:

#### Interfaces

1. One <u>Loopback</u> interface (70.0.*x*.0/32).
2. Several <u>Serial</u> interfaces (10.0.*x*.?) to connect to edge, core and other aggregation routers.

#### OSPF

Passive interfaces: Loopback interface.

Network: 10.0.0.0/8

### Core routers

For each <u>core</u> router:

#### Interfaces

1. One <u>Loopback</u> interface (70.0.*x*.0/32).
2. Several <u>Serial</u> interfaces (10.0.*x*.?) to connect to aggregation routers.

#### OSPF

Passive interfaces: Loopback interface.

Network: 10.0.0.0/8

## BGP fattrees