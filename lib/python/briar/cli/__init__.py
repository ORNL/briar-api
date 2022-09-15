"""!
The modules contained in the CLI package each contain a function (detect, extract, enroll, etc.) which is a
command within the broader CLI toolkit along with the assorted helper functions.

The briar_cli file has each of these important functions mapped in a dictionary which accesses them based off
of user commands. The module functions then add additional command line options which can be parsed into options or
displayed as part of a help message. From there, the module functions will connect to the specified service and send
it messages and receive replies based off of the arguments passed in through the command line.
"""

    # Here are some templates for standard option formats.
    # parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True,
    #                 help="Decrease the verbosity of the program")

    # parser.add_option("-b", "--bool", action="store_true", dest="my_bool", default=False,
    #                  help="don't print status messages to stdout")

    # parser.add_option( "-c","--choice", type="choice", choices=['c1','c2','c3'], dest="my_choice", default="c1",
    #                  help="Choose an option.")

    # parser.add_option( "-f","--float", type="float", dest="my_float", default=0.0,
    #                  help="A floating point value.")

    # parser.add_option( "-i","--int", type="int", dest="my_int", default=0,
    #                  help="An integer value.")

    # parser.add_option( "-s","--str", type="str", dest="my_str", default="default",
    #                  help="A string value.")

    # parser.add_option( "--enroll", type="str", dest="enroll_database", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "--search", type="str", dest="search_database", default=None,
    #                  help="Search images for faces from a database.")

    # parser.add_option( "--name", type="str", dest="subject_name", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "--subject-id", type="str", dest="subject_id", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "--search-log", type="str", dest="search_log", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "-m","--match-log", type="str", dest="match_log", default=None,
    #                  help="A directory to store matching faces.")

    # parser.add_option( "--same-person", type="str", dest="same_person", default=None,
    #                  help="Specifies a python function that returns true if the filenames indicate a match.  Example: lambda x,y: x[:5] == y[:5]")

    # parser.add_option( "-s","--scores-csv", type="str", dest="scores_csv", default=None,
    #                  help="Save similarity scores to this file.")

