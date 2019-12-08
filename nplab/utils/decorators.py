"""
A collection of decorators useful when subclassing in NPLab
"""
from __future__ import print_function
from builtins import object
__author__ = 'alansanders'


class inherit_docstring(object):
    """Appends the current functions docstring with that of the specified base function"""
    def __init__(self, base_f):
        self.base_f = base_f

    def __call__(self, f):
        # if the base function has no docstring then do nothing
        if self.base_f.__doc__ is None:
            return f
        # using new lines is not necessary if there is no current docstring to separate
        if f.__doc__ is None:
            f.__doc__ = self.base_f.__doc__
        elif f.__doc__ == '':
            f.__doc__ += self.base_f.__doc__
        # if there is a docstring in both the current function and the base function
        # then the new docstring will include both docstrings separated by an empty line
        else:
            f.__doc__ += '\n\n'+self.base_f.__doc__
        return f


if __name__ == '__main__':
    class A(object):
        def foo(self, x):
            """Docstring for A"""
            return x+1

    class B(A):
        @inherit_docstring(A.foo)
        def foo(self, x):
            return x+2

    class C(B):
        @inherit_docstring(B.foo)
        def foo(self, x):
            """Docstring for C"""
            return x+3

    print(C.foo.__doc__)