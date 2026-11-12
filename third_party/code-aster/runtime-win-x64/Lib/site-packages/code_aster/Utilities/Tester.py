# coding=utf-8
# --------------------------------------------------------------------
# Copyright (C) 1991 - 2026 - EDF - www.code-aster.org
# This file is part of code_aster.
#
# code_aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# code_aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with code_aster.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

""":py:mod:`Tester` --- Checking code_aster execution of testcases
***************************************************************

"""

import inspect
import re
import unittest
import unittest.case as case
from functools import partial, wraps

import numpy as np

# TODO use the logger object
# TODO tell the Helpers to increase the exit status in case of failure
#      (through the logger) ?

_print = partial(print, flush=True)


def addSuccess(method):
    """Decorator to wrap TestCase methods by calling writeResult"""

    @wraps(method)
    def wrapper(inst, *args, **kwds):
        """Wrapper"""
        # move 'msg' arguments from args to kwds if it exists
        sig = inspect.signature(method)
        args = list(args)
        for i, para in enumerate(sig.parameters):
            if i >= len(args):
                break
            if para == "msg":
                kwds["msg"] = args.pop(i)
        try:
            ret = method(inst, *args, **kwds)
        except AssertionError as exc:
            ret = None
            inst.writeResult(False, method.__name__, kwds.get("msg"), str(exc))
        else:
            inst.writeResult(True, method.__name__, kwds.get("msg"))
        return ret

    return wrapper


def where(level=3):
    """Return the filename/line number where the test is called.

    Arguments:
        level (Optional[int]): Number of frames to rewind to find the
            caller. Defaults to 3 (1: *here*, 2: *write_xxx*, 3: *assertXxx*).

    Returns:
        (str, int): Filename and line number.

    """
    filename, line_no = "not_found", 0
    caller = inspect.currentframe()
    try:
        for _ in range(level):
            if not caller.f_back:
                break
            caller = caller.f_back
        filename = caller.f_code.co_filename
        line_no = caller.f_lineno
    finally:
        pass
    return f"{filename}#{line_no}"


class AssertRaisesContext(case._AssertRaisesContext):
    """Wrap Context of TestCase object"""

    def __init__(self, expected, test_case, expected_regexp=None):
        self.writeResult = test_case.writeResult
        # these two lines already exist in __exit__ in python >= 2.7.9
        if isinstance(expected_regexp, str):
            expected_regexp = re.compile(expected_regexp)
        super().__init__(expected, test_case, expected_regexp)

    def __exit__(self, exc_type, exc_value, tb):
        comment = ""
        try:
            ret = super().__exit__(exc_type, exc_value, tb)
            if not ret:
                try:
                    exc_name = exc_type.__name__
                except AttributeError:
                    exc_name = str(exc_type)
                raise AssertionError("unexpected exception raised: {0}".format(exc_name))
        except AssertionError as exc:
            ret = False
            comment = str(exc)
        try:
            exc_name = self.expected.__name__
        except AttributeError:
            exc_name = str(self.expected)
        self.writeResult(ret, exc_name, comment)
        # never fail
        return True


class TestCase(unittest.TestCase):
    """Similar to a unittest.TestCase
    Does not fail but print result OK/NOOK in the .resu file
    """

    def __init__(self, methodName="runTest", silent=False):
        """Initialization"""
        self._silent = silent
        self._passed = 0
        self._failure = 0
        self._last_ok = True
        super().__init__("runTest")

    @property
    def last_failed(self):
        """bool: Tell if the last test failed."""
        return not self._last_ok

    def runTest(self):
        """Does nothing"""
        pass

    def printSummary(self):
        """Print a summary of the tests"""
        _print(("-" * 70))
        count = self._passed + self._failure
        _print(
            ("Ran {0} tests, {1} passed, {2} in failure".format(count, self._passed, self._failure))
        )
        if self._failure:
            _print("\nNOOK\n")
        else:
            _print("\n OK \n")

    def writeResult(self, ok, funcTest, msg, exc=None):
        """Write a message in the result file"""
        if self._silent:
            return
        exc = exc or ""
        msg = msg or ""
        s1 = " : " if exc else ""
        s2 = " : " if msg else ""
        here = where()
        self._last_ok = ok
        if ok:
            self._passed += 1
            fmt = " OK  {func:>16} passed{s2}{msg}"
        else:
            self._failure += 1
            fmt = "NOOK {func:>16} failed{s1}{exc} - {here}"
        _print(fmt.format(func=funcTest, msg=msg, exc=exc, s1=s1, s2=s2, here=here))

    # just use a derivated context class
    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        """Fail unless an exception of class excClass is raised"""
        context = AssertRaisesContext(excClass, self)
        if callableObj is None:
            return context
        with context:
            callableObj(*args, **kwargs)

    def assertRaisesRegex(
        self, expected_exception, expected_regexp, callable_obj=None, *args, **kwargs
    ):
        """Asserts that the message in a raised exception matches a regexp."""
        context = AssertRaisesContext(expected_exception, self, expected_regexp)
        if callable_obj is None:
            return context
        with context:
            callable_obj(*args, **kwargs)

    def assertArrayEqual(self, actual, reference, rtol=1.0e-07, atol=1.0e-6):
        """Compare numpy arrays using isclose tolerance.

        If assertion fails a message will be printed detailling failing rows.

        Arguments:
            actual (numpy.ndarray): 1D or 2D
            reference (numpy.ndarray): 1D or 2D
            rtol (float): relative tolerance
            atol (float): absolute tolerance

        """
        if not actual.dtype.fields:
            is_close_results = np.isclose(actual, reference, rtol=rtol, atol=atol)
        else:
            to_stack = []
            for field in actual.dtype.fields:
                to_stack.append(np.isclose(actual[field], reference[field], rtol=rtol, atol=atol))
            is_close_results = np.stack(to_stack, axis=-1)
        arrays_are_equal = np.all(is_close_results)
        if not arrays_are_equal:
            differences = ~is_close_results
            not_equal_rows = np.any(differences, axis=-1)
            not_equal_rows_actual = actual[not_equal_rows]
            not_equal_rows_reference = reference[not_equal_rows]
            msg = (
                "Arrays are not equal, differing lines are printed bellow\n"
                f"actual: {not_equal_rows_actual}\n"
                f"reference: {not_equal_rows_reference}\n"
            )
        else:
            msg = "Arrays are equal"
        self.assertTrue(arrays_are_equal, msg=msg)


def _add_assert_methods(cls):
    for meth in [
        "assertAlmostEqual",
        "assertCountEqual",
        "assertDictContainsSubset",
        "assertDictEqual",
        "assertEqual",
        "assertFalse",
        "assertGreater",
        "assertGreaterEqual",
        "assertIn",
        "assertIs",
        "assertIsInstance",
        "assertIsNone",
        "assertIsNot",
        "assertIsNotNone",
        "assertLess",
        "assertLessEqual",
        "assertMultiLineEqual",
        "assertNotAlmostEqual",
        "assertNotEqual",
        "assertNotIn",
        "assertNotIsInstance",
        "assertNotRegex",
        "assertRegex",
        "assertSequenceEqual",
        "assertSetEqual",
        "assertTrue",
        "assertTupleEqual",
    ]:
        if not hasattr(unittest.TestCase, meth):
            continue
        setattr(cls, meth, addSuccess(getattr(unittest.TestCase, meth)))


_add_assert_methods(TestCase)
