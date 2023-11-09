"""
This library has methods to guess which variables are unknown and to potentially (monkey-patch) fix this.
"""

# SPDX-FileCopyrightText: 2023-present Robin van der Noord <robinvandernoord@gmail.com>
#
# SPDX-License-Identifier: MIT


import ast
import builtins
import contextlib
import importlib
import textwrap
import typing
import warnings
from _ast import NamedExpr

BUILTINS = set(builtins.__dict__.keys())


def traverse_ast(node: ast.AST, variable_collector: typing.Callable[[ast.AST], None]) -> None:
    """
    Recursively traverses the given AST node and applies the variable collector function on each node.

    Args:
        node (ast.AST): The AST node to traverse.
        variable_collector (Callable): The function to apply on each node.
    """
    variable_collector(node)
    for child in ast.iter_child_nodes(node):
        traverse_ast(child, variable_collector)


def find_defined_variables(code_str: str) -> set[str]:
    """
    Parses the given Python code and finds all variables that are defined within.

    A defined variable refers to any variable that is assigned a value in the code through direct assignment
    (e.g. `x = 5`). Other assignments such as through for-loops are ignored.
    Please use `find_variables` if more variable info is needed.

    This function does not account for scope - it will find variables defined anywhere in the provided code string.

    Args:
        code_str (str): A string of Python code.

    Returns:
        set[str]: A set of variable names that are defined within the provided Python code.
    """
    tree: ast.Module = ast.parse(code_str)

    variables: set[str] = set()

    def collect_definitions(node: ast.AST) -> None:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            # only look for variable definitions here!
            return

        # define function that can be recursed:
        def handle_elts(elts: typing.Iterable[ast.expr]) -> None:
            for node in elts:
                # with contextlib.suppress(Exception):
                try:
                    if isinstance(node, ast.Subscript):
                        node = node.value

                    if isinstance(node, ast.Tuple):
                        # recurse
                        handle_elts(node.elts)
                        continue

                    variables.add(getattr(node, "id"))

                except Exception as e:  # pragma: no cover
                    warnings.warn("Something went wrong trying to find variables.", source=e)
                    # raise

        handle_elts(node.targets if hasattr(node, "targets") else [node.target])

    traverse_ast(tree, collect_definitions)
    return variables


def remove_specific_variables(code: str, to_remove: typing.Iterable[str] = ("db", "database")) -> str:
    """
    Removes specific variables from the given code.

    Args:
        code (str): The code from which to remove variables.
        to_remove (Iterable): An iterable of variable names to be removed.

    Returns:
        str: The code after removing the specified variables.
    """
    # Parse the code into an Abstract Syntax Tree (AST)
    tree = ast.parse(code)

    # Function to check if a variable name is 'db' or 'database'
    def should_remove(var_name: str) -> bool:
        return var_name in to_remove

    # Function to recursively traverse the AST and remove lines with 'db' or 'database' definitions
    def remove_desired_variable_refs(node: ast.AST) -> typing.Optional[ast.AST]:
        if isinstance(node, ast.Assign):
            # Check if any of the assignment targets contain 'db' or 'database'
            if any(isinstance(target, ast.Name) and should_remove(target.id) for target in node.targets):
                return None

        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and should_remove(node.name):
            return None

        # doesn't work well without list() !!!
        for child_node in list(ast.iter_child_nodes(node)):
            new_child_node = remove_desired_variable_refs(child_node)
            if new_child_node is None and hasattr(node, "body"):
                node.body.remove(child_node)

        return node

    # Traverse the AST to remove 'db' and 'database' definitions
    new_tree = remove_desired_variable_refs(tree)

    if not new_tree:  # pragma: no cover
        return ""

    # Generate the modified code from the new AST
    return ast.unparse(new_tree)


