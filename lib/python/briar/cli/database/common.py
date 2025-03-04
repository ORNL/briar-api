def db_no_exist(name):
    """
The db_no_exist function is called when the user attempts to access a database that does not exist.
It prints an error message and returns None.

:param name: Print the name of the database that doesn't exist
:return: A string
:doc-author: Joel Brogan
"""
    print('No database exists named \"', name, '\"')