# BRIAR Command Line Interface (CLI) and Client

## Command Line Interface (CLI)

The command line interface provides a terminal based method of interacting with algorithms developed using the BRIAR API
and unifies the commands given to the services into a set of universal commands shared across all projects developed
using the API. It is the method of interfacing with any service built using the BRIAR framework as it shares the method
calls assigned to the service and provides callable methods which invoke service functions. The client and the
associated command line tools will be shared across all algorithms created with BRIAR and should not be modified,
ensuring the Evaluation Harness and other sets of tests can be run across algorithms created by different sets of
developers and generate comparable sets of results.

Like most command line toos, the command line interface can be scripted to act as part of a larger task. The client in
briar_client.py (which the command line interface is an interface for) can also be imported into a python project

## Usage

After running `setup.py`, the briar command line can be run by entering `python -m briar` anywhere. This will print a
help statement showing the different functions made available by the command line tool.

Before running any of these functions, however, you will need to first start the provided example service, so it can
reply to the commands. This is done by either directly calling the service python file `python service.py` or calling it
as a module `python -m briar.service`. This will start the service, and it will run until you forcefully exit it.

You can get the status and version of the example service with `python -m briar status` and you should see the results
printed by the client. Attempting to run any of the other functions with the example service in service.py will raise
a "NotImplementedError".

## More Details

The stubs and protobuf files which the client uses are detailed more thouroughly in the briar protobuf and stubs
documentation