def has_local_imports(code: str) -> bool:
    """
    Checks if the given code has local imports.

    Args:
        code (str): The code to check for local imports.

    Returns:
        bool: True if local imports are found, False otherwise.
    """

    class FindLocalImports(ast.NodeVisitor):
        def visit_ImportFrom(self, node: ast.ImportFrom) -> bool:
            if node.level > 0:  # This means it's a relative import
                return True
            return False

    tree = ast.parse(code)
    visitor = FindLocalImports()
    return any(visitor.visit(node) for node in ast.walk(tree))


def remove_import(code: str, module_name: typing.Optional[str]) -> str:
    """
    Removes the import of a specific module from the given code.

    Args:
        code (str): The code from which to remove the import.
        module_name (str, optional): The name of the module to remove.

    Returns:
        str: The code after removing the import of the specified module.
    """
    tree = ast.parse(code)
    new_body = [
        node
        for node in tree.body
        if not isinstance(node, (ast.Import, ast.ImportFrom))
        or (not isinstance(node, ast.Import) or all(alias.name != module_name for alias in node.names))
        and (not isinstance(node, ast.ImportFrom) or node.module != module_name)
    ]
    tree.body = new_body
    return ast.unparse(tree)


def remove_local_imports(code: str) -> str:
    """
    Removes all local imports from the given code.

    Args:
        code (str): The code from which to remove local imports.

    Returns:
        str: The code after removing all local imports.
    """

    class RemoveLocalImports(ast.NodeTransformer):
        def visit_ImportFrom(self, node: ast.ImportFrom) -> typing.Optional[ast.ImportFrom]:
            if node.level > 0:  # This means it's a relative import
                return None  # Remove the node
            return node  # Keep the node

    tree = ast.parse(code)
    tree = RemoveLocalImports().visit(tree)
    return ast.unparse(tree)


def find_function_to_call(code: str, function_call_hint: str) -> typing.Optional[str]:
    """
    Finds the function to call in the given code based on the function call hint.

    Args:
        code (str): The code in which to find the function.
        function_call_hint (str): The hint for the function call.

    Returns:
        str, optional: The name of the function to call if found, None otherwise.
    """
    function_name = function_call_hint.split("(")[0]  # Extract function name from hint
    tree = ast.parse(code)
    return next(
        (function_name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == function_name),
        None,
    )


DEFAULT_ARGS = ("db",)


def extract_function_details(
    function_call: str, default_args: typing.Iterable[str] = DEFAULT_ARGS
) -> tuple[str | None, list[str]]:
    """
    Extracts the function name and arguments from the function call string.

    Args:
        function_call (str): The function call string.
        default_args (Iterable, optional): The default arguments for the function.

    Returns:
        tuple: A tuple containing the function name and a list of arguments.
    """
    function_name = function_call.split("(")[0]  # Extract function name from hint
    if "(" not in function_call:
        return function_name, list(default_args)

    with contextlib.suppress(SyntaxError):
        tree = ast.parse(function_call)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if len(node.args) == 0:
                    # If no arguments are given, add 'db' automatically
                    return function_name, list(default_args)

                func = typing.cast(ast.Name, node.func)
                return func.id, [ast.unparse(arg) for arg in node.args]

    return None, []


def add_function_call(
    code: str, function_call: str, args: typing.Iterable[str] = DEFAULT_ARGS, multiple: bool = False
) -> str:
    """
    Adds a function call to the given code.

    Args:
        code (str): The code to which to add the function call.
        function_call (str): The function call string.
        args (Iterable, optional): The arguments for the function call.
        multiple (bool, optional): If True, add a call after every function with the specified name.

    Returns:
        str: The code after adding the function call.
    """
    function_name, args = extract_function_details(function_call, default_args=args)

    def arg_value(arg: str) -> ast.Name:
        # make mypy happy
        body = typing.cast(NamedExpr, ast.parse(arg).body[0])
        return typing.cast(ast.Name, body.value)

    tree = ast.parse(code)
    # Create a function call node
    new_call = ast.Call(
        func=ast.Name(id=function_name, ctx=ast.Load()),
        args=[arg_value(arg) for arg in args] if args else [],
        keywords=[],
    )
    func_call = ast.Expr(value=new_call)

    # Insert the function call right after the function definition
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            tree.body.insert(i + 1, func_call)
            if not multiple:
                break

    return ast.unparse(tree)


