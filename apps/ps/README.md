# Prepaid scenario handler:

Script `handler.py` is used to interact with a sidechain managed by [Pre-paid scenario application](https://github.com/supsi-dacd-isaac/cosmos-apps/blob/master/ps/README.md).

### Examples:

<pre>
(venv) # python handler.py -f conf/strato.json -c set_measure -s PImp 
(venv) # python handler.py -f conf/strato.json -c get_tokens_amount
(venv) # python handler.py -f conf/strato.json -c get_measure -s E_cons -t 2021-03-01T12:05:00Z
</pre>

