# Functions
HELP_ARGS = [
                '$F: Input configuration file',
                '$N: Node (all | label of the node reported in the configuration file)',
                '$C: Command (for details type $ python handle_sidechain -c help_commands)',
                '$P: Parameter eventually used by the command',
            ]

HEADER_EXAMPLE = '$ python handle_sidechain.py'
CONF_FILE_EXAMPLE = 'apps/ps/conf/sidechains/demo_ps_2pc_1valid.json'

HELP_CMDS = [
                {
                    'cmd': 'apply_setup',
                    'desc': 'Apply the setup',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c apply_setup'
                },
                {
                    'cmd': 'check_disk_size',
                    'desc': 'Check the disk usage',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c check_disk_size'
                },
                {
                    'cmd': 'check_sidechain_size',
                    'desc': 'Check the disk used by the sidechain',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c check_sidechain_size'
                },
                {
                    'cmd': 'clean_folders',
                    'desc': 'Clean the local folder',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c clean_folders'
                },
                {
                    'cmd': 'create_setup',
                    'desc': 'Create locally the setup (genesis + TOML files) for the remote nodes',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c create_setup'
                },
                {
                    'cmd': 'create_new_sidechain',
                    'desc': 'Create a new sidechain given the structure defined in the configuration file',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -c create_new_sidechain'
                },
                {
                    'cmd': 'delete',
                    'desc': 'Delete the sidechain',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c delete'
                },
                {
                    'cmd': 'draw',
                    'desc': 'Draw the sidechain defined in the configuration file',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c delete'
                },
                {
                    'cmd': 'get_genesis_file',
                    'desc': 'Download the remote genesis file',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c get_genesis_file'
                },
                {
                    'cmd': 'get_node_id',
                    'desc': 'Print the Tendermint identifier of the remote nodes',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c get_node_id'
                },
                {
                    'cmd': 'help',
                    'desc': 'Print the main help',
                    'example': HEADER_EXAMPLE + ' -c help'
                },
                {
                    'cmd': 'help_commands',
                    'desc': 'Print the commands help',
                    'example': HEADER_EXAMPLE + ' -c help_commands'
                },
                {
                    'cmd': 'init',
                    'desc': 'Initialize the sidechain',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c init'
                },
                {
                    'cmd': 'log',
                    'desc': 'Print the Cosmos log',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c log -p 5'
                },
                {
                    'cmd': 'log_rest_api',
                    'desc': 'Print the Cosmos REST API log',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c log_rest_api -p 5'
                },
                {
                    'cmd': 'save_node_id',
                    'desc': 'Save locally the Tendermint identifiers',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c save_node_id'
                },
                {
                    'cmd': 'show_account_info',
                    'desc': 'Save Cosmos account info',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c show_account_info'
                },
                {
                    'cmd': 'show_key_info',
                    'desc': 'Save Cosmos key info',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c show_key_info'
                },
                {
                    'cmd': 'status',
                    'desc': 'Print the status of the Cosmos application',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c status'
                },
                {
                    'cmd': 'status_rest_api',
                    'desc': 'Print the status of the Cosmos REST API',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c status_rest_api'
                },
                {
                    'cmd': 'start',
                    'desc': 'Start the Cosmos application',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c start'
                },
                {
                    'cmd': 'start_rest_api',
                    'desc': 'Start the Cosmos REST API',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c start_rest_api'
                },
                {
                    'cmd': 'stop',
                    'desc': 'Stop the Cosmos application',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c stop'
                },
                {
                    'cmd': 'stop_rest_api',
                    'desc': 'Stop the Cosmos REST API',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c stop_rest_api'
                },
                {
                    'cmd': 'upload_app',
                    'desc': 'Upload the Cosmos application',
                    'example': HEADER_EXAMPLE + ' -f ' + CONF_FILE_EXAMPLE + ' -n all -c upload_app'
                }
            ]