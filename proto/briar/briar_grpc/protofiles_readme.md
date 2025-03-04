# Protobuf Files

## Primer From Google

The main gRPC webpage at <https://grpc.io> is a good resource for basic information about gRPC. As a primer, the link below talks about concepts relating to grpc, protobuf, and streaming.

<https://grpc.io/docs/what-is-grpc/core-concepts/>



## Protobuf File Overview

The files in this folder are the 'uncompiled' protobuf files which define the messages and services which make up the BRIAR API. Using build-proto-stubs.sh in the repo's root folder, these .proto files can be compiled into stubs of multiple languages which will be used by both the BRIAR client and services which implement performer algorithms. Linked below are the three protobuf files defining the API

- briar.proto
- briar_service.proto
- briar_error.proto



### briar.proto

This file defines the messages which represent objects such as detections, rectangles, and other pieces of information which need to be sent between clients and services. These objects will be contained inside the request and reply messages sent by the service and will not be sent between clients and services without an outer request or reply wrapper. Aside from those few details, these messages are not particularly remarkable and shoudl be reasonably self documenting.



### briar_service.proto

This file contains definitions for the BRIAR Service which defines the methods which the clients can invoke in services and the arguments they can pass between each other.

In BRIARService, you will notice multiple lines starting with 'rpc'. These define which methods are special 'gRPC methods' which can be invoked by the client. Upon compilation, the protobuf files will create BRIARServiceStub and BRIARServiceServicer classes, the former serves as the method calls for the client, and the latter which serves as the inheritable class for the service.

On the client side, after connecting a channel and initializing the stub, the stub can run a method on the service as simply as calling the method with an appropriate request as an argument. For example:
~~~
reply = stub.status(status_request)
~~~
where 'status_request' is an initialized StatusRequest class. This will run the code inside the status method in the service, which should return a 'StatusReply' which will then be assigned to the variable 'reply'

 This will be different for rpc lines marked with the 'stream' argument in either the method field and/or the 'returns' field, which means the data will be streamed unilaterally or bi-laterally depending on which fields have the 'stream' decleration.



 ### briar_error.proto

 A simple error class for storing error information which can be returned as an argument in any of the reply messages. Used for telling the client that the service experienced a handled error and providing relevant details, especially since gRPC's error messages can be needlessly confounding at times