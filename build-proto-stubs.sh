#!/bin/bash

# Python
echo "Building Python Stubs"
python -m grpc_tools.protoc --proto_path=proto --python_out=lib/python --grpc_python_out=lib/python briar/briar_grpc/briar.proto briar/briar_grpc/briar_error.proto briar/briar_grpc/briar_service.proto

# C++
echo "Building C++ Stubs"
export CPP_DIR=$BRIAR_DIR/lib/cpp/briar/briar_grpc
mkdir -p $CPP_DIR
protoc -I proto --proto_path=proto --cpp_out=lib/cpp proto/briar/briar_grpc/briar.proto proto/briar/briar_grpc/briar_error.proto proto/briar/briar_grpc/briar_service.proto

# C Sharp
#echo "Building C# Stubs"
#export CSHARP_DIR=$BRIAR_DIR/lib/csharp/briar/briar_grpc
#mkdir -p $CSHARP_DIR
#protoc -I proto --proto_path=proto --csharp_out=lib/csharp --grpc_out=lib/csharp/briar/briar_grpc proto/briar/briar_grpc/briar.proto proto/briar/briar_grpc/briar_error.proto proto/briar/briar_grpc/briar_service.proto
#
## build ruby
#echo "Building Ruby Stubs"
#export RUBY_DIR=$BRIAR_DIR/lib/ruby/briar/briar_grpc
#mkdir -p $RUBY_DIR
#protoc -I proto --proto_path=proto --ruby_out=lib/ruby --grpc_out=lib/ruby proto/briar/briar_grpc/briar.proto proto/briar/briar_grpc/briar_error.proto proto/briar/briar_grpc/briar_service.proto
#
## build php
#echo "Building PHP Stubs"
#export PHP_DIR=$BRIAR_DIR/lib/php/briar/briar_grpc
#mkdir -p $PHP_DIR
#protoc -I proto --proto_path=proto --php_out=lib/php --grpc_out=lib/php proto/briar/briar_grpc/briar.proto proto/briar/briar_grpc/briar_error.proto proto/briar/briar_grpc/briar_service.proto
#
## build objc
#echo "Building Objective C Stubs"
#export OBJC_DIR=$BRIAR_DIR/lib/objc/briar/briar_grpc
#mkdir -p $OBJC_DIR
#protoc -I proto --proto_path=proto --objc_out=lib/objc --grpc_out=lib/objc --plugin=protoc-gen-grpc=`which grpc_objective_c_plugin` proto/briar/briar_grpc/briar.proto proto/briar/briar_grpc/briar_error.proto proto/briar/briar_grpc/briar_service.proto
#
## build node
#echo "Building JS Stubs"
#export JS_DIR=$BRIAR_DIR/lib/js/briar/briar_grpc
#mkdir -p $JS_DIR
#protoc -I proto --proto_path=proto --js_out=lib/js --grpc_out=lib/js/briar/briar_grpc --plugin=protoc-gen-grpc=`which grpc_node_plugin` proto/briar/briar_grpc/briar.proto proto/briar/briar_grpc/briar_error.proto proto/briar/briar_grpc/briar_service.proto

echo Proto build complete.
