"""!
Takes a file resulting from running "python -m briar [cmd_name] --help > cmd_file.txt" and annotes it with
doxygen compatible markdown text.
"""

#import string
import sys
import re


def get_leading_whitespace(s):
    """!
    Gets how many leading whitespace digits exist in string
    @param s: string to check
    @return: integer how many digits are whitespace
    """
    for i, sub_s in enumerate(s):
        if not sub_s.isspace():
            return i
    return i

def main(cmd_name, in_cmd_file, out_cmd_file):
    file_lines = ["\page page_{} {}\n".format(cmd_name.lower(), "BRIAR CLI cmd: " + cmd_name[0].lower() + cmd_name[1:]),
                  "\section s_{} {}\n".format(cmd_name.lower(), cmd_name[0].upper() + cmd_name[1:])]
    with open(in_cmd_file, 'r') as in_f:
        for lnum, line in enumerate(in_f.readlines()):
            # skip noise messages - don't include them
            if "Warning: could not import fast_util" in line:
                continue

            stripped_line = line.lstrip()

            # Make 'options' a section head
            if line.strip() == "Options:":
                modified_line = "\\section s_{}_options Options\n".format(cmd_name)

            # make each command a bullet point
            elif stripped_line and stripped_line[0] == "-":
                # Assuming that each line only has one occurence of a double hyphen
                colon_loc = re.search(r"--[\S]*", line).end()
                new_line = line[:colon_loc] + ' :' + line[colon_loc:]
                modified_line = new_line.replace('-', '+ -', 1)

            # make 1x indented sections subsections
            elif get_leading_whitespace(line) == 2 and line.strip()[0] not in ['-', '+']:
                line_text = line.strip()
                modified_line = "\\subsection ss_{}_{} {}\n".format(cmd_name,
                                                                    line_text.lower().replace(' ', '_').rstrip(':'),
                                                                    line_text)

            # Nothing to change
            else:
                modified_line = line

            file_lines.append(modified_line)

    # overwrite the input file
    with open(out_cmd_file, 'w') as out_file:
        out_file.write(''.join(file_lines))

if __name__ == "__main__":
    # arguments are [CMD_NAME] [Path to cmd --help output]
    try:
        cmd_name = sys.argv[1]
        cmd_file = sys.argv[2]
        out_cmd_file = sys.argv[3]
        if len(sys.argv) != 4:
            raise AttributeError
    except Exception as e:
        print("Usage: \"python markdownify_cmd_text.py [cmd_name] [path to cmd --help file] [path to output]\"")
    main(cmd_name, cmd_file, out_cmd_file)



