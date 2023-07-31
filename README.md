# Witchery

**A Python Package for Code Analysis and Modification**

Witchery is a powerful Python library that offers various functionalities for code analysis and modification. It
provides tools to traverse Abstract Syntax Trees (AST) of Python code and perform tasks such as finding defined
variables, removing specific variables, identifying local imports, adding function calls, and much more.

Whether you need to analyze code for missing variables, remove certain variables from your codebase, or perform code
transformations, Witchery has you covered. It is a versatile utility for developers and programmers seeking to enhance
their code analysis and modification capabilities.

With Witchery, you can easily parse Python code, identify used and defined variables, handle imports, and generate code
for missing variables, among other useful features. This package is designed to simplify code manipulation tasks and
assist in creating cleaner and more efficient Python codebases.

Features:

- Find defined variables within Python code
- Remove specific variables from code
- Identify local imports in code
- Remove imports of specific modules
- Add function calls to existing code
- Find missing variables in code
- Generate ✨ magic ✨ code to define missing variables
- and more!

[![PyPI - Version](https://img.shields.io/pypi/v/witchery.svg)](https://pypi.org/project/witchery)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/witchery.svg)](https://pypi.org/project/witchery)  
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![su6 checks](https://github.com/robinvandernoord/witchery/actions/workflows/su6.yml/badge.svg?branch=development)](https://github.com/robinvandernoord/witchery/actions)
![coverage.svg](coverage.svg)

-----

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [License](#license)

## Installation

You can install `witchery` using pip:

```bash
pip install witchery
```

## Usage

The `witchery` library provides several useful methods to work with Python code. Here are the main functions and their
purposes:

1. `find_defined_variables(code_str: str) -> set[str]`: Parses the given Python code and finds all variables that are
   defined within. It returns a set of variable names that are defined in the provided Python code.

2. `remove_specific_variables(code: str, to_remove: typing.Iterable[str] = ("db", "database")) -> str`: Removes specific
   variables from the given code. You can specify a list of variable names to be removed, and the function will return
   the code after removing the specified variables.

3. `has_local_imports(code: str) -> bool`: Checks if the given code has local imports. It returns True if local imports
   are found, and False otherwise.

4. `remove_import(code: str, module_name: typing.Optional[str]) -> str`: Removes the import of a specific module from
   the given code. You can specify the name of the module to remove, and the function will return the code after
   removing the import of the specified module.

5. `remove_local_imports(code: str) -> str`: Removes all local imports from the given code. It returns the code after
   removing all local imports.

6. `find_function_to_call(code: str, function_call_hint: str) -> typing.Optional[str]`: Finds the function to call in
   the given code based on the function call hint. It returns the name of the function to call if found, or None
   otherwise.

7. `extract_function_details(function_call: str, default_args: typing.Iterable[str] = DEFAULT_ARGS) -> tuple[str | None, list[str]]`:
   Extracts the function name and arguments from the function call string. It returns a tuple containing the function
   name and a list of arguments.

8. `add_function_call(code: str, function_call: str, args: typing.Iterable[str] = DEFAULT_ARGS) -> str`: Adds a function
   call to the given code. You can specify the function call string and the arguments for the function call.

9. `find_variables(code_str: str) -> tuple[set[str], set[str]]`: Finds all used and defined variables in the given code
   string. It returns a tuple containing sets of used and defined variables.

10. `find_missing_variables(code: str) -> set[str]`: Finds and returns all missing variables in the given code. It
    returns a set of names of missing variables.

11. `generate_magic_code(missing_vars: set[str]) -> str`: Generates code to define missing variables with a do-nothing
    object. After finding missing variables, it fills them in with an object that does nothing except return itself or
    an empty string.

## Examples

```python
import witchery

# Example 1: Find defined variables in code
code = """
x = 5
y = 10
z = x + y
"""
defined_vars = witchery.find_defined_variables(code)
print(defined_vars)
# Output: {'x', 'y', 'z'}

# Example 2: Remove specific variables from code
code = """
x = 5
y = 10
db = Database()
"""
new_code = witchery.remove_specific_variables(code, to_remove=["x", "db"])
print(new_code)
# Output: "y = 10"

# Example 3: Check if code has local imports
code = "from my_module import my_function"
has_local_imports = witchery.has_local_imports(code)
print(has_local_imports)
# Output: False

code = "from .my_module import my_function"
has_local_imports = witchery.has_local_imports(code)
print(has_local_imports)
# Output: True

# Example 4: Remove import of a specific module from code
code = """
import module_name
from module_name import something
x = module_name.function()
"""
new_code = witchery.remove_import(code, module_name="module_name")
print(new_code)
# Output: "x = module_name.function()"

# do note that this only removes the import, NOT any function calls to it!

# Example 5: Remove all local imports from code
code = """
from .local_module import something
from another_module import func

def my_function():
    return func(), something()
"""
new_code = witchery.remove_local_imports(code)
print(new_code)
# Output:
# from another_module import func
# 
# def my_function():
#     return func(), something()

# do note that this only removes the imports, NOT any function calls to it!

# Example 6: Find the function to call based on the function call hint
code = """
def my_function():
    return 42

x = my_function()
"""
function_to_call = witchery.find_function_to_call(code, "my_function()")  # can be with or without parentheses
print(function_to_call)
# Output: "my_function"

# will be None if the function does not exist in the specified code.

# Example 7: Extract function name and arguments from function call string
function_call = "my_function(x, y, 'z')"
function_name, args = witchery.extract_function_details(function_call)
print(function_name)
# Output: "my_function"
print(args)
# Output: ['x', 'y', "'z'"]

# Example 8: Add a function call to code
code = """
def add(a, b):
    return a + b

result = add(3, 5)
"""
new_code = witchery.add_function_call(code, function_call="add(x, y)")
print(new_code)
# Output: 
# def add(a, b):
#     return a + b
# add(x, y)
# result = add(3, 5)

# The call will be placed right below the function definition.

# Example 9: Find used and defined variables in code
code = """
x = 5
y = x + z
result = x * y
"""
used_vars, defined_vars = witchery.find_variables(code, with_builtins=False)
print(used_vars)
# Output: {'x', 'y', 'z'}
print(defined_vars)
# Output: {'x', 'y', 'result'}  # will be a lot longer if with_builtins = True

# Example 10: Find missing variables in code
code = """
x = 5
result = x * y
"""
missing_vars = witchery.find_missing_variables(code)
print(missing_vars)
# Output: {'y'}

# Example 11: Generate magic code to define missing variables
missing_vars = {'y', 'z'}
magic_code = witchery.generate_magic_code(missing_vars)
print(magic_code)
# Output: """
# class Empty:
#     ...
#
# empty = Empty()
# y = empty; z = empty;
# """

```

## License

`witchery` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
