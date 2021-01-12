import requests
import os
import json

class CosmosInterface:
    """
    CosmosInterface class
    """
    def __init__(self, app, cfg, logger):
        """
        Constructor
        :param cfg: configuration dictionary
        :type dict
        :param logger
        :type Logger
        """
        # define the main global variables
        self.app = app
        self.cfg = cfg
        self.logger = logger
        self.full_path_app = '%s/bin/%scli' % (self.cfg['cosmos']['goPath'], self.app)
        self.base_url = '%s://%s:%i' % (self.cfg['cosmos']['protocol'], self.cfg['cosmos']['host'],
                                        self.cfg['cosmos']['port'])
        self.account = self.get_account_info()
        self.account_number, self.sequence_number = self.get_account_sequence_numbers()

    def get_account_info(self):
        res = os.popen('%s keys list' % self.full_path_app).read()
        accounts = json.loads(res)
        return accounts[0]

    def get_account_sequence_numbers(self):
        url = '%s/auth/accounts/%s' % (self.base_url, self.account['address'])
        r = requests.get(url)
        data = json.loads(r.text)

        return int(data['result']['value']['account_number']), int(data['result']['value']['sequence'])

    def do_query(self, cmd, params):
        url = '%s/%s/%s?' % (self.base_url, self.app, cmd)
        for k in params.keys():
            url = '%s%s=%s&' % (url, k, params[k])
        self.logger.info('GET -> %s' % url)
        r = requests.get(url)
        return json.loads(r.text)

    def do_transaction(self, cmd, params):
        # Create a transaction without signature
        self.do_unsigned_transaction(cmd, params, 'unsignedTx.json')

        # If power then send two messages in the same transaction(the former for the power data, the latter for the energy)
        if params['signal'] == 'PImp':
            self.add_msg_to_transactions(cmd, params, 'E_cons', 'unsignedTx.json')
        elif params['signal'] == 'PExp':
            self.add_msg_to_transactions(cmd, params, 'E_prod', 'unsignedTx.json')

        # Sign the transaction
        self.do_transaction_signature('unsignedTx.json')

        # Broadcast the transaction
        self.broadcast_transaction()

        # Delete tmp files
        self.delete_transactions_temporary_files()

    def add_msg_to_transactions(self, cmd, params, new_signal, output_file):
        energy_output_file = 'unsignedTxE.json'
        params['signal'] = new_signal
        # 15 minutes time-resolution => E = P/4
        params['value'] = '%i' % int(float(params['value'])/4)

        # Save data related to energy
        self.do_unsigned_transaction(cmd, params, energy_output_file)

        with open('%s/%s' % (self.cfg["cosmos"]["folderSignatureFiles"], output_file)) as json_file:
            data = json.load(json_file)

        with open('%s/%s' % (self.cfg["cosmos"]["folderSignatureFiles"], energy_output_file)) as json_file:
            data_energy = json.load(json_file)

        # Append the energy data to the message array
        data['value']['msg'].append(data_energy['value']['msg'][0])

        self.logger.info('Add the consumed/produced energy data to the unsigned transaction')
        with open('%s/%s' % (self.cfg["cosmos"]["folderSignatureFiles"], output_file), 'w') as fw:
            json.dump(data, fw)

    def do_unsigned_transaction(self, cmd, payload, output_file):
        endpoint = '%s/%s/%s' % (self.base_url, self.app, cmd)
        payload['base_req'] = {"from": self.account['address'], "chain_id": self.cfg['cosmos']['chainName']}
        headers = {"content-type": "application/json; charset=UTF-8"}

        # Perform the POST request
        self.logger.info('POST -> %s {%s}' % (endpoint, payload))
        r = requests.post(endpoint, headers=headers, json=payload)

        # Update the sequence number
        _, self.sequence_number = self.get_account_sequence_numbers()

        transaction_dict = json.loads(r.text)

        self.logger.info('Create the unsigned transaction')
        with open('%s/%s' % (self.cfg["cosmos"]["folderSignatureFiles"], output_file), 'w') as fw:
            json.dump(transaction_dict, fw)

    def do_transaction_signature(self, unsigned_file):
        # Sign the transaction
        self.logger.info('Create the signed transaction')
        cmd_signature = '%s tx sign %s/%s --from %s --offline --chain-id %s ' \
                        '--sequence %i --account-number %i' % (self.full_path_app,
                                                               self.cfg['cosmos']['folderSignatureFiles'],
                                                               unsigned_file,
                                                               self.account['name'],
                                                               self.cfg['cosmos']['chainName'],
                                                               self.sequence_number,
                                                               self.account_number)
        res = os.popen(cmd_signature).read()

        res_dict = json.loads(res)
        with open('%s/signedTx.json' % self.cfg["cosmos"]["folderSignatureFiles"], 'w') as fw:
            json.dump(res_dict, fw)

    def broadcast_transaction(self):
        self.logger.info('Send the transaction as broadcast on the sidechain')
        cmd_broadcast = '%s tx broadcast %s/signedTx.json' % (self.full_path_app,
                                                              self.cfg["cosmos"]["folderSignatureFiles"])
        os.popen(cmd_broadcast).read()

    def delete_transactions_temporary_files(self):
        if os.path.exists('%s/unsignedTxE.json' % self.cfg["cosmos"]["folderSignatureFiles"]):
            os.unlink('%s/unsignedTxE.json' % self.cfg["cosmos"]["folderSignatureFiles"])
        os.unlink('%s/unsignedTx.json' % self.cfg["cosmos"]["folderSignatureFiles"])
        os.unlink('%s/signedTx.json' % self.cfg["cosmos"]["folderSignatureFiles"])
