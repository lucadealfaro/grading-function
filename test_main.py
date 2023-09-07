import os

from main import *

code1 = """
import math
from collections import defaultdict
import numpy as np

def f(n):
    if n < 2:
        return n
    else:
        return math.sqrt(2)

def g(n):
    print(f(n))
    with open("salsa.txt") as f:
        print(f.read())

print(f(4))
"""

code2 = """
class Chicken(object):

    def __init__(self, x):
        self.x = x

    def get(self):
        return self.x

c = Chicken(3)
print(c.get())
print(type(Chicken))
"""

code3 = """
l = list([2, 3, 4])
d = dict(a=3)
print(d)
for i, el in enumerate(l):
    print (el, ":", i)
al = [el + 1 for el in l]
dd = dict(enumerate(al))
print(dd)
"""

code4 = """
with open("/Users/luca/.cshrc") as f:
    print(f.read())
"""

code5 = """
import os
"""

code6 = """
import random
print(random.random())
"""

code7 = """
import random
from collections import defaultdict
print(random.random())
"""

code9 = """
import pandas
"""

code_hidden = """
def f(x):
    return x + 1

assert f(3) == 4

### BEGIN HIDDEN TESTS
assert f(4) == 6
### END HIDDEN TESTS
"""


def no_test_exec():
    for code in [code1, code2, code3, code6, code7]:
        collector = OutputCollector()
        my_globals = get_clean_globals()
        my_globals["__builtins__"]["print"] = collector
        clean_code = ast.unparse(cleaner.visit(ast.parse(code)))
        cr = compile(clean_code, '<string>', 'exec')
        exec(cr, my_globals)
        print("---------")
        print(collector.result())


def no_test_defaultdict():
    for code in [code7]:
        collector = OutputCollector()
        my_globals = get_clean_globals()
        my_globals["__builtins__"]["print"] = collector
        clean_code = ast.unparse(cleaner.visit(ast.parse(code)))
        cr = compile(clean_code, '<string>', 'exec')
        exec(cr, my_globals)
        print("---------")
        print(collector.result())


def no_test_fail():
    for code in [code4, code5]:
        try:
            collector = OutputCollector()
            my_globals = get_clean_globals()
            my_globals["__builtins__"]["print"] = collector
            clean_code = ast.unparse(cleaner.visit(ast.parse(code)))
            cr = compile(clean_code, '<string>', 'exec')
            exec(cr, my_globals)
            print(collector.result())
            print("---------")
            result = False
        except Exception as e:
            result = True
        assert result, "Let something incorrect happen."


def no_test_hidden():
    collector = OutputCollector()
    my_globals = get_clean_globals()
    my_globals["__builtins__"]["print"] = collector
    clean_code = code_hidden
    cr = compile(clean_code, '<string>', 'exec')
    try:
        exec(cr, my_globals)
    except Exception as e:
        print("Exception:", traceback.format_exception_only(e)[0])
    print(collector.result())


def no_test_notebook1():
    with open("test_files/notebook1.json") as f:
        notebook_json = f.read()
    nb = nbformat.reads(notebook_json, as_version=4)
    points, had_errors = run_notebook(
        nb, max_num_timeouts=1)
    print("Points:", points, "had errors:", had_errors)
    print(nbformat.writes(nb, 4))

def test_notebook2():
    with open("test_files/notebook2.json") as f:
        notebook_json = f.read()
    nb = nbformat.reads(notebook_json, as_version=4)
    points, had_errors = run_notebook(
        nb, max_num_timeouts=1)
    print("Points:", points, "had errors:", had_errors)
    with open("test_files/notebook2_out.ipynb", "w") as f:
        f.write(nbformat.writes(nb, 4))
