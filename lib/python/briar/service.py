"""!
Systems based off the BRIAR API will come in two parts: the BRIAR client (which shouldn't need to be extended and
is the api itself since it is the 'hooks' which connect into gRPC) and the Service which runs wherever you want
the image processing to be performed. Any machine learning, neural networks, image processing, etc should take
place within performer designed services and this file, containing the BRIARService, exists as a basic framework
for creating these other services and does nothing significant on is own.

The Service itself runs as a server which can accept gRPC calls on the specified port. These calls are defined
within briar_service.proto under in the "BRIARService" service. Each line will look like:

- rpc status(StatusRequest) returns (StatusReply){};

or

- rpc detect(stream DetectRequest) returns (stream DetectReply){}

where the name after 'rpc' will define which method to call and 'stream' prefixing a request will define said
request to be an iterable on client side, server side, or both. Whenever the service gets receives a request
matching one which is defined, it will invoke the associated method defined within the class, (i.e. the line
"rpc detect(...." will cause BRIARService.detect to run with the Detect Request acting as the argument.

In the case of a stream, the client is expected to yield when "stream" prefixes the reply, and the server is
expected to yield when "stream" prefixes the request within the rpc decleration. For example, when the server
is streaming, on the server side the code will need to yield replies, and on client-side you will put the
service_stub.method_name in a loop.

- for reply in service_stub.method_name(DetectRequest):

When the client is streaming the client will yield requests and on the server-side you will put the request
iterator in a loop.

- for request in request_iterator:

In case both are streaming, then both will yield, and both will iterate in a ping-pong fashion, yielding back and
forth to each-other.
"""
import briar.briar_grpc.briar_pb2
import briar.briar_grpc.briar_pb2_grpc
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.briar_grpc.briar_service_pb2_grpc as srvc_pb2_grpc
import grpc
import logging
import multiprocessing as mp
import os
import random
import time
import traceback
import uuid
from briar import DEFAULT_SERVE_PORT
from briar.media_converters import *
from concurrent import futures


