import pytz
import argparse
import os
import json
import datetime
import psutil
from datetime import datetime
import matplotlib.pyplot as plt
import networkx as nx

import subprocess
import hashlib
from pssh.clients import ParallelSSHClient

import constants as c

# Functions
DT_FRMT = '%Y-%m-%dT%H:%M:%SZ'

def send_cmd_over_ssh(host, user, command, print_flag):
    client = ParallelSSHClient(hosts=[host], user=user)
    try:
        output = client.run_command(command=command, return_list=True)
        result = []
        for host_output in output:
            for line in host_output.stdout:
                if print_flag:
                    print(line)
                result.append(line)
        return result
    except Exception as e:
        print('EXCEPTION: %s' % str(e))
        return None

def scp_get(node, host, user, remote_file, local_folder):
    scp_cmd = 'scp %s@%s:%s %s' % (user, host, remote_file, local_folder)
    print(scp_cmd)
    os.system(scp_cmd)

    print('Rename %s/genesis.json to %s/%s.json' % (local_folder, local_folder, node))
    os.rename('%s/genesis.json' % local_folder, '%s/%s.json' % (local_folder, node))

def scp_send(host, user, local_file, remote_file):
    scp_cmd = 'scp %s %s@%s:%s' % (local_file, user, host, remote_file)
    print(scp_cmd)
    os.system(scp_cmd)

def exec_real_cmd(host, user, real_cmd, print_flag):
    print('Remote command: %s' % real_cmd)
    if print_flag:
        print('Result:')
    res = send_cmd_over_ssh(host=host, user=user, command=real_cmd, print_flag=print_flag)
    print('****')
    return res


# Get the first MAC address
def get_eth_mac(host, user):
    # I apologize for the following code, if you try something better please send a PR

    # Run the remote command
    if user == 'pi':
        ret = exec_real_cmd(host, user, 'sudo ifconfig', False)
    else:
        ret = exec_real_cmd(host, user, 'ifconfig', False)

    # The classical way (ETH0)
    idx_eth0 = -1
    for idx in range(0, len(ret)):
        if 'eth0' in ret[idx]:
            idx_eth0 = idx

    if idx_eth0 != -1:
        for idx in range(idx_eth0, len(ret)):
            if 'ether' in ret[idx]:
                break
    else:
        # it works on Ubuntu>=18.04
        idx_dev_int = -1
        for idx in range(0, len(ret)):
            if 'device' in ret[idx] and 'interrupt' in ret[idx]:
                idx_dev_int = idx

        for idx in range(idx_dev_int, 0, -1):
            if 'ether' in ret[idx]:
                break

    res = ret[idx].replace('  ', ' ').replace(' ', ';').replace(';;', '').split(';')
    return res[1]

def get_real_account(host, user, account):
    if account == 'hashed_mac':
        # Get the remote first MAC address
        eth_mac = get_eth_mac(host, user)

        # Encode the MAC address
        h = hashlib.new('sha512')
        h.update(str.encode(eth_mac))
        real_account = h.hexdigest()
    else:
        real_account = account
    return real_account

def init_chain(node, host, user, app, remote_goroot, cfg, account, tokens_string):
    app_cli = '%scli' % app[:-1]
    chain_name = cfg['tendermint']['chainName']

    # Setup the main configuration
    exec_real_cmd(host, user, '%s/bin/%s init %s --chain-id=%s' % (remote_goroot, app, node, chain_name), False)
    exec_real_cmd(host, user, '%s/bin/%s config output json' % (remote_goroot, app_cli), False)
    exec_real_cmd(host, user, '%s/bin/%s config indent true' % (remote_goroot, app_cli), False)
    exec_real_cmd(host, user, '%s/bin/%s config trust-node true' % (remote_goroot, app_cli), False)
    exec_real_cmd(host, user, '%s/bin/%s config chain-id %s' % (remote_goroot, app_cli, chain_name), False)
    exec_real_cmd(host, user, '%s/bin/%s config keyring-backend test' % (remote_goroot, app_cli), False)

    # Get the real account
    real_account = get_real_account(host, user, account)

    # Setup the part related to the node key and address
    exec_real_cmd(host, user, '%s/bin/%s keys delete %s' % (remote_goroot, app_cli, real_account), False)
    exec_real_cmd(host, user, '%s/bin/%s keys add %s' % (remote_goroot, app_cli, real_account), False)

    address = exec_real_cmd(host, user, '%s/bin/%s keys show %s -a' % (remote_goroot, app_cli, real_account), True)

    exec_real_cmd(host, user, '%s/bin/%s add-genesis-account %s %s' % (remote_goroot, app, address[0], tokens_string), False)

    if node in cfg['validators']:
        exec_real_cmd(host, user, '%s/bin/%s gentx --name %s --keyring-backend test' % (remote_goroot, app, real_account), False)
        exec_real_cmd(host, user, '%s/bin/%s collect-gentxs' % (remote_goroot, app), False)

    exec_real_cmd(host, user, '%s/bin/%s validate-genesis' % (remote_goroot, app), False)