def find_variables(code_str: str, with_builtins: bool = True) -> tuple[set[str], set[str]]:
    """
    Finds all used and defined variables in the given code string.

    Args:
        code_str (str): The code string to parse for variables.
        with_builtins (bool): include Python builtins?

    Returns:
        tuple: A tuple containing sets of used and defined variables.
    """
    # Partly made by ChatGPT
    code_str = textwrap.dedent(code_str)

    # could raise SyntaxError
    tree: ast.Module = ast.parse(code_str)

    used_variables: set[str] = set()
    defined_variables: set[str] = set()
    imported_modules: set[str] = set()
    imported_names: set[str] = set()
    loop_variables: set[str] = set()

    def collect_variables(node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                used_variables.add(node.id)
            elif isinstance(node.ctx, ast.Store):
                defined_variables.add(node.id)
            elif isinstance(node.ctx, ast.Del):
                defined_variables.discard(node.id)

    def collect_definitions(node: ast.AST) -> None:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            return

        def handle_elts(elts: list[ast.expr]) -> None:
            for node in elts:
                # with contextlib.suppress(Exception):
                try:
                    if isinstance(node, ast.Subscript):
                        node = node.value

                    if isinstance(node, ast.Tuple):
                        # recurse
                        handle_elts(node.elts)
                        continue

                    defined_variables.add(getattr(node, "id"))
                except Exception as e:  # pragma: no cover
                    warnings.warn("Something went wrong trying to find variables.", source=e)
                    # raise

        handle_elts(node.targets if hasattr(node, "targets") else [node.target])

    def collect_imports(node: ast.AST) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module_name = node.module
            imported_module = importlib.import_module(module_name)
            if node.names[0].name == "*":
                imported_names.update(name for name in dir(imported_module) if not name.startswith("_"))
            else:
                imported_names.update(alias.asname or alias.name for alias in node.names)

    def collect_imported_names(node: ast.AST) -> None:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)

    def collect_loop_variables(node: ast.AST) -> None:
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            loop_variables.add(node.target.id)

    def collect_everything(node: ast.AST) -> None:
        collect_variables(node)
        collect_definitions(node)
        collect_imported_names(node)
        collect_imports(node)
        collect_loop_variables(node)

    # manually rewritten (2.19s for 10k):
    traverse_ast(tree, collect_everything)

    all_variables = (
        defined_variables | imported_modules | loop_variables | imported_names | (BUILTINS if with_builtins else set())
    )

    return used_variables, all_variables


def find_missing_variables(code: str) -> set[str]:
    """
    Finds and returns all missing variables in the given code.

    Args:
        code (str): The code to check for missing variables.

    Returns:
        set: A set of names of missing variables.
    """
    used_variables, defined_variables = find_variables(code)
    return {var for var in used_variables if var not in defined_variables}


def generate_magic_code(missing_vars: set[str]) -> str:
    """
    Generates code to define missing variables with a do-nothing object.

    After finding missing vars, fill them in with an object that does nothing except return itself or an empty string.
    This way, it's least likely to crash (when used as default or validator in pydal, don't use this for running code!).

    Args:
        missing_vars (set): The set of missing variable names.

    Returns:
        str: The generated code.
    """
    extra_code = """
        class Empty:
            # class that does absolutely nothing
            # but can be accessed like an object (obj.something.whatever)
            # or a dict[with][some][keys]
            def __getattribute__(self, _):
                return self

            def __getitem__(self, _):
                return self

            def __get__(self):
                return self

            def __call__(self, *_):
                return self

            def __str__(self):
                return ''

            def __repr__(self):
                return ''

        # todo: overload more methods
        empty = Empty()
            \n
        """
    for variable in missing_vars:
        extra_code += f"{variable} = empty; "

    return textwrap.dedent(extra_code)
