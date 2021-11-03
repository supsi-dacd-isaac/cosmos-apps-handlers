import pytz
import argparse
import os
import json
import toml
import datetime
import psutil
from datetime import datetime
import matplotlib.pyplot as plt
import networkx as nx

import subprocess
import hashlib

import constants as c

# Functions
DT_FRMT = '%Y-%m-%dT%H:%M:%SZ'


def send_cmd_over_ssh(host, user, command, print_flag):
    result = subprocess.check_output('ssh %s@%s %s' % (user, host, command), shell=True)
    decoded_ret = result.decode('UTF-8')
    if print_flag:
        print(decoded_ret)
    return decoded_ret.split('\n')


def scp_get(host, user, remote_file, local_folder):
    scp_cmd = 'scp %s@%s:%s %s%s%s' % (user, host, remote_file, local_folder, os.sep, remote_file.split(os.sep)[-1])
    print(scp_cmd)
    os.system(scp_cmd)

def scp_send(host, user, local_file, remote_file):
    scp_cmd = 'scp %s %s@%s:%s' % (local_file, user, host, remote_file)
    print(scp_cmd)
    os.system(scp_cmd)


def exec_real_cmd(host, user, real_cmd, print_flag):
    try:
        if print_flag:
            print('Remote command: %s' % real_cmd)
            print('Result:')
        res = send_cmd_over_ssh(host=host, user=user, command=real_cmd, print_flag=print_flag)
        if print_flag:
            print('****')
        return res
    except Exception as e:
        print('EXCEPTION: %s' % str(e))
        return None


# Get the first MAC address
def get_eth_mac(host, user, eth_interface):
    # I apologize for the following code, if you try something better please send a PR
    # Run the remote command
    if user == 'pi':
        ret = exec_real_cmd(host, user, 'sudo ifconfig %s' % eth_interface, False)
    else:
        ret = exec_real_cmd(host, user, 'ifconfig %s' % eth_interface, False)

    for idx in range(0, len(ret)):
        if 'Ethernet' in ret[idx]:
            res = ret[idx].replace('  ', ' ').replace(' ', ';').replace(';;', '').split(';')
            break
    return res[1]


def get_real_account(host, user, account):
    if 'hashed_mac' in account:
        tmp = account.split(';')
        if len(tmp) == 2:
            eth_mac = get_eth_mac(host, user, tmp[1])
        else:
            eth_mac = get_eth_mac(host, user, 'eth0')

        # Encode the MAC address
        h = hashlib.new('sha512')
        h.update(str.encode(eth_mac))
        real_account = h.hexdigest()
    else:
        real_account = account
    return real_account


