"""!
"""
import briar.briar_grpc.briar_service_pb2_grpc as srvc_pb2_grpc
import grpc
import os
import time
import multiprocessing as mp
from concurrent import futures
import datetime
__version__ = '2.4.5'

import briar.briar_grpc.briar_service_pb2_grpc
from sys import platform
PLATFORM = "UNKNOWN"
if platform == "linux" or platform == "linux2":
    PLATFORM = "linux"
elif platform == "darwin":
    PLATFORM = "darwin"
elif platform == "win32":
    PLATFORM = "windows"

DEFAULT_PORT_FALLBACK = "0.0.0.0:50051"
#get the default port from the environment variable BRIAR_PORT if it exists.  Otherwise, default to DEFAULT_PORT_FALLBACK
DEFAULT_PORT = os.getenv("BRIAR_PORT", DEFAULT_PORT_FALLBACK)
DEFAULT_SERVE_PORT = '[::]:50051'
DEFAULT_MAX_MESSAGE_SIZE = 64 * 1024 * 1024 *8 # 512MB
_ONE_DAY = datetime.timedelta(days=1)

class Rect:
    """
    Basic rectangle for storing ROIs without needing to mess with the gRPC BriarRect
    """

    def __init__(self, x, y, width, height):
        """    
    The __init__ function is called when the class is instantiated.
    It sets up the object with its initial state.
    
    
    :param self: Represent the instance of the class
    :param x: Set the x coordinate of the rectangle
    :param y: Set the y coordinate of the rectangle
    :param width: Set the width of the rectangle
    :param height: Set the height of the rectangle
    :return: Nothing
    :doc-author: Joel Brogan
    """
        self.x = x
        self.y = y
        self.width = width
        self.height = height


# try:
#     BRIAR_DIR = os.environ["BRIAR_DIR"]
# except Exception as e:
#     raise EnvironmentError("The Briar root directory environment variable (BRIAR_DIR) is not set "
#                            "in your environment")

def dyn_import(name):
    """
The dyn_import function is a helper function that allows you to import modules
dynamically.  This means that you can pass in the name of a module as a string, and
the dyn_import function will return the actual module object.  For example:

:param name: Specify the name of the module to be imported
:return: A module object
:doc-author: Joel Brogan
"""
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod
def _wait_forever(server):
    """
The _wait_forever function is a simple function that waits forever.
It's used to keep the server running until it receives a KeyboardInterrupt (Ctrl+C).


:param server: Stop the server
:return: Nothing
:doc-author: Joel Brogan
"""
    try:
        while True:
            time.sleep(_ONE_DAY.total_seconds())
    except KeyboardInterrupt:
        server.stop(None)
def get_process_number():
    """
The get_process_number function returns the process number of the current process.
The main process is denoted by a 0 while all other processes are 1-indexed.
:return: The process number of the current process
:doc-author: Joel Brogan
"""
    try:
        proc_number = int(mp.current_process().name.split('-')[-1]) #
    except:
        proc_number = 0

    return proc_number
def get_thread_number():
    """
The get_thread_number function returns the thread number of the current thread.

:return: The thread number of the current thread
:doc-author: Joel Brogan
"""
    try:
        thread_number = int(threading.current_thread().name.split('-')[-1])
    except:
        thread_number = 0
    return thread_number
