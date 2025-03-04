#!/bin/bash

# INSTALLING THE PACKAGE
# conda install -c conda-forge go
# go get -u github.com/pseudomuto/protoc-gen-doc/cmd/protoc-gen-doc

# Had problems with the docker image reading/outputting the right path. Modified protoc command to actually work
#docker run --rm -v $(pwd)/doc:/out -v $(pwd)/proto/:/protos pseudomuto/protoc-gen-doc

#protoc  --doc_out=doc --doc_opt=html,index.html --proto_path=proto briar_error.proto

#protoc --doc_out=html,Protbuf-ObjectDoc.html:doc --proto_path=proto proto/briar/briar_grpc/*.proto

# A working docker command:
docker run --rm -v $(pwd)/doc:/out -v $(pwd)/proto/:/protos pseudomuto/protoc-gen-doc briar/briar_grpc/briar.proto briar/briar_grpc/briar_error.proto briar/briar_grpc/briar_service.proto
#podman run --rm -v $(pwd)/doc:/out -v $(pwd)/proto/:/protos pseudomuto/protoc-gen-doc briar/briar_grpc/briar.proto briar/briar_grpc/briar_error.proto briar/briar_grpc/briar_service.proto
mv doc/index.html doc/Protobuf-Object-Doc.html
