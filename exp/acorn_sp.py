import os
import sys
import time
from datetime import datetime
from typing import List

from pybatfish.client.session import Session
from pybatfish.question.question import load_questions


def get_networks_dir(sp: bool, ospf: bool) -> str:
    # shortest path (sp) or valley free (vf)
    tmp = ['data', 'danw-data', 'acorn_benchmarks', 'networks', 'sp' if sp else 'vf', 'ospf' if ospf else 'bgp']
    return os.path.sep + os.path.sep.join(tmp)


def get_network_name(sp: bool, ospf: bool, net: str) -> str:
    return '_'.join(['acorn', 'sp' if sp else 'vf', 'ospf' if ospf else 'bgp', net])


def get_snapshot_name():
    return 'snapshot-' + _get_date()


def get_output_log(sp: bool, ospf: bool) -> str:
    tmp = ['data', 'danw-data', 'acorn_benchmarks', 'outputs', 'sp' if sp else 'vf', 'ospf' if ospf else 'bgp',
           _get_date(), 'log.txt']
    return _get_path(tmp)


def get_output_routes(sp: bool, ospf: bool, net: str) -> str:
    tmp = ['data', 'danw-data', 'acorn_benchmarks', 'outputs', 'sp' if sp else 'vf', 'ospf' if ospf else 'bgp',
           _get_date(), net, 'routes.csv']
    return _get_path(tmp)


def _get_date() -> str:
    return datetime.today().strftime('%Y-%m-%d')


def _get_path(tmp: List[str]) -> str:
    pth = '/' + os.path.sep.join(tmp)
    if not os.path.exists(pth):
        os.makedirs(os.path.dirname(pth))
    return pth


def compute_data_planes(sp: bool, ospf: bool):
    load_questions()

    networks_dir = get_networks_dir(sp, ospf)

    with open(get_output_log(sp, ospf), 'w', encoding='utf-8') as f:
        f.write('network name\tparse config time\tcompute dp time\ttotal time\n')

    nets = sorted(os.listdir(networks_dir))
    for net in nets:
        compute_dp(sp, ospf, net)


def compute_dp(sp: bool, ospf: bool, net: str):
    bf = Session(host="localhost")

    net_name = get_network_name(sp, ospf, net)
    bf.set_network(net_name)

    SNAPSHOT_DIR = get_networks_dir(sp, ospf) + '/' + net

    snapshot_name = get_snapshot_name()

    # parse configuration files
    t_start = time.time()
    bf.init_snapshot(SNAPSHOT_DIR, name=snapshot_name, overwrite=True)
    t_end = time.time()
    parse_config_time = t_end - t_start

    # compute data plane
    t_start = time.time()

    # bf.generate_dataplane()

    routes_df = bf.q.routes().answer().frame()
    routes_df.to_csv(get_output_routes(sp, ospf, net))

    t_end = time.time()
    compute_dp_time = t_end - t_start

    with open(get_output_log(sp, ospf), 'a', encoding='utf-8') as f:
        f.write('\t'.join(
            [net, str(parse_config_time), str(compute_dp_time), str(parse_config_time + compute_dp_time)]) + '\n')


if __name__ == "__main__":
    sp = not any([x == 'vf' for x in sys.argv])
    ospf = any([x == 'ospf' for x in sys.argv])
    compute_data_planes(sp, ospf)
