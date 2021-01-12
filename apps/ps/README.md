# How to interact with the Cosmos REST API:

**References:** 

- Uses cases description: https://docs.google.com/document/d/17g-dTYTWL0qrM2610QHnE9Ofsf6v_NzMt54my7FxdMs/edit#heading=h.u5fcvqyjl0c5
- Energy community manager: https://github.com/supsi-dacd-isaac/cosmos-apps

**Important:** The following examples refer to `ps` (prepaid-scenario) application.  

**Nodes hashes used in the examples (dstreppa's PC and OLD PC):**

<pre>
NEW=ea4ff9fa3e8a06f824b947b573b63c30a288cf172fe553a03f1ff51839fa2b95a0ef9e47a4e8743c4442000e81b23e38d081e65193bfcaf975d8c4a7c0c3f844
OLD=c5694a93541db032e136404cf82ce6d6834da188d7c331078026ecab6d0d555e3fcd39a7eee23f4942c6e193ae236302a6f492e8de8663528043ded0c94eaba8 
</pre>

## Launch the sidechain with the REST interface:

<pre>
(venv) # python handle_sidechain.py -f conf/sidechains/demo_ps_2pc_1valid.json -n all -c start
(venv) # python handle_sidechain.py -f conf/sidechains/demo_ps_2pc_1valid.json -n all -c start_rest_api
</pre>

## How to sign a transaction:
Currently, Cosmos does not provide a safe procedure to sign the transaction via REST.
Consequently, after a POST request related to a transaction, the following commands must be run via console: 

<pre>
# curl -X POST -s http://localhost:1317/$REST > unsignedTx.json
# pscli tx sign unsignedTx.json --from $NEW --offline --chain-id encom_chain --sequence $SEQUENCE --account-number $ACCOUNT_NUMBER > signedTx.json
# pscli tx broadcast signedTx.json
</pre>

`$SEQUENCE` and `$ACCOUNT_NUMBER` are needed to safely sign the transactions and are obtained with the following query for $NEW.

<pre>
# curl -s http://localhost:1317/auth/accounts/$(pscli keys show $NEW -a)
</pre>

N.B. `$ACCOUNT_NUMBER` is always fixed, instead `$SEQUENCE` changes according to the occurred transactions.

## Administrative commands:

### *admin* register:

`admin` register cannot be modified/read via REST API.
It must be set via console after the sidechain initialization, as shown in following example.

<pre>
# pscli tx ps set-admin $NEW --from $NEW -y
</pre>

### *MeterAccount* list:

Only the `admin` node is allowed to run the transaction. This list contains the identifiers of the meters allowed 
to perform transactions about their energy consumption/production.

##### Transactions:
<pre>
# curl -X POST -s http://localhost:1317/ps/meterAccount --data-binary '{"base_req":{"from":"'$(pscli keys show $NEW -a)'","chain_id":"encom_chain"},"meter":"'$NEW'","account":"'$(pscli keys show $NEW -a)'"}' > unsignedTx.json
# pscli tx sign unsignedTx.json --from $NEW --offline --chain-id encom_chain --sequence $SEQUENCE --account-number $ACCOUNT_NUMBER > signedTx.json
# pscli tx broadcast signedTx.json
# curl -X POST -s http://localhost:1317/ps/meterAccount --data-binary '{"base_req":{"from":"'$(pscli keys show $NEW -a)'","chain_id":"encom_chain"},"meter":"'$OLD'","account":"'$ADDRESS_OLD'"}' > unsignedTx.json
# pscli tx sign unsignedTx.json --from $NEW --offline --chain-id encom_chain --sequence $SEQUENCE --account-number $ACCOUNT_NUMBER > signedTx.json
# pscli tx broadcast signedTx.json
</pre>

N.B. `$ADDRESS_OLD` is obtained typing the comand `pscli keys show $OLD -a` on the `OLD` node.

##### Query:
<pre>
# curl -s http://localhost:1317/ps/meterAccount
</pre>

### *parameters* dataset:

Only the `admin` node is allowed to run the transaction.

##### Transaction:

<pre>
# curl -X POST -s http://localhost:1317/ps/parameters --data-binary '{"base_req":{"from":"'$(pscli keys show $NEW -a)'","chain_id":"encom_chain"},"prodConvFactor":"1","consConvFactor":"2","maxConsumption":"100","penalty":"13"}' > unsignedTx.json
# pscli tx sign unsignedTx.json --from $NEW --offline --chain-id encom_chain --sequence $SEQUENCE --account-number $ACCOUNT_NUMBER > signedTx.json
# pscli tx broadcast signedTx.json
</pre>

##### Query:
<pre>
# curl -s http://localhost:1317/ps/parameters
</pre>

## Operating commands:

### Storage of generic data in the sidechain:

Each measure is identified by the following three elements:

* `signal` 
* `timestamp`
* `meter identifier`  

##### Transaction:

<pre>
# curl X POST -s http://localhost:1317/ps/setMeasure --data-binary '{"base_req":{"from":"'$(pscli keys show $NEW -a)'","chain_id":"encom_chain"},"signal":"V","timestamp":"1000","value":"231.4"}' > unsignedTx.json
# pscli tx sign unsignedTx.json --from $NEW --offline --chain-id encom_chain --sequence $SEQUENCE --account-number $ACCOUNT_NUMBER > signedTx.json
# pscli tx broadcast signedTx.json
</pre>

##### Query:
<pre>
# curl -s "http://localhost:1317/ps/getMeasure?signal=V&timestamp=1000"
</pre>



#### Still to implement in the REST API:

* _Minting_, performed by the admin
* _Auto-burning_, performed by nodes in the `MeterAccount` list, related to node energy consumption
* _Auto-minting_, performed by nodes in the `MeterAccount` list, related to node energy production