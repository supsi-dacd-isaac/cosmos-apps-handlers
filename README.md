# cosmos-apps-handlers 
_cosmos-apps-handlers_ is a collection of Python scripts that can be used to handle the Cosmos sidechains
implemented in https://github.com/supsi-dacd-isaac/cosmos-apps.
Basically, to each application developed on [Cosmos-apps](https://github.com/supsi-dacd-isaac/cosmos-apps) 
 correspond on this repository a handler. Besides, a specific script has been developed for the sidechains administration.
It is highly recommended to create a Python virtual environment.


## Sidechain administration:
The script `handle_sidechain.py` is used for the generic management of a sidechains. 
For its usage, please refer to the help commands below.  

<pre>
(venv)# python handle_sidechain.py -c help
(venv)# python handle_sidechain.py -c help_commands
</pre>


## Available applications:

* [Prepaid-scenario handler](https://github.com/supsi-dacd-isaac/cosmos-apps-handlers/tree/main/apps/ps#readme)



## Acknowledgements
The authors would like to thank the Swiss Federal Office of Energy (SFOE) and the Swiss Competence Center for Energy Research - Future Swiss Electrical Infrastructure (SCCER-FURIES), for their financial and technical support to this research work.