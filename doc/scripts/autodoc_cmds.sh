START_DIR=$(pwd)
BRIAR_DIR=$(readlink -f ../../)
DOC_DIR=$BRIAR_DIR/doc
PDF_DIR=$DOC_DIR/pdf
BUILD_DIR=$BRIAR_DIR/doc/build/cmd_autodoc/
TMP_DIR=$BRIAR_DIR/doc/build/cmd_autodoc/tmp
CMDS_LIST_FILE=$TMP_DIR/all_cmds.txt
CMD_FILE_OUT_DIR=$BUILD_DIR/cmds
DOXYDIR=$BUILD_DIR/doxygen
OUT_FILE=$PDF_DIR/BRIAR-Commands.pdf

GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building BRIAR CLI cmd documentation${NC}"
mkdir -p $TMP_DIR
mkdir -p $CMD_FILE_OUT_DIR
mkdir -p $DOXYDIR

# get a current list of commands from the cli tool
echo -e "${GREEN}Getting BRIAR CLI cmds${NC}"
python -c "from briar.briar_cli import COMMANDS
import string as s
[print(cmd) for cmd in COMMANDS if cmd[0] in s.ascii_letters]" > $CMDS_LIST_FILE

# remove noise messages from the cmd file
if grep -q "Warning: could not import fast_util." "$CMDS_LIST_FILE"; then
  sed -i "1d" $CMDS_LIST_FILE
fi

# save the commands into a markdown bullet point list with links to the pages
BULLET_LIST=""

# iterate each command in the cmds file and dump its help message into a folder
while read CMD; do
  # dump the command help text into a file
  echo  -e "-Getting $CMD...${NC}"
  TMP_CMD_FILE=$TMP_DIR/$CMD.md
  DONE_CMD_FILE=$CMD_FILE_OUT_DIR/$CMD.md
  python -m briar $CMD --help > $TMP_CMD_FILE

  # markdown the cmd.md file into a doxygen compatible markdown file
  python ./markdownify_cmd_text.py $CMD $TMP_CMD_FILE $DONE_CMD_FILE

  # Create the links to put in the top-level readme
  PAGE_REF=$(grep "\\page" $DONE_CMD_FILE | cut -d ' ' -f2)
  LINE="- [${CMD}](@ref ${PAGE_REF})" # Create a bullet with a markup-text link to the page
  BULLET_LIST=${BULLET_LIST}${LINE}$'\n'

done < $CMDS_LIST_FILE

# Create a new readme from the template and put the new links into it. Build the doxyfile
echo -e "${GREEN}Building Doxygen files${NC}"
MAINFILE=$BUILD_DIR/cmd-readme.md
cp template-cmds-readme.md $MAINFILE
echo "" >> $MAINFILE
echo "$BULLET_LIST" >> $MAINFILE
doxygen doxyfile-cmd

# Create the pdf from Latex
echo -e "${GREEN}Generating Command Tools PDF...${NC}"
cd $DOXYDIR/latex
make pdf
cp refman.pdf $OUT_FILE
cd $START_DIR
