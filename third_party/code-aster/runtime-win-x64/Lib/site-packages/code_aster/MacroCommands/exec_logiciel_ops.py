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


"""
This module defines the EXEC_LOGICIEL operator
"""

import subprocess
import sys
import traceback
from subprocess import PIPE

from libaster import AsterError

from ..Messages import UTMESS
from ..Utilities import config


class CommandLine:
    """Simple command line builder"""

    def __init__(self):
        """Initialisation"""

    def build(self, cmd, shell=False):
        """Return the command line to execute"""
        if shell:
            cmd = " ".join(cmd)
        return cmd


class ExecProgram:
    """Execute a program from Code_Aster

    Attributes:
    :step: the *etape* object
    :prog: the program to execute
    :args: the arguments passed to the program
    :shell: indicator to run the program through a shell
    :debug: debug flag
    :exitCodeMax: the maximum acceptable return code
    :cmdBuilder: object to build the command line
    """

    def __init__(self, step):
        """Initialisation"""
        self.step = step
        # Other attributes are initialized by configure.
        # Ensure that `cleanUp()` has the necessary attrs

    def configure(self, kwargs):
        """Pre-execution function, read the keywords"""
        self.prog = kwargs.get("LOGICIEL")
        self.args = list(kwargs.get("ARGUMENT") if "ARGUMENT" in kwargs else [])
        self.shell = kwargs.get("SHELL") == "OUI"
        self.debug = kwargs.get("INFO") == 2
        self.exitCodeMax = kwargs.get("CODE_RETOUR_MAXI")
        self.cmdBuilder = CommandLine()

    def execute(self):
        """Execute the program"""
        self.executeCommand()

    def post(self):
        """Execute a post-function"""

    def cleanUp(self):
        """Cleanup function executed even if `execute` fails"""

    def executeCmdLine(self, cmd, capture, silent=False):
        """Execute the command line.
        Return output, error and the exit code"""
        if self.debug or not silent:
            UTMESS("I", "EXECLOGICIEL0_8", valk=repr(cmd))
        options = {}
        if config["ASTER_PLATFORM_POSIX"]:
            options["close_fds"] = True
        if capture:
            options["stdout"] = PIPE
            options["stderr"] = PIPE
        process = subprocess.Popen(cmd, shell=self.shell, **options)
        output, error = process.communicate()
        status = process.returncode
        return output or "", error or "", status

    def executeCommand(self, capture=True, silent=False):
        """Execute the program"""
        cmd = self.cmdBuilder.build([self.prog] + self.args, self.shell)
        output, error, exitCode = self.executeCmdLine(cmd, capture, silent)
        if type(output) is bytes:
            output = output.decode()
        if type(error) is bytes:
            error = error.decode()
        ok = self.isOk(exitCode)
        # print the output
        if self.debug or not silent:
            UTMESS("I", "EXECLOGICIEL0_11", vali=[self.exitCodeMax, exitCode])
            if capture:
                UTMESS("I", "EXECLOGICIEL0_9", valk=output)
        # print error in debug mode or if it failed
        if (self.debug or not ok) and capture:
            UTMESS("I", "EXECLOGICIEL0_10", valk=error, print_as="E")
        # error
        if not ok:
            UTMESS("F", "EXECLOGICIEL0_3", vali=[self.exitCodeMax, exitCode])

    def isOk(self, exitCode):
        """Tell if the execution succeeded"""
        if self.exitCodeMax < 0:
            return True
        return exitCode <= self.exitCodeMax


def exec_logiciel_ops(self, **kwargs):
    """Execute a program"""

    action = ExecProgram(self)
    try:
        action.configure(kwargs)
        action.execute()
        return action.post()
    except AsterError:
        raise
    except Exception as err:
        trace = "".join(traceback.format_tb(sys.exc_info()[2]))
        UTMESS("F", "SUPERVIS2_3", valk=("EXEC_LOGICIEL", trace, str(err)))
    finally:
        action.cleanUp()
    return