def help_args():
    print('\n*** Input arguments\n')
    print('\t $ python handle_sidechain.py -f $F -n $N -c $C -p $P')
    print('')
    for help_arg in c.HELP_ARGS:
        print(' * %s' % help_arg)
        print()

def help_commands():
    print('*** Available commands\n')
    for help_cmd in c.HELP_CMDS:
        print(' * %s: %s' % (help_cmd['cmd'], help_cmd['desc']))
        print('\tExample: %s' % help_cmd['example'])
        print()

def exec_cmd(cfg, node, cmd, param):
    # Define main variables
    app = '%sd' % cfg['tendermint']['app']
    app_cli = '%scli' % cfg['tendermint']['app']
    host = cfg['nodes'][node][2]
    user = cfg['nodes'][node][3]
    remote_goroot = cfg['nodes'][node][4]
    account = cfg['nodes'][node][5]
    tokens_string = cfg['nodes'][node][6]

    # Get the node status
    print('**** NODE: %s@%s; COMMAND: \'%s\'' % (user, host, cmd))

    # Start the node
    if cmd == 'start':
        # ATTENTION: After a restart you have to wait the first empty block before performing transactions
        real_cmd = 'nohup %s/bin/%s start >> /home/%s/log/%s.log &' % (remote_goroot, app, user, app)
        print('Remote command: %s' % real_cmd)
        # This command does not work with ParallelSSHClient class
        subprocess.Popen(['ssh', '%s@%s' % (user, host), real_cmd], shell=False,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print('****')
    # Start the node REST API
    elif cmd == 'start_rest_api':
        real_cmd = 'nohup %s/bin/%s rest-server --chain-id %s --trust-node >> /home/%s/log/%s_rest.log &' % (remote_goroot,
                                                                                                             app_cli,
                                                                                                             cfg['tendermint']['chainName'],
                                                                                                             user,
                                                                                                             app_cli)
        print('Remote command: %s' % real_cmd)
        # This command does not work with ParallelSSHClient class
        subprocess.Popen(['ssh', '%s@%s' % (user, host), real_cmd], shell=False,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print('****')
    else:
        # Apply the setup on the sideschain
        if cmd == 'apply_setup':
            # Send the configuration TOML file
            local_file = '%s/to_sidechain/toml/%s.toml' % (cfg['dataFolder'], node)
            remote_file = '/home/%s/.%s/config/config.toml' % (user, app)
            scp_send(host, user, local_file, remote_file)

            # Send the genesis file
            local_file = '%s/to_sidechain/%s.json' % (cfg['dataFolder'], cfg['genesisFileGeneratorNode'])
            remote_file = '/home/%s/.%s/config/genesis.json' % (user, app)
            scp_send(host, user, local_file, remote_file)

        # Get the node disk occupancy
        if cmd == 'check_disk_size':
            real_cmd = 'df -h | grep /dev'
            exec_real_cmd(host, user, real_cmd, True)

        # Get the sidechain disk occupancy
        if cmd == 'check_sidechain_size':
            real_cmd = 'du -sh /home/%s/.%s' % (user, app)
            exec_real_cmd(host, user, real_cmd, True)

        # Delete the sidechain
        if cmd == 'delete':
            real_cmd = 'rm -rf /home/%s/.%s' % (user, app)
            exec_real_cmd(host, user, real_cmd, False)

        # Get the genesis file
        if cmd == 'get_genesis_file':
            scp_get(node, host, user, '/home/%s/.%s/config/genesis.json' % (user, app),
                    '%s/from_sidechain/genesis_files' % cfg['dataFolder'])

        # Get the node ID
        if cmd == 'get_node_id':
            real_cmd = '%s/bin/%s tendermint show-node-id' % (remote_goroot, app)
            exec_real_cmd(host, user, real_cmd, True)

        # Initialize the sidechain
        if cmd == 'init':
            init_chain(node, host, user, app, remote_goroot, cfg, account, tokens_string)

        # Get the node log
        if cmd == 'log':
            real_cmd = 'tail -%s /home/%s/log/%s.log' % (param, user, app)
            exec_real_cmd(host, user, real_cmd, True)

        # Get the node REST API log
        if cmd == 'log_rest_api':
            real_cmd = 'tail -%s /home/%s/log/%s_rest.log' % (param, user, app_cli)
            exec_real_cmd(host, user, real_cmd, True)

        # Get the node ID
        if cmd == 'save_node_id':
            real_cmd = '%s/bin/%s tendermint show-node-id' % (remote_goroot, app)
            node_id_info = exec_real_cmd(host, user, real_cmd, False)

            fw = open('%s/from_sidechain/nodes_ids.txt' % cfg['dataFolder'], 'a')
            fw.write('%s=%s@%s:%i\n' % (node, node_id_info[0], host, cfg['tendermint']['peerPort']))
            fw.close()

        # Show account info
        if cmd == 'show_account_info':
            real_cmd = '%s/bin/%s keys show %s -a' % (remote_goroot, app_cli, get_real_account(host, user, account))
            account_address = exec_real_cmd(host, user, real_cmd, False)
            real_cmd = '%s/bin/%s query account %s' % (remote_goroot, app_cli, account_address[0])
            exec_real_cmd(host, user, real_cmd, True)

        # Show key info
        if cmd == 'show_key_info':
            real_cmd = '%s/bin/%s keys show %s' % (remote_goroot, app_cli, get_real_account(host, user, account))
            exec_real_cmd(host, user, real_cmd, True)

        # Get the node status
        if cmd == 'status':
            real_cmd = 'ps aux | grep -v grep | grep %s/bin/%s' % (remote_goroot, app)
            exec_real_cmd(host, user, real_cmd, True)

        # Get the node REST API status
        if cmd == 'status_rest_api':
            real_cmd = 'ps aux | grep -v grep | grep %s/bin/%s' % (remote_goroot, app_cli)
            exec_real_cmd(host, user, real_cmd, True)

        # Stop the node
        if cmd == 'stop':
            real_cmd = 'killall %s' % app
            exec_real_cmd(host, user, real_cmd, False)

        # Stop the node REST API
        if cmd == 'stop_rest_api':
            real_cmd = 'killall %s' % app_cli
            exec_real_cmd(host, user, real_cmd, False)

        if cmd == 'upload_app':
            # Send the appd executable
            local_file = '%s/bin/%s' % (os.environ['GOPATH'], '%sd' % cfg['tendermint']['app'])
            remote_file = '%s/bin/%s' % (remote_goroot, '%sd' % cfg['tendermint']['app'])
            scp_send(host, user, local_file, remote_file)

            # Send the appcli executable
            local_file = '%s/bin/%s' % (os.environ['GOPATH'], '%scli' % cfg['tendermint']['app'])
            remote_file = '%s/bin/%s' % (remote_goroot, '%scli' % cfg['tendermint']['app'])
            scp_send(host, user, local_file, remote_file)

            # Set the remote permission
            exec_real_cmd(host, user, 'chmod 744 %s/bin/%s' % (remote_goroot, '%sd' % cfg['tendermint']['app']), False)
            exec_real_cmd(host, user, 'chmod 744 %s/bin/%s' % (remote_goroot, '%scli' % cfg['tendermint']['app']), False)

def clear(cfg):
    if os.path.isfile('%s/from_sidechain/nodes_ids.txt' % cfg['dataFolder']):
        os.unlink('%s/from_sidechain/nodes_ids.txt' % cfg['dataFolder'])

def check_cmd_availability(cmd):
    for available_cmd in c.HELP_CMDS:
        if available_cmd['cmd'] == cmd:
            return True
    return False

def run_cmd(node, cmd, cfg, param):
    # Clear folder and files, which can eventually be used
    if cmd == 'save_node_id':
        clear(cfg)

    if node == 'all':
        # Custom case of setup creation
        if cmd == 'create_setup':
            # Get the node status
            print('**** COMMAND: \'%s\'' % cmd)
            create_setup(cfg)
        else:
            # cycle over the nodes
            for single_node in cfg['nodes'].keys():
                # exec the command
                exec_cmd(cfg, single_node, cmd, param)
    else:
        # exec the command
        exec_cmd(cfg, node, cmd, param)

def check_data_folder(data_folder):
    if os.path.isdir(data_folder) is False:
        os.mkdir(data_folder)
        os.mkdir('%s/from_sidechain' % data_folder)
        os.mkdir('%s/from_sidechain/genesis_files' % data_folder)
        os.mkdir('%s/to_sidechain/' % data_folder)
        os.mkdir('%s/to_sidechain/toml' % data_folder)

def clean_folder(folder):
    print('Clean data folder %s' % folder)

    # Cycle recursively in the given folder
    for root, dirs, files in os.walk(folder):
        for file in files:
            print('Delete %s/%s' % (root, file))
            os.unlink(os.path.join(root, file))

def draw_sidechain(cfg):
    nodes_info = cfg['nodes']
    edges = cfg['edges']
    nodes = nodes_info.keys()

    validators_pos = dict()
    for validator in cfg['validators']:
        validators_pos[validator] = [nodes_info[validator][0], nodes_info[validator][1]]

    edges_with_validators = []
    edges_without_validators = []
    for edge in edges:
        if edge[0] in cfg['validators'] and edge[1] in cfg['validators']:
            edges_with_validators.append(edge)
        else:
            edges_without_validators.append(edge)

    # Get the positions from the nodes info
    nodes_pos = dict()
    for node in nodes_info:
        nodes_pos[node] = [nodes_info[node][0], nodes_info[node][1]]

    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    nx.draw_networkx(G, with_labels=True, pos=nodes_pos, node_color='#FFFFFF', edge_color='#FFFFFF',
                     font_weight='normal', font_size=16, font_color='#000000')
    nx.draw_networkx_nodes(G, nodes_pos, nodelist=nodes, node_color='#628CBD', node_size=300, alpha=0.8)
    nx.draw_networkx_nodes(G, validators_pos, nodelist=list(validators_pos.keys()), node_color='#FF8000', node_size=300, alpha=0.8)
    nx.draw_networkx_edges(G, nodes_pos, edgelist=edges_without_validators, width=2, alpha=0.8, edge_color='#228B22')
    nx.draw_networkx_edges(G, nodes_pos, edgelist=edges_with_validators, width=2, alpha=0.8, edge_color='#FF4000')
    plt.show()


def get_dt(str_dt, tz_local, flag_set_minute=True):
    if str_dt == 'now':
        dt = datetime.datetime.now()
    elif str_dt == 'now_s00':
        dt = datetime.datetime.now()
        dt = dt.replace(second=0, microsecond=0)
    else:
        dt = datetime.datetime.strptime(str_dt, DT_FRMT)
    dt = tz_local.localize(dt)
    dt_utc = dt.astimezone(pytz.utc)

    if flag_set_minute is True:
        # Set the correct minute (0,15,30,45)
        return set_start_minute(dt_utc)
    else:
        return dt_utc

def set_start_minute(dt_utc):
    if 0 <= dt_utc.minute < 15:
        return dt_utc.replace(minute=0, second=0, microsecond=0)
    elif 15 <= dt_utc.minute < 30:
        return dt_utc.replace(minute=15, second=0, microsecond=0)
    elif 30 <= dt_utc.minute < 45:
        return dt_utc.replace(minute=30, second=0, microsecond=0)
    else:
        return dt_utc.replace(minute=45, second=0, microsecond=0)

def set_end_minute(dt_utc):
    if 0 <= dt_utc.minute < 15:
        return dt_utc.replace(minute=14, second=59, microsecond=0)
    elif 15 <= dt_utc.minute < 30:
        return dt_utc.replace(minute=29, second=59, microsecond=0)
    elif 30 <= dt_utc.minute < 45:
        return dt_utc.replace(minute=44, second=59, microsecond=0)
    else:
        return dt_utc.replace(minute=59, second=59, microsecond=0)

def get_macs(family):
    macs = dict()
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == family:
                macs[interface] = snic.address
    return macs

def check_configuration(cfg):
    ids = get_nodes_ids_from_file(cfg)
    print(ids)
    nodes_conns = dict()
    res = True
    for node in cfg['nodes'].keys():
        for edge in cfg['edges']:
            if node == edge[0]:

                if node not in nodes_conns.keys():
                    nodes_conns[node] = [ids[edge[1]]]
                else:
                    if ids[edge[1]] in nodes_conns[node]:
                        print('ERROR: Edge %s -> %s already saved in the conf file' % (node, ids[edge[1]]))
                        res = False
                    nodes_conns[node].append(ids[edge[1]])

    if res is True:
        print('RESULT: Configuration OK')
    else:
        print('RESULT: Found errors in conf file %s' % args.c)

def create_setup(cfg):

    ids = get_nodes_ids_from_file(cfg)
    nodes_conns = dict()
    for node in cfg['nodes'].keys():
        for edge in cfg['edges']:
            if node == edge[0]:

                if node not in nodes_conns.keys():
                    nodes_conns[node] = [ids[edge[1]]]
                else:
                    try:
                        nodes_conns[node].append(ids[edge[1]])
                    except Exception as e:
                        print('ERROR! Probably wrong configuration')

    create_toml_files(nodes_conns, cfg)

    genesis_data = dict()
    validators_data = []
    genesis_folder = '%s/from_sidechain/genesis_files' % cfg['dataFolder']
    for node in cfg['nodes'].keys():
        tmp_genesis_data = json.loads(open(os.path.expanduser('%s/%s.json' % (genesis_folder, node))).read())
        if node != cfg['genesisFileGeneratorNode']:
            genesis_data[node] = tmp_genesis_data
        else:
            genesis_result = tmp_genesis_data

        # Get the configured validators
        for validator in tmp_genesis_data['app_state']['genutil']['gentxs']:
            validators_data.append(validator)

    # Append accounts of nodes that will not generate the genesis file
    for node in genesis_data.keys():
        for account in genesis_data[node]['app_state']['auth']['accounts']:
            genesis_result['app_state']['auth']['accounts'].append(account)

    # Append the validators
    genesis_result['app_state']['genutil']['gentxs'] = []
    for validator in validators_data:
        genesis_result['app_state']['genutil']['gentxs'].append(validator)

    # Create the final genesis file
    final_genesis_file = '%s/to_sidechain/%s.json' % (cfg['dataFolder'], cfg['genesisFileGeneratorNode'])
    print('Create genesis file %s' % final_genesis_file)
    with open(final_genesis_file, 'w') as outfile:
        json.dump(genesis_result, outfile, indent=4)

def get_perspeers_string(node, nodes_conns):
    str_peers = ''
    if node in nodes_conns.keys():
        for peer in nodes_conns[node]:
            str_peers = '%s%s,' % (str_peers, peer)
        return str_peers[:-1]
    else:
        return str_peers

def create_toml_files(nodes_conns, cfg):
    for k in cfg['nodes'].keys():
        out_toml_file = '%s/to_sidechain/toml/%s.toml' % (cfg['dataFolder'], k)
        str_peers = get_perspeers_string(k, nodes_conns)
        fr = open(os.path.expanduser(cfg['referenceTOMLFile']), 'r')
        fw = open(os.path.expanduser(out_toml_file), 'w')
        print('Create TOML file %s' % out_toml_file)
        for line in fr:
            if 'persistent_peers =' in line:
                fw.write('persistent_peers = "%s"\n' % str_peers)
            elif 'moniker =' in line:
                fw.write('moniker = "%s"\n' % k)
            else:
                fw.write(line)
        fw.close()
        fr.close()

def get_nodes_ids_from_file(cfg):
    f = open(os.path.expanduser('%s/from_sidechain/nodes_ids.txt' % cfg['dataFolder']), 'r')
    ids = dict()
    for id_line in f:
        (node, data) = id_line.split('=')
        ids[node] = data[:-1]
    return ids

def create_nodes_file(cfg):
    of = '/tmp/nodes.txt'
    fw = open(of, 'w')
    for node in cfg['nodes'].keys():
        fw.write('%s%s\n' % (cfg['nodes'][node][2], node))
    fw.close()
    print('File %s created' % of)


# Main
if __name__ == "__main__":
    # Input args
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-c', help='comand')
    args = arg_parser.parse_args()