def serve(serviceClass, options=None, serve_port=None):
    """
The serve function is the main entry point for a BRIARService. It initializes and runs the service until killed.
Initialize and run the BRIARService. Runs until killed
:param serviceClass: Specify the service class to be used
:param options: Pass in the configuration options for the service
:param serve_port: Specify the port to serve on
:return: A server object
:doc-author: Joel Brogan
"""

    if options is not None:
        max_message_size = options.max_message_size
    else:
        max_message_size = DEFAULT_MAX_MESSAGE_SIZE * 8
    worker_count = 10
    if options is not None:
        msize = options.max_message_size
        worker_count = options.thread_per_service_count
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=worker_count),
                                 compression=grpc.Compression.Gzip,  # Default for responses
        compression_algorithms=[  # This sets supported decompress algorithms for incoming requests
            grpc.Compression.Gzip,
            grpc.Compression.Deflate,  # Comment out if not available in your grpcio
            grpc.Compression.NoCompression
        ],
                         options=[('grpc.max_send_message_length', max_message_size),
                                  ('grpc.max_receive_message_length', max_message_size),
                                  ("grpc.so_reuseport", 1),],maximum_concurrent_rpcs=worker_count*2) #we add +1 to ensure the queue doesn't hit a resource exhausted limit
    service_object = serviceClass(options=options)
    service_object:briar_grpc.briar_service_pb2_grpc.BRIARService
    allports = parse_ports(options)
    #add important configuration information to the service
    try:
        procnumber = int(mp.current_process().name.split('-')[-1])
    except:
        procnumber = 0
    setattr(service_object, 'process_number', procnumber)
    setattr(service_object, 'server_count', len(allports))
    setattr(service_object,'service_per_port_count',options.service_per_port_count)
    setattr(service_object, 'thread_per_service_count', options.thread_per_service_count)
    setattr(service_object,'port_list',allports)
    setattr(service_object, 'base_port', allports[0])

    srvc_pb2_grpc.add_BRIARServiceServicer_to_server(service_object, server)
    if serve_port is None:
        if options is not None:
            serve_port = options.port
        else:
            serve_port = DEFAULT_SERVE_PORT
    elif isinstance(serve_port,list):
        serve_port = serve_port[0]
    server.add_insecure_port(serve_port)
    server.start()

    print("Service Process",service_object.process_number,"with", service_object.thread_per_service_count,"internal threads Started on port ", serve_port, ".")
    # server.wait_for_termination()
    _wait_forever(server)
    # while True:
    #     time.sleep(0.1)

def multiproc_serve(serviceClass, options=None, serve_port=None):
    """
The multiproc_serve function is a wrapper around the serve function that allows
multiple instances of the same service to be run on different ports. This is useful
for running multiple instances of a service in parallel, which can improve performance.
The multiproc_serve function takes three arguments:

:param serviceClass: Specify the class of service that is being served
:param options: Pass in the options for the service
:param serve_port: Specify the port that the server will listen on
:return: The return value of the serve function
:doc-author: Joel Brogan
"""
    proc_count = options.service_per_port_count
    workers = []
    if isinstance(serve_port,str):
        serve_ports = [serve_port]
    else: #serve_port is already a list
        serve_ports = serve_port
    for serve_port in serve_ports:
        for i in range(proc_count):
            # NOTE: It is imperative that the worker subprocesses be forked before
            # any gRPC servers start up. See
            # https://github.com/grpc/grpc/issues/16001 for more details.
            worker = mp.Process(
                target=serve, args=(serviceClass, options, serve_port,)
            )
            worker.start()
            workers.append(worker)
    for worker in workers:
        worker.join()

def parse_ports(options):
    """
The parse_ports function takes in a string of ports separated by commas, and returns a list of strings.
If the port range is greater than 1, then it will return a list with all the ports in that range.
For example: parse_ports(&quot;localhost:8080&quot;) -&gt; [&quot;localhost:8080&quot;]
             parse_ports(&quot;localhost:8000-8002&quot;) -&gt; [&quot;localhost:8000&quot;, &quot;localhost:80001&quot;, &quot;locahostl8002&quot;]

:param options: Parse the command line arguments
:return: A list of ports
:doc-author: Joel Brogan
"""
    all_ports_parts = options.port.split(',')
    all_ports = []
    # parse all of the ports listed in the options, separated by a comma
    for p in all_ports_parts:
        if len(p) > 0:
            all_ports.append(p)

    assert len(all_ports) > 0 and (options.port_range == 1 or (len(all_ports) == 1 and options.port_range > 1))

    # populate the port list if a range is specified
    if options.port_range > 1:
        starting_port_parts = all_ports[0].split(':')
        starting_port = starting_port_parts[-1]
        address = all_ports[0].split(":"+starting_port)[0]
        starting_port = int(starting_port)
        all_ports = []
        for i in range(options.port_range):
            all_ports.append(address + ":" + str(starting_port + i))
    return all_ports

