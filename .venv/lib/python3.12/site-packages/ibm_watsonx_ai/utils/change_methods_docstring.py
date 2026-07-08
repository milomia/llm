#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import types
import inspect

package_name = "ibm_watson_machine_learning"
new_package_name = "ibm_watsonx_ai"

def copy_enum(enum):
    attribute = getattr(enum, '__module__')
    setattr(enum, '__module__', attribute.replace(package_name, new_package_name))
    return enum

def copy_func(f):
    new_globals = f.__globals__.copy()
    model_spec = new_globals['__spec__']
    model_spec.name = model_spec.name.replace(package_name, new_package_name)

    for attribute in new_globals:
        if isinstance(new_globals[attribute], str):
            new_globals[attribute] = new_globals[attribute].replace(package_name, new_package_name)

    g = types.FunctionType(f.__code__, new_globals, name=f.__name__,
                        argdefs=f.__defaults__,
                        closure=f.__closure__)
    g.__kwdefaults__ = f.__kwdefaults__

    old_docstring = g.__doc__
    if old_docstring is not None:
        g.__doc__ = old_docstring.replace(package_name, new_package_name)
    return g

def change_docstrings(original_class):
    parent_class = original_class.__mro__[1]
    defined_methods = (method for method in dir(original_class) if not method.startswith("_") and\
                        method in parent_class.__dict__)
    for method_name in defined_methods:
        method = inspect.getattr_static(original_class, method_name)        
        if (callable(method) and  original_class.__name__ in getattr(method, "__globals__", {})) or\
              (isinstance(parent_class.__dict__[method_name], (staticmethod, classmethod))):
            if not isinstance(parent_class.__dict__[method_name], (staticmethod, classmethod)):
                setattr(original_class, method_name, copy_func(method))
            else:
                old_docstring = method.__doc__
                if old_docstring:
                    new_docstring = old_docstring.replace(package_name, new_package_name)
                    method.__doc__ = new_docstring
                function = copy_func(parent_class.__dict__[method_name].__func__)
                if isinstance(parent_class.__dict__[method_name], staticmethod):
                    setattr(original_class, method_name, staticmethod(function))
                else:
                    setattr(original_class, method_name, classmethod(function))

    return original_class
