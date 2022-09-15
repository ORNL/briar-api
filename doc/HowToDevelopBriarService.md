# How to develop a BRIAR Service

## Authors

| Name | Organization |
| ------ | ------ |
| Deniz Aykac | Oak Ridge National Laboratory |
| David Bolme | Oak Ridge National Laboratory |
| Joel Brogan | Oak Ridge National Laboratory |
| Ian Shelley | Oak Ridge National Laboratory |
| Bob Zhang | Oak Ridge National Laboratory |

<!-- Developing a BRIAR Service (External File)
   * Introduction
   * How the gRPC works in a nutshell (And also the BRIAR API)
   * Building Stubs
   * Submitting Containers
     * docker
     * singularity
     * Starting your container
   * Testing your algorithms using the API
   * Version Requirements
     * Phase 1
     * Phase 2
     * Phase 3
   * Quick Reference

 -->


## Table of Contents
[[_TOC_]]

## Introduction
This document will give you a quick guide on how to take the algorithms you've developed for BRIAR and make them conform and communicate with the BRIAR API.  Throughout this document we will use examples from the BRIAR API Example code which is developed in the Python language.

### How the gRPC works in a nutshell (And also the BRIAR API)
The BRIAR API is implemented using the [google Remote Procedure Call (gRPC) framework](https://grpc.io/). The BRIAR API uses this paradigm to interact with performer implementations via a **Client-Server Interface**, where performers' implementations of algorithms comprise a **Server**, while a already implemented API comprises the **Client**.  In this way, the BRIAR Client can seamlessly interact with algorithms written in many different languages. To accomplish this, a set of protobuf messages are defined that can be passed between the client and server as requests and responses to different function calls. *All performers must do is implement code for each function that accept input and generate output in the form of these messages.*

gRPC is a proto-language that defines a **service** which contains multiple **functions** that each pass strictly defined **messages** back and forth.  **Messages** can be thought of as class definitions, and are defined to have strongly-typed **fields**.  These **fields** can either be primitive types, or other messages themselves. The files that define the proto structure for BRIAR are located in [proto/briar/briar_grpc](proto/briar/briar_grpc)

**As a performer, you must implement the functions defined by the BRIAR API protocol:**
~~~
Commands:
    status - Connects to the server and displays version and status information.
    detect - Only run detection.
    extract - Run feature extraction.
    enroll - Extract and enroll biometrics in a database.
    search - Search database for media and IDs that contain biometric matches to the query.
    finalize - Finalize a database.
    sigset-stats - Convert a sigset to a csv file.
    sigset-enroll - Enroll a sigset in a database.
~~~

To wrap your algorithms in the correct code that can communicate over gRPC to the BRIAR client, we will need the compiled stub files, service files, and message files for your specific language to continue.  [Jump to this section](#building-stubs) to learn how to run the protoc compiler to automatically generate these stubs.

Compiled protobuf code provides an **abstract service implementation** as a class, filled with **unimplemented functions** in any given language desired by the performer. These abstract classes should be subclassed by performers, with unimplemented functions subsequently implemented to wrap performer code to comply with the specific **BRIAR input and output messages types** provided by the Protoc compiler. 

## Building Stubs

To install protoc, use the installation instructions provided here: https://grpc.io/docs/protoc-installation/ 

In the root directory of the repository, there is a script to handle stub compilation for you. To build the stubs from the .proto files, run
`./build-proto-stubs.sh`

Stubs will be generated in the directory `lib` directory for a variety of popular languages including C++, CSharp, JavaScript, Objective-C, PHP, Python, and Ruby.  This stubs will allow developers to produce both clients and services in each of these languages.

## Submitting Containers
For evaluation the these containers will be run using `singularity` or `podman` due to data security requirements for ORNL computer systems.  Containers will be run in user space and will not have root permissions.  Each container will expose a port on the localhost interface that will be used for gRPC communications to the BRIAR API.  The container will also be provided with a data directory that will be used for persistent storage across runs.

The container should contain everything needed to run the BRIAR service including software dependencies, trained machine learning models, configuration files, etc.  The solution is expected to be automatic and easy to use with appropriate default parameters.  On start up the container will boot the software solution, initialize software and models as needed.  The software can initialize and load any data from previous runs in the persistent storage.  The software will also expose the gRPC service to the external network port 50051 and will be ready to accept client connections.

All R&D teams will be provided with the same testing client as well as supporting files and scripts used by the BRIAR T&E team.  Performers should conduct internal testing of their solutions before submission to insure the container operates correctly.  Experiments will typically consist three steps:
 1. enrolling subject media into a gallery database
 2. enrolling field videos and images into a probe database
 3. conducting searches and verifications of the probe entries against the gallery entries to generate search results or score matrices

To save computational time teams will need to implement gRPC calls to merge, split, and reorganize the templates in probe and gallery databases to support a variety of tests without re-enrolling the media. Starting in Phase 2, performers may also be expected to implement more specialized template fusion methods.

Most evaluations on the deliverables will treat the software as a black box and will only interface through the gRPC calls.  This means that teams should have complete freedom to implement solutions as long as they conform to the public gRPC interface.  Creativity is encouraged.  Many gRPC function calls and data field are marked as OPTIONAL or REQUIRED.  Teams are responsible for implementing REQUIRED items, however some of the OPTIONAL interfaces may transition to REQUIRED as the program and the software matures.  The API is designed to be flexible and has many ways to pass additional data structures, options, and parameters to support and encourage teams to implement additional features beyond the core required capabilities.

Software will be submitted to ORNL using containers.  
 * Containers should include everything need to run and evaluate the software solution 
   including: dependencies, compiled software, ML models, configuration files, etc.  
   Source code is not needed and can be delivered separately.
 * Software will be delivered in two container types.
   * Docker - is the gold standard for containerization and so this deliverable will 
     allow government agencies an easy method to start up and run BRIAR software.
   * Singularity - is a container solution that addresses security issues with docker.  
     Converting containers from docker to singularity is relatively easy. However, 
     instead of running with root permission singularity will require user level
     permissions.
 * Simple commands will be used to start and stop containers. These must respect 
   certain environment variables which tell the container which ports to start up on 
   and which CPU, GPU, and Memory Limits are allocated to the container. The start and stop commands for BRIAR example services are shown in the following sections.
 * A data directory will be mounted in the container that can be used for persistent 
   storage. This is primarily to store databases of templates but can be used for other
   configuration data as well. Data stored in other directories in the container will
   be wiped between runs.  

_Additional details to follow_

### Converting from docker to singularity 

The conversion from docker needs to take place on a machine with root permissions.  

1. Install singularity using this guide: https://sylabs.io/guides/3.8/user-guide/quick_start.html#quick-installation-steps

2. Singularity can convert the docker container to a singularity container using a command like this: `sudo singularity build briar-example.sif docker-daemon://briar-example:latest`

3. Move the singularity container to the target machine (root not access needed).

4. Run a shell to test the container `singularity shell --nv --no-home --cleanenv -B $BRIAR_DATA_DIR:/briar/briar_storage -H /briar ./briar-example.sif`

### Starting the container 

_Please double check this section before each deliverable.  Details on how 
solutions are started are subject to change through the course of the BRIAR 
program._

The evaluation environment will define variables that control the hardware resources 
allocated to each solution. Multiple versions of BRIAR software may also be run in 
parallel.

```
$ BRIAR_GRPC_PORT=127.0.0.1:50060 # Start the gRPC service on this port
$ MAX_MESSAGE_SIZE=134217728 # 128Mb
$ BRIAR_WORKERS=2 # Number of worker processes
$ BRIAR_GPUS=2,3 # Use only GPU 2 & 3
$ BRIAR_DATA_DIR=/briar/data/team1/experiment2
```

Performer teams should insure that the BRIAR services start and run correctly on both docker and singularity.

#### Docker
It is expected that government stake holders will use docker or compatible services to run BRIAR software.  Here we show a sample command.

```
docker run -e NVIDIA_DRIVER_CAPABILITIES=all --gpus all --shm-size=4g --net host -v $BRIAR_DATA_DIR:/briar/briar_storage --rm -it briar-exmaple python ./briar-exmaple/service.py -p $BRIAR_GRPC_PORT -w $BRIAR_WORKERS -g $BRIAR_GPUS --max-message-size=$MAX_MESSAGE_SIZE
```

#### Singularity
The current plan is to run all evaluations in singularity. There may be some issues converting to singularity since this will not run as a root process and permissions may need to be changed.

```
singularity run --nv --no-home --cleanenv -B $BRIAR_DATA_DIR:/briar/briar_storage -H ./briar-example ./briar-example.sif python  ./briar-example/service.py -p $BRIAR_GRPC_PORT -w $BRIAR_WORKERS -g $BRIAR_GPUS --max-message-size=$MAX_MESSAGE_SIZE
```

#### Command Line Tools
Once the service is started the command line tool can be used to test the service.  These instructions are found in the [BRIAR API Documentation](../README.mb)

## Evaluations

The services will be run using default parameters.  Services are expected to be completely automatic where video and images are provided and algorithms will auto-configure themselves and perform detection, tracking, extraction, and enrollment operations to ingest the media with no extra information.  Evaluations will be conducted using three steps:

1. Build a gallery database using the commands `python -m briar sigset-enroll --entry-type=subject --best ...` or `python -m briar enroll --entry-type=subject ...` commands.  This gallery will contain entries organized by a subject ids (G#####).  Each entry may come from multiple media files (e.g. photographs from different angles, gait walking videos, etc.) but should contain just one 'foreground' or 'best' person.
2. Build a probe database using the commands `python -m briar sigset-enroll --entry-type=media ...` or `python -m briar enroll --entry-type=media ...`. These probes will contain entries organized by unique media ids.  Each entry will come from a single media file where each file may contain multiple people.
3. The final step is to run search and verification commands to produce results that will be analyzed using statistical tools.  These commands are `python -m briar test-verify` or `python -m briar test-search`

## Version Requirements

This section will contain what performers will be required to implement for each phase once details are solidified.

## Quick Reference
Please check This section regularly to make sure deliverables stay up to date with the evaluation environment.  

| Parameter | Value | Notes |
| ------ | ------ | ------ |
| API Version | v1.0.0 | |
| Default gRPC Port | 127.0.0.1:50051 | |
| Evaluation Port Range | 50050 - 50150 | All deliverables should be able to run on these ports.  |
| Evaluation CPU Count | 8 | Intel or AMD |
| Evaluation Memory Limit | 32GB |  |
| GPU Count | 2 | NVIDIA A100 |
| GPU Memory | At least 8GB | Amount of memory per GPU |
| Singularity Version | ## |  |
| CUDA Version | 11.4.1 | CUDA version on the host machine |
| Enrollment Speed | 5x Realtime |  |
| Verification Speed | TBD |  |
| Search Speed | TBD |  |
| Template Size | < 1Mb |  |

## BRIAR API Versions

_This section will contain notes on how the BRIAR API has been developed and how it will be changing in the future.  Please check back regularly for updates to make sure any solution delivered stays in compliance._

2021/09/07 v1.0.0 - Initial BRIAR API released.