def CLIServe(serviceClass,add_custom_options=None):
    """
    :param serviceClass: The class that contains the implementation of the service to be served.
    :param add_custom_options: A function that can be used to add custom options to the command line parser.
    :return: None

    This method sets up a command line interface (CLI) for serving a gRPC service. It takes in a serviceClass parameter that represents the class containing the implementation of the service
    * to be served. It also takes an optional add_custom_options parameter, which is a function that can be used to add custom options to the command line parser.

    The method uses the `optparse` module to define and parse command line options. It creates an instance of `OptionParser`, sets some default options and help text, and defines several
    * command line options such as verbosity, maximum message size, port number(s), port range, number of services per port, and number of threads per service.

    If the add_custom_options parameter is not None, it calls the add_custom_options function to add custom options to the command line parser.

    The method then parses the command line arguments using the `parse_args` method of the `OptionParser` instance. The parsed options and arguments are stored in the `options` and `args
    *` variables, respectively.

    Depending on the number of ports specified or the number of services per port, the method either invokes the `multiproc_serve` function or the `serve` function to start serving the service
    *. In case of an IndexError exception, an AssertionError is raised.

    Note: This method assumes the existence of other functions and variables such as DEFAULT_MAX_MESSAGE_SIZE, DEFAULT_SERVE_PORT, and parse_ports, which are not provided in the given code
    * snippet.
    """
    import optparse
    parser = optparse.OptionParser(usage='python service.py [OPTIONS]',
                                   conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")
    parser.add_option("--max-message-size", type="int", dest="max_message_size",
                      default=DEFAULT_MAX_MESSAGE_SIZE,
                      help="Maximum gRPC message size. Set to -1 for unlimited. Default=%d" % (
                              DEFAULT_MAX_MESSAGE_SIZE))
    parser.add_option("-p", "--port", type="str", dest="port", default=DEFAULT_SERVE_PORT,
                      help="The port(s) used for the recognition service, separated by a comma. A duplicate set of services will be started on each "
                           "Default={}".format(DEFAULT_SERVE_PORT))
    parser.add_option("--port-range", type="int", dest="port_range",
                      default=1,
                      help="If --port is singular, this is a shortcut to define contiguous set of multiple ports. e.g. --port localhost:50051 --port-range 4 would create services an 50051-50054. Default=1")
    parser.add_option("--services-per-port", type="int", dest="service_per_port_count",
                      default=1,
                      help="Number of gRPC servers to run at once on a single port. These act as processes and are auto-load balanced by so_reuseport. Each service will receive --worker-count amount of video streams at once Default=1")
    parser.add_option("--threads-per-service", type="int", dest="thread_per_service_count",
                      default=1,
                      help="Defines the number of video streams each service can process at once before reporting RESOURCE_EXHAUSTED. Default=10")
    if add_custom_options is not None:
        add_custom_options(parser)

    (options, args) = parser.parse_args()
    if options.service_per_port_count > 1 and briar.PLATFORM == 'darwin':
        raise OSError("SO_REUSEPORT is not implemented to load-balance in MacOS. --services-per-port must be set to 1.")

    all_ports = parse_ports(options)
    if len(all_ports) > 1 or options.service_per_port_count > 1:
        multiproc_serve(serviceClass,options=options, serve_port=all_ports)
    else:
        serve(serviceClass, options=options, serve_port=all_ports)
        assert IndexError
