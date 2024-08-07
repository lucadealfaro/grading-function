# This file contains the functions used to run a notebook.

import ast
import builtins
import importlib
import json
import nbformat.v4, nbformat
import requests
import threading
import traceback
import warnings

import functions_framework

@functions_framework.http
def grader(request):
    # Reads the parameters.
    request_json = request.get_json(silent=True)
    notebook_json = request_json.get("notebook_json")
    timeout = request_json.get("timeout", 60)
    max_num_timeouts = request_json.get("max_num_timeouts", 1)
    nonce = request_json.get("nonce")
    callback_url = request_json.get("callback_url")
    # Processes the request.
    nb = nbformat.reads(notebook_json, as_version=4)
    points, had_errors = run_notebook(
        nb, timeout=timeout, max_num_timeouts=max_num_timeouts)
    payload = dict(
        nonce=nonce,
        graded_json=nbformat.writes(nb, 4),
        points=points,
        had_errors=had_errors,
    )
    print("Processed request, nonce: {}, callback_url: {} points: {}".format(nonce, callback_url, points))
    if callback_url:
        r = requests.post(callback_url, json=payload)
        r.raise_for_status()
        return "ok"
    else:
        return json.dumps(payload, indent=2)


warnings.simplefilter(
    "ignore")  # Silences nasty warnings from restricted python.


class IllegalImport(Exception):
    pass


SAFE_BUILTINS = [
    'ArithmeticError',
    'AssertionError',
    'AttributeError',
    'BaseException',
    'BaseExceptionGroup',
    'BlockingIOError',
    'BrokenPipeError',
    'BufferError',
    'BytesWarning',
    'ChildProcessError',
    'ConnectionAbortedError',
    'ConnectionError',
    'ConnectionRefusedError',
    'ConnectionResetError',
    'DeprecationWarning',
    'EOFError',
    'Ellipsis',
    'EncodingWarning',
    'EnvironmentError',
    'Exception',
    'ExceptionGroup',
    'False',
    'FileExistsError',
    'FileNotFoundError',
    'FloatingPointError',
    'FutureWarning',
    'GeneratorExit',
    'IOError',
    'ImportError',
    'ImportWarning',
    'IndentationError',
    'IndexError',
    'InterruptedError',
    'IsADirectoryError',
    'KeyError',
    'KeyboardInterrupt',
    'LookupError',
    'MemoryError',
    'ModuleNotFoundError',
    'NameError',
    'None',
    'NotADirectoryError',
    'NotImplemented',
    'NotImplementedError',
    'OSError',
    'OverflowError',
    'PendingDeprecationWarning',
    'PermissionError',
    'ProcessLookupError',
    'RecursionError',
    'ReferenceError',
    'ResourceWarning',
    'RuntimeError',
    'RuntimeWarning',
    'StopAsyncIteration',
    'StopIteration',
    'SyntaxError',
    'SyntaxWarning',
    'SystemError',
    'SystemExit',
    'TabError',
    'TimeoutError',
    'True',
    'TypeError',
    'UnboundLocalError',
    'UnicodeDecodeError',
    'UnicodeEncodeError',
    'UnicodeError',
    'UnicodeTranslateError',
    'UnicodeWarning',
    'UserWarning',
    'ValueError',
    'Warning',
    'ZeroDivisionError',
    '__build_class__',
    '__debug__',
    '__doc__',
    # '__import__',
    # '__loader__',
    '__name__',
    # '__package__',
    '__spec__',
    'abs',
    'aiter',
    'all',
    'anext',
    'any',
    'ascii',
    'bin',
    'bool',
    # 'breakpoint',
    'bytearray',
    'bytes',
    'callable',
    'chr',
    'classmethod',
    # 'compile',
    'complex',
    'copyright',
    'credits',
    'delattr',
    'dict',
    # 'dir',
    'divmod',
    'enumerate',
    # 'eval',
    # 'exec',
    # 'execfile',
    'filter',
    'float',
    'format',
    'frozenset',
    'getattr',
    # 'globals',
    'hasattr',
    'hash',
    'help',
    'hex',
    'id',
    'input',
    'int',
    'isinstance',
    'issubclass',
    'iter',
    'len',
    'license',
    'list',
    # 'locals',
    'map',
    'max',
    'memoryview',
    'min',
    'next',
    'object',
    'oct',
    # 'open',
    'ord',
    'pow',
    # 'print', # replaced
    'property',
    'range',
    'repr',
    'reversed',
    'round',
    'set',
    'setattr',
    'slice',
    'sorted',
    'staticmethod',
    'str',
    'sum',
    'super',
    'tuple',
    'type',
    'vars',
    'zip'
]

WHITELISTED_MODULES = [
    # special
    "pandas", "numpy", "scipy", "math", "random", "matplotlib", "pytorch",
    "requests", "PIL", "sklearn", "networkx", "openai", "langchain",
    "dotenv",
    # text and binary
    "string", "re", "struct",
    # data types
    "datetime", "zoneinfo", "calendar", "collections",
    "heapq", "bisect", "array", "types", "copy", "enum", "graphlib",
    # numbers etc.
    "numbers", "math", "cmath", "decimal", "fractions", "random", "statistics",
    # functions etc.
    "itertools", "functools", "operator",
    # Crypto etc
    "hashlib", "hmac", "secrets",
    # Os and the like.
    "time", "io",
    # Data handling.
    "json", "base64", "binascii", "zipfile",
]


class CleanCode(ast.NodeTransformer):

    def visit_Import(self, node):
        for n in node.names:
            module_name = n.name.split(".")[0]
            if module_name not in WHITELISTED_MODULES:
                raise IllegalImport(
                    "You cannot import module {}".format(module_name))
        return node

    def visit_ImportFrom(self, node):
        module_name = node.module.split(".")[0]
        if module_name not in WHITELISTED_MODULES:
            raise IllegalImport(
                "You cannot import module {}".format(module_name))
        return node


