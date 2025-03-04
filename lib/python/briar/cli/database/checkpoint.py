import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2

from briar.cli.database.retrieve import parseDatabaseRetrieveOptions







def database_checkpoint(options=None, args=None,input_command=None,ret = False):
    ''' Checkpoints a database without finalizing it '''
    # rpc database_checkpoint(DatabaseCheckpointRequest) returns(DatabaseCheckpointReply) {};

    options, args = parseDatabaseRetrieveOptions(inputCommand=input_command)

    client = briar_client.BriarClient(options)

    if options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]
    print('Checkpointing database', database)
    request = briar_service_pb2.DatabaseCheckpointRequest(database=briar_pb2.BriarDatabase(name=options.database))
    # request.database.name = options.database

    # print(request)
    reply = client.stub.database_checkpoint(request)

    # print(reply)

    print("Database '{}' has been checkpointed".format(database, ))
