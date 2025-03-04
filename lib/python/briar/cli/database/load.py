import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
from briar.cli.database.retrieve import parseDatabaseRetrieveOptions

def database_load():
    ''' Loads a database from storage (in case the database needs a procedure for loading from disk into memory)'''
    # rpc database_checkpoint(DatabaseCheckpointRequest) returns(DatabaseCheckpointReply) {};

    options, args = parseDatabaseRetrieveOptions()

    client = briar_client.BriarClient(options)
    if options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]
    request = briar_service_pb2.DatabaseLoadRequest(database=briar_pb2.BriarDatabase(name=options.database))
    # request.database.name = options.database

    reply = client.stub.database_load(request)

    # print(reply)

    print("Database '{}' has been Loaded".format(options.database, ))