cleaner = CleanCode()


def failimporter(*args, **kwargs):
    raise IllegalImport("You cannot import modules in solution cells")


def safeimporter(name, globals=None, locals=None, fromlist=(), level=0):
    module_name = name.split(".")[0]
    if module_name not in WHITELISTED_MODULES:
        raise IllegalImport("You cannot import module {}".format(module_name))
    res = importlib.__import__(name, globals=globals, locals=locals,
                               fromlist=fromlist, level=level)
    return res


def get_clean_globals():
    my_builtins = {k: getattr(builtins, k) for k in SAFE_BUILTINS}
    my_builtins["__import__"] = safeimporter
    my_globals = dict(__builtins__=my_builtins)
    return my_globals


class OutputCollector(object):

    def __init__(self, _getattr_=None):
        self.txt = []
        self.lock = threading.Lock()

    def write(self, text):
        with self.lock:
            self.txt.append(text)

    def result(self):
        with self.lock:
            return '\n'.join(self.txt)

    def clear(self):
        with self.lock:
            self.txt = []

    def __call__(self, *args):
        with self.lock:
            self.txt.append(" ".join([str(a) for a in args]))


class RunCellWithTimeout(object):
    def __init__(self, function, collector, args):
        self.function = function
        self.collector = collector
        self.args = args
        self.answer = "timeout"

    def worker(self):
        self.answer = self.function(*self.args)
        # print("Cell answered:", self.answer)

    def run(self, timeout=None):
        thread = threading.Thread(target=self.worker)
        thread.start()
        thread.join(timeout=timeout)
        return self.answer


def run_cell(c, my_globals, collector):
    """
    Runs a notebook cell.  This function is called in a thread, to implement
    timeouts.
    Args:
        c: cell to be run.
        my_globals: global environment (a dictionary) in which the cell is to be run.
    Returns:
        True if all went well, False if an exception occurred.
        In any case, the cell output is updated.
    """
    c.outputs = []
    try:
        collector.clear()
        clean_code = ast.unparse(cleaner.visit(ast.parse(c.source)))
        cr = compile(clean_code, '<string>', 'exec')
        exec(cr, my_globals)
        add_output(c, collector.result())
        # print("Returning True")
        return True
    except IllegalImport as e:
        add_output(c, collector.result())
        add_output(c, "Import Error: {}".format(str(e)))
        # print("Returning False")
        return False
    except Exception as e:
        err_list = traceback.format_exception(e, limit=-1)
        add_output(c, collector.result())
        add_output(c, "".join(err_list))
        # print("Returning False")
        return False


def add_output(c, text):
    # print("Output:", text) # DEBUG
    c.outputs.append(nbformat.v4.new_output(
        "execute_result",
        {"text/plain": text}))


def add_feedback(c, text):
    c.outputs.insert(0, nbformat.v4.new_output(
        "execute_result", {"text/html": "<b>{}</b>".format(text)}
    ))

def is_solution(c):
    return (hasattr(c, "metadata")
            and hasattr(c.metadata, "notebookgrader")
            and hasattr(c.metadata.notebookgrader, "is_solution")
            and c.metadata.notebookgrader.is_solution)

def is_tests(c):
    return (hasattr(c, "metadata")
            and hasattr(c.metadata, "notebookgrader")
            and hasattr(c.metadata.notebookgrader, "is_tests")
            and c.metadata.notebookgrader.is_tests)

def run_notebook(nb, timeout=60, max_num_timeouts=1):
    """Runs a notebook, returning a notebook with output cells completed.
    Args:
        nb: notebook to be run.
        timeout: cell timeout to be used.
        max_num_timeouts: maximum number of cells that can timeout.
            This can be used to limit how many threads are created and
            left running.
    Returns:
        The total number of points.
        The notebook is adorned with the results of the execution.
    """
    collector = OutputCollector()
    my_globals = get_clean_globals()
    my_globals["__builtins__"]["print"] = collector
    execution_count = 0
    points_earned = 0
    num_timeouts = 0
    had_errors = False
    # We reset all points earned.
    for c in nb.cells:
        if c.cell_type == "code" and is_tests(c):
            c.metadata.notebookgrader.points_earned = 0
    for c in nb.cells:
        if c.cell_type == "code":
            # Prepares the globals, according to whether imports are possible.
            importer = failimporter if is_solution(c) else safeimporter
            my_globals["__builtins__"]["__import__"] = importer
            # Runs the cell.
            runner = RunCellWithTimeout(run_cell, collector,
                                        (c, my_globals, collector))
            res = runner.run(timeout=timeout)
            # print("----> Result:", res) # DEBUG
            execution_count += 1
            # c.execution_count = execution_count
            # If the cell timed out, adds an explanation of it to the outputs.
            if res == "timeout":
                explanation = "Timeout Error: The cell timed out after {} seconds".format(
                    timeout)
                add_feedback(c, explanation)
                num_timeouts += 1
                had_errors = True
            if is_tests(c):
                # Gives points for successfully completed test cells.
                points = c.metadata.notebookgrader.test_points
                # print("Cell worth", points, "points") # DEBUG
                if res is True:
                    c.metadata.notebookgrader.points_earned = points
                    points_earned += points
                    add_feedback(c,
                                 "Tests passed, you earned {}/{} points".format(
                                     points, points))
                else:
                    add_feedback(c,
                                 "Tests failed, you earned {}/{} points".format(
                                     0, points))
                    had_errors = True
            execution_count += 1
            c.execution_count = execution_count
            if num_timeouts >= max_num_timeouts:
                break
    return points_earned, had_errors

