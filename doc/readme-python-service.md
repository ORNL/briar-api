# BRIAR API


## Introduction

This document is intended to describe how to integrate a performer's implementation with the necessary code to allow it to communicate to the Briar API.

The Briar API is designed to create a unified method of interfacing with different algorithms created across different teams of performers, with the gRPC communication layer acting as a cross-platform, cross-language API to aid the design of algorithms and the services which implement them. The client offers a number of functions, such as detect, extract, enroll, enhance, etc. which allow users to construct requests to run said functions on a gRPC service which may run both locally or on a network-connected system.

The face/body detection/identification algorithms can be written in any language supported by gRPC <https://grpc.io/docs/languages/> using BRIARService in 'briar_service.proto'. This 'proto file' is compiled into stubs for other languages, allowing abstract implementation of services to be written in said languages and hook into the client using gRPC messages. An example of one of these services is a python implementation in 'service.py' which illustrates a very simple, working example of a BRIAR service, whose workings can be extrapolated to whatever language implementation which is desired. As this an API and not an implementation of an algorithm, the provided example python service does not implement the detect, extract, etc. functions but does provide a lightly documented example to aid performers in creating their own services to run their algorithms.

If the performer wants a template for a python service then they can create a service class which inherits from BRIARService() in service.py, or they can use the class BRIARServiceServicer in srvc_pb2_grpc.py (a compiled proto-file) if a blank slate is desired.


## Using the API and Creating your algorithms

The gRPC stubs and server/client implementation makes BRIAR unique as an API implementation and may not be intuitive at first glance, hence the need of this section.

### Supported languages

Because the API uses gRPC as an interface between the client which implements the command line and some other base functions and the service which shall implement your code, your service can be implemented in whatever languages which are supported by gRPC. Here is a link to the supported languages <https://grpc.io/docs/languages/>

While python is used extensively in the documentation to illustrate functionality, any language supported by gRPC can be used in its place.

### Protobuf files

Before creating your own implementations, it will be helpful to understand how gRPC is being leveraged for cross-platform, cross-language communication between the BRIAR API and projects which are derived from it.

Protobuf files (found [Here](/proto/briar/briar_grpc)) are files ending in '.proto' which outline the functions accessible to the API. They are easily modifiable, cross language files formatted similarly to C++ which define gRPC objects and may be compiled into gRPC stubs with the script `build-proto-stubs.sh`. The compilation creates stubs, which are importable source files, in a number of languages, allowing programs written in said languages to be called from BRIAR clients. Effectively, the gRPC layer can be thought of a cross-language API, allowing any of the languages supported by gRPC to be used as part of the larger BRIAR ecosystem, so long as the messages passed between client and service are the ones defined within the BRIAR protobuf files.

An important section of the proto files, the BRIARService, is shown in part below.

~~~
service BRIARService{
    rpc status(StatusRequest) returns (StatusReply){};
    rpc detect(stream DetectRequest) returns (stream DetectReply){};
    rpc extract(stream ExtractRequest) returns (stream ExtractReply){};

    ... more definitions
}
~~~

This is where the api functions (technically service methods) are defined. `rpc function_name(request_type)` defines the function, and what kind of request it expects, and `returns(reply_type)` defines what kind of reply is expected. These request and reply messages, defined within [briar_service.proto](proto/briar/briar_grpc/briar_service.proto), define the data that is passed to and returned by the service's functions. When compiled, two abstract service classes are created: `BRIARServiceStub` for the client and `BRIARServiceServicer` for the service.

`BRIARServiceServicer` should be inherited by your service class so you can write your own method implementations for it. When initialized, it will listen on the specified port for connections from clients and run the methods defined in the protobuf as it gets requests

`BRIARServiceStub`, referred to as 'stub', mirrors the methods of the service. I.e. the stub has stub.detect, stub.status, etc. which, when called, expect an appropriate request message such as a 'DetectRequest' or 'StatusRequest' which it will send to the connected service, and will return or yield the reply type defined in the 'returns' field in the protobuf definition.

#### Protobuf Files and gRPC - a Python Example

It is important to lead this section saying that the Briar API supports every language supported by gRPC and the python implementation of service.py and this section's examples do not limit the actual implementation of your programs to python.

Within the existing BRIAR code, the gRPC stubs are used to define the format and contents of the messages being passed between BRIAR clients and services. These gRPC messages can be conceptually divided into three types - requests, replies, and objects. Requests are sent by clients to services to invoke functions on the service side, replies are sent from services to clients to ferry back the results from the invoked method, and the objects are classes/structures suction as "Detection" or "BriarRect" which are used to hold data in a meaningful way as it is passed one way or the other. Which functions in the service accept what methods is defined within the BRIARService service in the briar_service.proto file

For an example of how a client invokes a request and gets a reply, look at the status function in briar_client. Within the function, there are these lines:

~~~{.py}
# Establishing a connection to the service
self.channel = grpc.insecure_channel(port,options=channel_options)
# Creating the stub
self.stub = srvc_pb2_grpc.BRIARServiceStub(self.channel)
~~~

and 

~~~{.py}
# Getting the service's status
reply = self.stub.status(srvc_pb2.StatusRequest())
print(reply.developer_name, reply.service_name, reply.version, reply.status)
~~~

As stated before, BRIARService in the briar_service.proto defines the service, and BRIARServiceStub contains 'network calls' to methods on the service side. The line with `self.stub.status(srvc_pb2.StatusRequest())` initializes a status request message and passes it to the stub which then calls the network code and passes the message on to the connected service. The service will receive the status request and, because `self.stub.status` was called, the service will call its 'status' function when it handles the incoming network message. Below is the code where that happens

