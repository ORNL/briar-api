import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import optparse
import re
from briar.cli.connection import addConnectionOptions
from briar.cli.database.retrieve import parseDatabaseRetrieveOptions
def database_create(options=None, args=None,input_command=None,ret = False):
    ''' Checkpoints a database without finalizing it '''
    # rpc database_checkpoint(DatabaseCheckpointRequest) returns(DatabaseCheckpointReply) {};
    if options is None and args is None and input_command is not None:
        options, args = parseDatabaseRetrieveOptions(input_command)
    else:
        options, args = parseDatabaseRetrieveOptions()

    client = briar_client.BriarClient(options)
    if options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]
    request = briar_service_pb2.DatabaseCreateRequest(database=briar_pb2.BriarDatabase(name=options.database))
    # request.database.name = options.database

    reply = client.stub.database_create(request)

    # print(reply)

    print("Database '{}' has been created".format(options.database, ))
    if ret:
        return reply