class BRIARService(srvc_pb2_grpc.BRIARServiceServicer):
    """

    """
    process_number = None
    server_count = None
    service_per_port_count = None
    thread_per_service_count = None
    port_list = None
    base_port = briar.DEFAULT_SERVE_PORT

    def __init__(self, options=None, database_path="databases"):
        """!
        @param options optparse.Values: Command line options to control the service

        @param database_path str: Path to where to save generated data
        """
        super(BRIARService, self).__init__()


        self.options = options

    def get_api_version(self, request, context):
        return briar_pb2.APIVersion(major=1, minor=2, patch=3)

    def status(self, request, context):
        """!
        @param request briar_service_pb2.StatusRequest: Request containing options for the get status request

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.StatusReply
        """
        return srvc_pb2.StatusReply(developer_name="[devname-here]",
                                    service_name="This is a service",
                                    version=briar_pb2.APIVersion(major=1,
                                                                 minor=2,
                                                                 patch=3),
                                    status=briar_pb2.BriarServiceStatus.READY)

    def detect(self, req_iter, context):
        """!
        Streams image data in the form of a extract request iterator. Takes images, detects contents, and
        creates detections using provided detections.

        @param req_iter Generator(briar_service_pb2.DetectRequest): Detections happen as a part of an iteration
                         part of a for loop. Will yield a DetectRequest containing a detect and other info.

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: Each iteration should yield a DetectReply
        """
        raise NotImplementedError

    def extract(self, req_iter , context):
        """!
        Streams image data in the form of a extract request iterator. Takes images,
        extracts faces, and creates templates using provided detections, auto detection,
        or the full image as specified by the extract flag. Returns templates representing
        faces in the media

        @param req_iter Generator(briar_service_pb2.ExtractRequest): Extracts happen as a part of an iteration
                         part of a for loop. Will yield a ExtractRequest containing templates and other info
                         resulting from extractions

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: Each iteration yields a ExtractReply
        """
        raise NotImplementedError

    def enroll(self, req_iter, context):
        """!
        Streams images or templates in the form of an enroll request iterator. Takes images, optionally
        detects, and extracts them to create templates using provided detections, auto detection,
        or the full image as specified by the extract flag. Enrolls templates into the database

        @param req_iter Generator(briar_service_pb2.EnrollRequest): Enrolls (and optional detects and extracts) happen as a part of an iteration
                         request_iter will need to be part of a for loop. Will yield a EnrollRequest containing
                         info resulting from enrolls.

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: Each iteration should yield a EnrollReply
        """
        print("Enrolling...")
        raise NotImplementedError

    def verify(self, request , context):
        """!
        @brief: Calculate how similar sets of templates are

        @param request briar_service_pb2.VerifyRequest: Request to verify containing templates/media to compare

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service.VerifyReply
        """
        print("Verifying template matches")
        raise NotImplementedError

    def search(self, request , context):
        """!
        Search database for templates matching the provided probe

        @param request briar_service_pb2.SearchRequest: Request to search containing template and name of database to search

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.SearchReply
        """
        print("Searching Templates")
        raise NotImplementedError

    def cluster(self, request : srvc_pb2.ClusterRequest, context):
        """!
        Takes a set of templates and clusters them, matching according to subject similarity

        @param request briar_service_pb2.ClusterRequest: Templates name to cluster

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.ClusterReply
        """
        raise NotImplementedError

    def enhance(self, request , context):
        """!
        Run an enhancement on a provided image

        @param request briar_service_pb2.EnhanceRequest: Contains image(s), enhancement options, and type of enhancement to run

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.EnhanceReply
        """
        raise NotImplementedError

    def database_create(self, request : srvc_pb2.DatabaseCreateRequest, context):
        """!
        Create a new database and populate it with templates

        @param request briar_service_pb2.DatabaseCreateRequest: Request with database name and optionally templates

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.DatabaseCreateReply
        """
        raise NotImplementedError

    def database_rename(self, request : srvc_pb2.DatabaseRenameRequest, context):
        raise NotImplementedError

    def database_refresh(self, request : srvc_pb2.Empty, context):
        raise NotImplementedError
    def database_load(self, request : srvc_pb2.DatabaseLoadRequest, context):
        """!
        Load the database specified in the load request

        @param request briar_service_pb2.DatabaseLoadRequest: Request containing database name to load

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @reply: briar_service_pb2.DatabaseLoadReply
        """
        raise NotImplementedError

    def database_insert(self, request : srvc_pb2.DatabaseInsertRequest, context):
        """!
        Inserts the templates contained in the request into a specified database

        @param request briar_service_pb2.DatabaseInsertRequest: Request containing database name and templates to insert

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.DatabaseInsertReply
        """

        raise NotImplementedError

    def database_retrieve(self, request : srvc_pb2.DatabaseRetrieveRequest, context):
        """!
        Retrieves the templates contained in the database matching the provided names

        @param request briar_service_pb2.DatabaseRetrieveRequest: Request containing the database name to pull templates from

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.DatabaseRetrieveReply
        """
        raise NotImplementedError

    def database_remove_templates(self, request, context):
        """!
        Takes the ids in 'request' and removes them from the database

        @param request briar_service_pb2.DatabaseRemoveTmplsRequest: Request containing database name and template ids to remove

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.DatabaseRemoveTmplsReply
        """
        raise NotImplementedError

    def database_names(self, request, context):
        """!
        Produces a list of database names contained in the specified database

        @param request briar_service_pb2.DatabaseNamesRequest: Request. No additional options

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.DatabaseNamesReply
        """
        raise NotImplementedError

    def database_list_templates(self, request, context):
        """!
        Produces a list of templates contained in the specified database

        @arg request: briar_service_pb2.DatabaseListRequest
        @param request: Request containing database name to list

        @param context grpc.ServicerContext: object that provides RPC-specific information such as timeout limits.

        @return: briar_service_pb2.DatabaseListReply
        """
        raise NotImplementedError

    def database_finalize(self, request, context):
        """!
        @brief: Finalizes the database and saves it to the disk

        @param request briar_service_pb2.DatabaseFinalizeRequest: Request.

        @return: briar_service_pb2.DatabaseFinalizeReply
        """
        raise NotImplementedError
    def database_checkpoint_subject(self, request, context):
        """
    The database_checkpoint_subject function is used to checkpoint a subject in the database.

    :param self: Represent the instance of the class
    :param request: Get the subject_id from the client
    :param context: Pass information about the grpc call
    :return: A checkpointsubjectresponse
    :doc-author: Joel Brogan
    """
        raise NotImplementedError

    def get_service_configuration(self, request, context):
        reply = srvc_pb2.BriarServiceConfigurationReply()
        reply.number_of_service_ports = self.server_count
        reply.number_of_processes_per_port = self.service_per_port_count
        reply.number_of_threads_per_process = self.thread_per_service_count
        reply.reporting_process_number = self.process_number
        reply.base_port = self.base_port
        reply.port_list.MergeFrom(self.port_list)
        return reply


if __name__ == '__main__':
    logging.basicConfig()
    briar.serve()
