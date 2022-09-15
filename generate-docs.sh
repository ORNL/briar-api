BRIAR_DIR=$(pwd)
DOC_DIR=$BRIAR_DIR/doc
DOC_BUILD_DIR=$BRIAR_DIR/doc/build
PROTO_DIR=$BRIAR_DIR/proto/briar/briar_grpc
PYTHON_DIR=$BRIAR_DIR/lib/python/briar
PDF_DIR=$DOC_DIR/pdf
STUB_DIR=$DOC_DIR/stubs

# colorize text to make sections more visible when scrolling through walls of doxygen/latex spam
GREEN='\033[0;32m'
NC='\033[0m' # No Color

mkdir -p $PDF_DIR
mkddif -p $STUB_DIR

# TODO Latex is very loud. Need to figure out a way to make it Shut Up when running in the makefiles.
########################
# Protobuf Documentation
########################
echo -e "${GREEN}[Protobuf Documents]${NC}"
echo -e "${GREEN}Generating Protobuf HTML...${NC}"
cd $BRIAR_DIR
protoc --doc_out=html,Protbuf-Object-Doc.html:doc --proto_path=proto proto/briar/briar_grpc/*.proto
mkdir -p $DOC_BUILD_DIR/proto
echo -e "${GREEN}Generating Doxygen...${NC}"
cd $PROTO_DIR
doxygen doxyfile-protobuf
echo -e "${GREEN}Generating PDF${NC}"
cd $DOC_BUILD_DIR/proto/latex
make pdf
cp refman.pdf $PDF_DIR/Protobuf-Documentation.pdf

########################
# Stub Documentation
########################
echo -e "${GREEN}[gRPC Stubs]${NC}"
cd $PROTO_DIR
mkdir -p $STUB_DIR

# Generate the C++ Stub Documentation
cd $PROTO_DIR
echo -e "${GREEN}Generating C++ Stub Doxygen...${NC}"
mkdir -p $DOC_BUILD_DIR/stubs/cpp
doxygen doxyfile-stubs-cpp
echo -e "${GREEN}Generating C++ Stub PDF...${NC}"
cd $DOC_BUILD_DIR/stubs/cpp/latex
make pdf
cp refman.pdf $STUB_DIR/CPP-Stub-Documentation.pdf

# Generate the C# Stub Documentation
cd $PROTO_DIR
echo -e "${GREEN}Generating C# Stub Doxygen...${NC}"
mkdir -p $DOC_BUILD_DIR/stubs/csharp
doxygen doxyfile-stubs-csharp
echo -e "${GREEN}Generating C# Stub PDF...${NC}"
cd $DOC_BUILD_DIR/stubs/csharp/latex
make pdf
cp refman.pdf $STUB_DIR/CSharp-Stub-Documentation.pdf

# Generate the Javascript Stub Documentation
cd $PROTO_DIR
echo -e "${GREEN}Generating Javascript Stub Doxygen...${NC}"
mkdir -p $DOC_BUILD_DIR/stubs/js
doxygen doxyfile-stubs-js
echo -e "${GREEN}Generating Javascript Stub PDF...${NC}"
cd $DOC_BUILD_DIR/stubs/js/latex
make pdf
cp refman.pdf $STUB_DIR/Javascript-Stub-Documentation.pdf

# Generate the Objective C Stub Documentation
cd $PROTO_DIR
echo -e "${GREEN}Generating C Stub Doxygen...${NC}"
mkdir -p $DOC_BUILD_DIR/stubs/objc
doxygen doxyfile-stubs-objc
echo -e "${GREEN}Generating C Stub PDF...${NC}"
cd $DOC_BUILD_DIR/stubs/objc/latex
make pdf
cp refman.pdf $STUB_DIR/ObjC-Stub-Documentation.pdf

# Generate the PHP Stub Documentation
cd $PROTO_DIR
echo -e "${GREEN}Generating PHP Stub Doxygen...${NC}"
mkdir -p $DOC_BUILD_DIR/stubs/php
doxygen doxyfile-stubs-php
echo -e "${GREEN}Generating PHP Stub PDF...${NC}"
cd $DOC_BUILD_DIR/stubs/php/latex
make pdf
cp refman.pdf $STUB_DIR/PHP-Stub-Documentation.pdf

# Generate the Python Stub Documentation
cd $PROTO_DIR
echo -e "${GREEN}Generating Python Stub Doxygen...${NC}"
mkdir -p $DOC_BUILD_DIR/stubs/python
doxygen doxyfile-stubs-python
echo -e "${GREEN}Generating Python Stub PDF...${NC}"
cd $DOC_BUILD_DIR/stubs/python/latex
make pdf
cp refman.pdf $STUB_DIR/Python-Stub-Documentation.pdf

# Generate the Ruby Stub Documentation
cd $PROTO_DIR
echo -e "${GREEN}Generating Ruby Stub Doxygen...${NC}"
mkdir -p $DOC_BUILD_DIR/stubs/ruby
doxygen doxyfile-stubs-ruby
echo -e "${GREEN}Generating Ruby Stub PDF...${NC}"
cd $DOC_BUILD_DIR/stubs/ruby/latex
make pdf
cp refman.pdf $STUB_DIR/Ruby-Stub-Documentation.pdf


#########################################
# Python Client and Service Documentation
#########################################
echo -e "${GREEN}[Python Documents]${NC}"
cd $PYTHON_DIR
mkdir $PDF_DIR

# Genearate documenation for the python client
echo -e "${GN}Generating Python Client Doxygen${NC}"
mkdir -p $DOC_BUILD_DIR/python_client
doxygen doxyfile-cli
echo -e "${GREEN}Generating Python Client PDF${NC}"
cd $DOC_BUILD_DIR/python_client/latex
make pdf
cp refman.pdf $PDF_DIR/Python-Client-Documentation.pdf

# Generate documentation for the example python service
echo -e "${GREEN}Generating Example Python Service Documents${NC}"
cd $DOC_DIR
mkdir -p $DOC_BUILD_DIR/example_python_service
doxygen doxyfile-python-service
echo -e "${GREEN}Generating Example Python Service PDF${NC}"
cd $DOC_BUILD_DIR/example_python_service/latex
make pdf
cp refman.pdf $PDF_DIR/Example-Python-Service-Documentation.pdf

#########################################
# BRIAR Main Documentation
#########################################
echo -e "${GREEN}[Main Readme]${NC}"
cd $BRIAR_DIR

# Generate the main repo readme
echo -e "${GREEN}Generating Repo Doxygen...${NC}"
doxygen doxyfile-main
echo -e "${GREEN}Generating Repo PDF...${NC}"
cd $DOC_BUILD_DIR/main/latex
make pdf
cp refman.pdf $PDF_DIR/Readme-And-How-To-Documentation.pdf

cd $BRIAR_DIR