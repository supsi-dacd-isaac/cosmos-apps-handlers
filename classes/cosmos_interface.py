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
        r = requests.get(url)
        return json.loads(r.text)

    def do_transaction(self, cmd, params):
        # Create a transaction without signature
        self.do_unsigned_transaction(cmd, params)

        # Sign the transaction
        self.do_transaction_signature()

        # Broadcast the transaction
        self.broadcast_transaction()

        # Delete tmp files
        self.delete_transactions_temporary_files()

    def do_unsigned_transaction(self, cmd, payload):
        endpoint = '%s/%s/%s' % (self.base_url, self.app, cmd)
        payload['base_req'] = {"from": self.account['address'], "chain_id": self.cfg['cosmos']['chainName']}
        headers = {"content-type": "application/json; charset=UTF-8"}

        # Perform the POST request
        r = requests.post(endpoint, headers=headers, json=payload)

        # Update the sequence number
        _, self.sequence_number = self.get_account_sequence_numbers()

        transaction_dict = json.loads(r.text)

        self.logger.info('Create the unsigned transaction')
        with open('%s/unsignedTx.json' % self.cfg["cosmos"]["folderSignatureFiles"], 'w') as fw:
            json.dump(transaction_dict, fw)

    def do_transaction_signature(self):
        # Sign the transaction
        self.logger.info('Create the signed transaction')
        cmd_signature = '%s tx sign %s/unsignedTx.json --from %s --offline --chain-id %s ' \
                        '--sequence %i --account-number %i' % (self.full_path_app,
                                                               self.cfg['cosmos']['folderSignatureFiles'],
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
        os.unlink('%s/unsignedTx.json' % self.cfg["cosmos"]["folderSignatureFiles"])
        os.unlink('%s/signedTx.json' % self.cfg["cosmos"]["folderSignatureFiles"])
