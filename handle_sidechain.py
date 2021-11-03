import argparse
import json
import time

import utilities as u

# Main
if __name__ == "__main__":

    # Input args
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-f', help='file')
    arg_parser.add_argument('-c', help='command')
    arg_parser.add_argument('-n', help='node')
    arg_parser.add_argument('-p', help='parameters')
    args = arg_parser.parse_args()

    # Define the main variables
    cmd = args.c
    node = args.n
    param = args.p

    if u.check_cmd_availability(cmd) is True:
        # Print the main help
        if cmd == 'help' or cmd is None:
            u.help_args()

        # Print the commands help
        elif cmd == 'help_commands':
            u.help_commands()

        else:
            # Get the configuration settings
            cfg = json.loads(open(args.f).read())

            # Check if the data folder is properly instantiated
            u.check_data_folder(cfg['dataFolder'])

            # Draw the sidechain structure
            if cmd == 'draw':
                u.draw_sidechain(cfg)

            # Create a new sidechain
            elif cmd == 'create_new_sidechain':
                u.run_cmd('all', 'stop', cfg, param)

                u.run_cmd('all', 'delete', cfg, param)
                u.run_cmd('all', 'init', cfg, param)

                u.run_cmd('all', 'save_node_id', cfg, param)
                u.run_cmd('all', 'get_genesis_file', cfg, param)
                u.run_cmd('all', 'get_toml_reference_file', cfg, param)
                u.create_setup(cfg)
                u.run_cmd('all', 'apply_setup', cfg, param)

                u.run_cmd('all', 'start', cfg, param)
                time.sleep(2)
                u.run_cmd('all', 'status', cfg, param)

            elif cmd == 'clean_folders':
                u.clean_folder(cfg['dataFolder'])

            else:
                u.run_cmd(node, cmd, cfg, param)
    else:
        print('ATTENTION! Comand %s is not available' % cmd)
        print('For details about the available commands type $ python handle_sidechain -c help_commands')