def init_chain(node, host, user, remote_goroot, cfg, account, tokens_string, tokens_to_stake):
    chain_name = cfg['tendermint']['chainName']
    app = '%sd' % cfg['tendermint']['app']

    # Setup the main configuration
    exec_real_cmd(host, user, '%s/bin/%s init %s --chain-id %s' % (remote_goroot, app, node, chain_name), False)
    exec_real_cmd(host, user, '%s/bin/%s config chain-id %s' % (remote_goroot, app, chain_name), False)
    exec_real_cmd(host, user, '%s/bin/%s config keyring-backend test' % (remote_goroot, app), False)

    # Get the real account
    real_account = get_real_account(host, user, account)

    # Setup the part related to the node key and address
    exec_real_cmd(host, user, '%s/bin/%s keys add %s' % (remote_goroot, app, real_account), False)

    address = exec_real_cmd(host, user, '%s/bin/%s keys show %s -a' % (remote_goroot, app, real_account), True)

    exec_real_cmd(host, user, '%s/bin/%s add-genesis-account %s %s' % (remote_goroot, app, address[0], tokens_string), False)

    if node in cfg['validators']:
        exec_real_cmd(host, user, '%s/bin/%s gentx %s %s --chain-id %s' % (remote_goroot, app, real_account, tokens_to_stake, chain_name), False)
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
    host = cfg['nodes'][node][2]
    user = cfg['nodes'][node][3]
    remote_goroot = cfg['nodes'][node][4]
    account = cfg['nodes'][node][5]
    tokens_string = cfg['nodes'][node][6]
    tokens_to_stake = cfg['nodes'][node][7]

    # Get the node status
    print('**** NODE: %s@%s; COMMAND: \'%s\'' % (user, host, cmd))

    # Start the node
    if cmd == 'start':
        # ATTENTION: After a restart you have to wait the first empty block before performing transactions
        real_cmd = 'nohup %s/bin/%sd start --log_format json >> /home/%s/log/%s.log 2>&1 &' % (remote_goroot, cfg['tendermint']['app'], user, cfg['tendermint']['app'])
        print('Remote command: %s' % real_cmd)
        # This command does not work with ParallelSSHClient class
        subprocess.Popen(['ssh', '%s@%s' % (user, host), real_cmd], shell=False,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print('****')
    else:
        # Apply the setup on the sideschain
        if cmd == 'apply_setup':
            # Send the configuration TOML files
            local_file = '%s/to_sidechain/toml_config/%s.toml' % (cfg['dataFolder'], node)
            remote_file = '/home/%s/.%s/config/config.toml' % (user, cfg['tendermint']['app'])
            scp_send(host, user, local_file, remote_file)

            local_file = '%s/to_sidechain/toml_app/%s.toml' % (cfg['dataFolder'], node)
            remote_file = '/home/%s/.%s/config/app.toml' % (user, cfg['tendermint']['app'])
            scp_send(host, user, local_file, remote_file)

            # Send the genesis file
            local_file = '%s/to_sidechain/%s.json' % (cfg['dataFolder'], cfg['genesisFileGeneratorNode'])
            remote_file = '/home/%s/.%s/config/genesis.json' % (user, cfg['tendermint']['app'])
            scp_send(host, user, local_file, remote_file)

        # Get the node disk occupancy
        if cmd == 'check_disk_size':
            real_cmd = 'df -h | grep /dev'
            exec_real_cmd(host, user, real_cmd, True)

        # Get the sidechain disk occupancy
        if cmd == 'check_sidechain_size':
            real_cmd = 'du -sh /home/%s/.%s' % (user, cfg['tendermint']['app'])
            exec_real_cmd(host, user, real_cmd, True)

        # Delete the sidechain
        if cmd == 'delete':
            real_cmd = 'rm -rf /home/%s/.%s' % (user, cfg['tendermint']['app'])
            exec_real_cmd(host, user, real_cmd, False)

        # Get the genesis file
        if cmd == 'get_genesis_file':
            local_folder = '%s/from_sidechain/genesis_files' % cfg['dataFolder']
            scp_get(host, user, '/home/%s/.%s/config/genesis.json' % (user, cfg['tendermint']['app']), local_folder)

            print('Rename %s/genesis.json to %s/%s.json' % (local_folder, local_folder, node))
            os.rename('%s/genesis.json' % local_folder, '%s/%s.json' % (local_folder, node))

        if cmd == 'get_toml_reference_file':
            if node == cfg['tomlFilesReferenceNode']:
                scp_get(host, user, '/home/%s/.%s/config/app.toml' % (user, cfg['tendermint']['app']),
                        '%s/from_sidechain/toml_app' % cfg['dataFolder'])

                scp_get(host, user, '/home/%s/.%s/config/config.toml' % (user, cfg['tendermint']['app']),
                        '%s/from_sidechain/toml_config' % cfg['dataFolder'])

        # Get the node ID
        if cmd == 'get_node_id':
            real_cmd = '%s/bin/%sd tendermint show-node-id' % (remote_goroot, cfg['tendermint']['app'])
            exec_real_cmd(host, user, real_cmd, True)

        # Initialize the sidechain
        if cmd == 'init':
            init_chain(node, host, user, remote_goroot, cfg, account, tokens_string, tokens_to_stake)

        # Get the node log
        if cmd == 'log':
            real_cmd = 'tail -%s /home/%s/log/%s.log' % (param, user, cfg['tendermint']['app'])
            exec_real_cmd(host, user, real_cmd, True)


        # Get the node ID
        if cmd == 'save_node_id':
            real_cmd = '%s/bin/%sd tendermint show-node-id' % (remote_goroot, cfg['tendermint']['app'])
            node_id_info = exec_real_cmd(host, user, real_cmd, False)

            fw = open('%s/from_sidechain/nodes_ids.txt' % cfg['dataFolder'], 'a')
            fw.write('%s=%s@%s:%i\n' % (node, node_id_info[0], host, cfg['tendermint']['peerPort']))
            fw.close()

        # Show account info
        if cmd == 'show_account_info':
            real_cmd = '%s/bin/%sd keys show %s -a' % (remote_goroot, cfg['tendermint']['app'], get_real_account(host, user, account))
            account_address = exec_real_cmd(host, user, real_cmd, False)
            real_cmd = '%s/bin/%sd query account %s' % (remote_goroot, cfg['tendermint']['app'], account_address[0])
            exec_real_cmd(host, user, real_cmd, True)

        # Show key info
        if cmd == 'show_key_info':
            real_cmd = '%s/bin/%sd keys show %s' % (remote_goroot, cfg['tendermint']['app'], get_real_account(host, user, account))
            exec_real_cmd(host, user, real_cmd, True)

        # Get the node status
        if cmd == 'status':
            real_cmd = 'ps aux | grep -v grep | grep %s/bin/%s' % (remote_goroot, cfg['tendermint']['app'])
            exec_real_cmd(host, user, real_cmd, True)

        # Stop the node
        if cmd == 'stop':
            real_cmd = 'killall %sd' % cfg['tendermint']['app']
            exec_real_cmd(host, user, real_cmd, False)


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
        os.mkdir('%s/from_sidechain/toml_app' % data_folder)
        os.mkdir('%s/from_sidechain/toml_config' % data_folder)
        os.mkdir('%s/to_sidechain/' % data_folder)
        os.mkdir('%s/to_sidechain/toml_app' % data_folder)
        os.mkdir('%s/to_sidechain/toml_config' % data_folder)


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
                     font_weight='bold', font_size=24, font_color='#000000')
    nx.draw_networkx_nodes(G, nodes_pos, nodelist=nodes, node_color='#628CBD', node_size=600, alpha=1.0)
    nx.draw_networkx_nodes(G, validators_pos, nodelist=list(validators_pos.keys()), node_color='#FF8000', node_size=600, alpha=1.0)
    nx.draw_networkx_edges(G, nodes_pos, edgelist=edges_without_validators, width=4, alpha=1.0, edge_color='#228B22')
    nx.draw_networkx_edges(G, nodes_pos, edgelist=edges_with_validators, width=4, alpha=1.0, edge_color='#FF4000')
    plt.show()
    # plt.savefig('chain.pdf')


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

    # Get file from
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
        for validator in tmp_genesis_data['app_state']['genutil']['gen_txs']:
            validators_data.append(validator)

    # Append accounts and balances of nodes that will not generate the genesis file
    for node in genesis_data.keys():
        for account in genesis_data[node]['app_state']['auth']['accounts']:
            genesis_result['app_state']['auth']['accounts'].append(account)

        for balance in genesis_data[node]['app_state']['bank']['balances']:
            genesis_result['app_state']['bank']['balances'].append(balance)

    # Append the validators
    genesis_result['app_state']['genutil']['gen_txs'] = []
    for validator in validators_data:
        genesis_result['app_state']['genutil']['gen_txs'].append(validator)

    # Create the final genesis file
    final_genesis_file = '%s/to_sidechain/%s.json' % (cfg['dataFolder'], cfg['genesisFileGeneratorNode'])
    print('Create genesis file %s' % final_genesis_file)
    with open(final_genesis_file, 'w') as outfile:
        json.dump(genesis_result, outfile, indent=2)


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
        # Config file
        toml_config = toml.load('%s/from_sidechain/toml_config/config.toml' % cfg['dataFolder'])
        toml_config['moniker'] = k
        toml_config['p2p']['external_address'] = '%s:%i' % (cfg['nodes'][k][2], cfg['tendermint']['peerPort'])
        toml_config['p2p']['persistent_peers'] = get_perspeers_string(k, nodes_conns)
        file_path = '%s/to_sidechain/toml_config/%s.toml' % (cfg['dataFolder'], k)
        with open(file_path, 'w') as f:
            toml.dump(toml_config, f)

        # App file
        toml_app = toml.load('%s/from_sidechain/toml_app/app.toml' % cfg['dataFolder'])
        toml_app['api']['enable'] = True
        toml_app['api']['address'] = 'tcp://localhost:%i' % cfg['tendermint']['apiPort']
        file_path = '%s/to_sidechain/toml_app/%s.toml' % (cfg['dataFolder'], k)
        with open(file_path, 'w') as f:
            toml.dump(toml_app, f)



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