~~~{.py}
    def status(self, request, context):
        return srvc_pb2.StatusReply(developer_name="[devname-here]",
                                     service_name="This is a service",
                                     version=briar_pb2.APIVersion(major=1,
                                                                  minor=2,
                                                                  patch=3),
                                     status=briar_pb2.BriarServiceStatus.READY)
~~~

The service code above constructs a StatusReply message. The returned values will pass back through the gRPC backend and be sent over the network back to the client and be put into the variable 'reply'. From there, it can be accessed like any other class.

~~~{.py}
print(reply.developer_name, reply.service_name, reply.version, reply.status)
~~~

The official documentation for how services implement requests, methods, and replies can be found here <https://grpc.io/docs/what-is-grpc/core-concepts/>


### Creating a Python Service Example

This section will illustrate how to implement your own algorithms with the API using python, but the steps here can be applied to other languages as well. For convenience, let's assume you are working on a project named **BARB** which uses the BRIAR API.

You will want to add your algorithms in a service file which will inherit from the BRIARServiceServicer. Below are the steps to take.

1. Create the file barb_service.py and add the imports
~~~~
from concurrent import futures
import grpc
import time

from briar import media_converters, Rect
from briar.functions import new_uuid
from briar.service import BRIARService

from briar.briar_grpc.briar_pb2 import Attribute, BriarDurations, BriarRect, Detection
from briar.briar_grpc.briar_service_pb2 import DetectReply
from briar.briar_grpc.briar_service_pb2_grpc import add_BRIARServiceServicer_to_server
~~~~

2. Create a new class which inherits from BRIARService
~~~{.py}
class BARBService(BRIARService):
    def __init__(self, options=None, database_path="databases"):
        super(BARBService, self).__init__()
~~~

3. Implement one or more of the methods defined in BRIARService. 'detect' will be used as an example  
~~~{.py}
    def detect(self, request_iter, context):
        # Iterate over requests as the client sends them
        for detect_request in request_iter:
            t0 = time.time()

            # break out the request's attributes for clarity
            protobuf_media = detect_request.media
            frame_num = detect_request.frame
            subject_id = detect_request.subject_id
            subject_name = detect_request.subject_name
            detect_options = detect_request.detect_options

            # Convert the protobuf byte vector back into a numpy array
            numpy_img = media_converters.image_proto2cv(protobuf_media)

            # run the detection algorithm
            roi, det_class, score = self.detect_worker(numpy_img)

            # populate the gRPC detection class
            t1 = time.time()
            loc = BriarRect(x=roi.x, y=roi.y, width=roi.width, height=roi.height)
            detection = Detection(confidence=score, location=loc, frame=frame_num, detection_id=1,
                                  detection_class=det_class)
            t2 = time.time()

            # Create an arbitrary attribute to use
            attrib1 = Attribute(key="Attribute1",
                                text="AttributeText")
            attrib2 = Attribute(key="Attribute2",
                                fvalue=0.25)
            attrib3 = Attribute(key="Attribute3",
                                buffer="ByteArray".encode("utf-16"))

            # python GRPC doesn't like direct assignment of iterables. Use CopyFrom instead.
            detection.attributes.MergeFrom([attrib1, attrib2, attrib3])

            detect_reply = DetectReply()
            detect_reply.detections.append(detection)
            detect_reply.frame_id = frame_num

            # Briar has a 'durations' grpc_object to easily store and return timing metrics
            # durs = BriarDurations()
            detect_reply.durations.durations["detection_time"] = (t2-t1)*1e6 # Durations are tracked in microseconds
            detect_reply.durations.total_duration = (time.time()-t0)*1e6

            print("Yielding")
            yield detect_reply

    def detect_worker(self, numpy_img):
        # ... do detection stuff
        roi = Rect(5, 5, 25, 25)
        det_class = "FACE"
        score = 0.99

        return roi, det_class, score
~~~

4. Add \_\_main\_\_
~~~{.py}
if __name__ == "__main__":
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         options=[('grpc.max_send_message_length', 20000000),
                                  ('grpc.max_receive_message_length', 20000000)])
    add_BRIARServiceServicer_to_server(BARBService(), server)
    server.add_insecure_port("0.0.0.0:50051")
    server.start()
    # server.wait_for_termination()

    print("Service Started.  ")
    while True:
        time.sleep(0.1)
~~~

5. Run `python barb_service.py`
   1. You should see `Service Started.`
6. In another terminal, run `python -m briar detect /some/path/to/an/image/file.jpg`
   1. The client will automatically read the image file and send a detect request to the example BARB service (defaults to connecting to 127.0.0.1:50051 if no connection parameters given)
   2. The service will call self.detect, enter into the main iterator, and iterate once (if you gave a single file) and yield a single detect reply which will return to the client, which has its own iterator.
   3. You can provide multiple image files with the command line
      - `python -m briar detect img1.jpg img2.jpg img_dir`
7. A stacktrace related to gRPC will likely occur during integration of algorithms with the BRIAR-API. Because gRPC is a message passing language, an error in a performer's implementation will result in a error propagated through the BRIAR client. Error messages from gRPC can be opaque as shown by the following example:

~~~
  File "/home/ii1/anaconda3/envs/insightface/lib/python3.8/site-packages/grpc/_channel.py", line 426, in __next__
    return self._next()
  File "/home/ii1/anaconda3/envs/insightface/lib/python3.8/site-packages/grpc/_channel.py", line 809, in _next
    raise self
grpc._channel._MultiThreadedRendezvous: <_MultiThreadedRendezvous of RPC that terminated with:
        status = StatusCode.UNKNOWN
        details = "Exception iterating requests!"
        debug_error_string = "None"
~~~
8. Seeing this on the client end most likely means there was an issue with the service implementation, and server side debugging may be required. You will see this message anytime the implemented service fails to return a valid reply message.
