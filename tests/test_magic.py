import textwrap

from src.witchery import (
    add_function_call,
    extract_function_details,
    find_defined_variables,
    find_function_to_call,
    find_missing_variables,
    generate_magic_code,
    has_local_imports,
    remove_import,
    remove_local_imports,
    remove_specific_variables,
)

CODE_STRING = """
from math import floor # ast.ImportFrom
import datetime # ast.Import
from pydal import * # ast.ImportFrom with *
a = 1
b = 2
print(a, b + c)
d = e + b
f = d
del f  # ast.Del
print(f)
xyz
floor(d)
ceil(d)
ceil(e)

datetime.utcnow()

db = DAL()

db.define_table('...')

for table in []:
   print(table)

if toble := True:
   print(toble)
   
# subscript:
driver_args: dict[str, int] = {}

more_args["one"] = 2

# tuple:
tuple_one, tuple_two = 1, 2
"""


def test_find_defined():
    # defined: `variable = value` in code (so not imported or in loop etc.)
    all_variables = find_defined_variables(CODE_STRING)

    assert all_variables == {"a", "b", "d", "f", "db", "driver_args", "tuple_one", "tuple_two", "more_args"}


def test_find_missing():
    # Example usage:
    missing_variables = find_missing_variables(CODE_STRING)
    assert missing_variables == {"c", "xyz", "ceil", "e", "f"}, missing_variables


def test_find_local_imports():
    assert has_local_imports("from .math import floor")
    assert not has_local_imports("from math import floor")


def test_remove_import():
    code = textwrap.dedent(
        """
    import fake_module
    import typing
    """
    )

    new_code = remove_import(code, "fake_module")

    assert "fake_module" not in new_code
    assert "import typing" in new_code


def test_remove_local_imports():
    code = textwrap.dedent(
        """
    from .local import method1, method2
    from .other import method3
    from typing import *
    from math import floor
    """
    )
    new_code = remove_local_imports(code)

    assert "local" not in new_code
    assert "method" not in new_code
    assert "typing" in new_code
    assert "floor" in new_code


def test_find_function_to_call():
    code = textwrap.dedent(
        """
    def main(arg1, arg2):
        ...
    
    def other(arg: int):
        ...
    """
    )

    assert find_function_to_call(code, "main") == "main"
    assert find_function_to_call(code, "main()") == "main"
    assert find_function_to_call(code, "main(1, 2)") == "main"
    assert find_function_to_call(code, "other") == "other"
    assert find_function_to_call(code, "other(1, 2)") == "other"
    assert find_function_to_call(code, "doesnt_exist") is None
    assert find_function_to_call(code, "doesnt_exist()") is None


def test_extract_function_details():
    assert extract_function_details("my_method", default_args=[]) == ("my_method", [])
    assert extract_function_details("my_method()", default_args=[]) == ("my_method", [])

    assert extract_function_details("my_method", default_args=["arg1"]) == ("my_method", ["arg1"])
    assert extract_function_details("my_method()", default_args=["arg1"]) == ("my_method", ["arg1"])

    assert extract_function_details("my_method(first, 'second')", default_args=[]) == (
        "my_method",
        ["first", "'second'"],
    )
    assert extract_function_details("my_method(first, 'second')", default_args=["arg1"]) == (
        "my_method",
        ["first", "'second'"],
    )

    assert extract_function_details("syntax_error(") == (None, [])


def test_add_function_call():
    code = textwrap.dedent(
        """
    def main(arg: str):
        print('hi', arg)

    print('the end')
    """
    )

    target = textwrap.dedent(
        """
    def main(arg: str):
        print('hi', arg)
    main('World')
    print('the end')
    """
    )

    assert add_function_call(code, "main", args=["'World'"]).strip() == target.strip()

    # duplicate functions:
    code = textwrap.dedent(
        """
    def main(arg: str):
        print('hi', arg)

    def main(arg: str):
        print('another one')

    print('the end')
    """
    )

    target = textwrap.dedent(
        """
    def main(arg: str):
        print('hi', arg)
    main('World')

    def main(arg: str):
        print('another one')
    main('World')
    print('the end')
    """
    )

    assert add_function_call(code, "main", args=["'World'"], multiple=True).strip() == target.strip()


def test_fix_missing():
    code = generate_magic_code({"bla"})

    assert "empty = Empty()" in code
    assert "bla = empty" in code


def test_remove_specific_variables():
    code = textwrap.dedent(
        """
    db = DAL()
    def database():
        return True
    
    my_database = 'exists'
    print('hi')
    """
    )
    new_code = remove_specific_variables(code)
    assert "print('hi')" in new_code
    assert "db" not in new_code
    assert "DAL" not in new_code
    assert "def database" not in new_code
    assert "my_database" in new_code