def add_meter(node, cfg, app_cli):
    host = cfg['nodes'][node][2]
    user = cfg['nodes'][node][3]
    remote_goroot = cfg['nodes'][node][4]
    account = cfg['nodes'][node][5]

    real_cmd = '%s/bin/%s keys show %s' % (remote_goroot, app_cli, get_real_account(host, user, account))
    key_str = exec_real_cmd(host, user, real_cmd, False)

    # Build the dataset
    res = ''
    for elem in key_str:
        res = '%s%s' % (res, elem)
    data_key = json.loads(res)

    # Do the transaction
    transaction_params = {
        "meter": data_key["name"],
        "account": data_key["address"]
    }
    return transaction_params


def     get_tokens_amount(ci, cfg, app_cli, logger):
    # pscli query account $(pscli keys show $NEW -a) | jq ".value.coins[0]"
    data = ci.get_account_info()
    remote_goroot = cfg['cosmos']['goPath']
    cmd = '%s/bin/%s query account %s' % (remote_goroot, app_cli, data['address'])

    # real_cmd = '%s/bin/%s keys show %s' % (remote_goroot, app_cli, u.get_real_account(host, user, account))
    raw_data = subprocess.check_output(cmd, shell=True)
    data = json.loads(raw_data.decode('utf-8'))
    logger.info('Tokens balance for of %s' % data['value']['address'])
    for token in data['value']['coins']:
        logger.info('BALANCE[%s] = %s' % (token['denom'], token['amount']))
    return data


# Main
if __name__ == "__main__":
    # Input args
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-c', help='comand')
    args = arg_parser.parse_args()

