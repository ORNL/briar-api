import inspect
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
def test_warn(assertion,*kwargs):
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 2)

    try:
        m = assertion(*kwargs)
    except AssertionError as e:
        stack_i = 1
        print('warning from stack trace:')
        funcs = []
        while stack_i < 6 and True:
           func_name =  calframe[stack_i][3]
           funcs.append(func_name)
           if 'test' in func_name:
               break
           stack_i+=1
        print('Function:','->'.join(funcs))
        warnings.warn(str(e))


def finalize_db(args_string, db_name):
    from briar.cli.database.finalize import database_finalize

    checkpoint_reply = database_finalize(
        input_command="finalize " + args_string + db_name, ret=True)

def checkpoint_db(args_string, db_name):
    from briar.cli.database.checkpoint import database_checkpoint

    checkpoint_reply = database_checkpoint(input_command="database checkpoint " + args_string + db_name, ret=True)

if __name__ == '__main__':
    pass