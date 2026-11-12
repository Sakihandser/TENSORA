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

# imports are in a string
# aslint: disable=C4009

"""
:py:mod:`command_files` --- Changing commands files
---------------------------------------------------

This modules provides some functions that change commands files.
"""

import re
from string import Template

_starter = Template(
    """
# temporarly added for compatibility with code_aster legacy
from math import *
${prolog}
import code_aster
${imports}

${starter}"""
)

NOINIT_START = Template(
    _starter.safe_substitute(
        imports=("from code_aster.Commands import *\nfrom code_aster import CA")
    )
)

AUTO_START = Template(
    _starter.safe_substitute(imports="from code_aster import CA\nfrom code_aster.Commands import *")
)


def add_import_commands(text):
    """Add import of code_aster commands if not present.

    Arguments:
        text (str): Text of a command file.

    Returns:
        str: Changed content.
    """
    re_done = re.compile(r"^from +code_aster(\.Commands| +import +CA)", re.M)
    if re_done.search(text):
        return text

    re_init = re.compile("^(?P<init>(DEBUT|POURSUITE))", re.M)
    if re_init.search(text):
        starter = r"\g<init>"
        text = re_init.sub(NOINIT_START.substitute(prolog="", starter=starter), text)
    return text


def add_coding_line(text):
    """Ensure to have 'coding' line at the beginning.

    Arguments:
        text (str): Text of a command file.

    Returns:
        str: Changed content.
    """
    re_coding = re.compile(r"^#( *(?:|\-\*\- *|en)coding.*)" + "\n", re.M)
    text = re_coding.sub("", text)
    text = "# coding=utf-8\n" + text
    return text


def stop_at_end(text, last=True):
    """Stop execution for interactive commands instead of calling ``FIN()``.

    Arguments:
        text (str): Text of a command file.
        last (bool): Tell if this is the last file to be executed.
            If *False*, 'FIN()' must be preserved.

    Returns:
        str: Changed content.
    """
    refin = re.compile(r"^(?P<cmd>(?:FIN|CA\.close) *\()", re.M)
    partial = r"""
from code_aster import CA

print("\n# CA.basedir is the directory containing the export file")
print(f"CA.basedir: {CA.basedir}")
"""
    subst = r"""
import code
import readline
import rlcompleter

from code_aster import CA

print("\\n# CA.basedir is the directory containing the export file")
print(f"CA.basedir: {CA.basedir}")

readline.parse_and_bind('tab: complete')
code.interact(local=locals(),
                banner=('Entering in interactive mode\\n'
                        'Use exit() or Ctrl-D (i.e. EOF) to continue '
                        'with \g<cmd>...)'),
                exitmsg='Use exit() or Ctrl-D (i.e. EOF) to exit')

\g<cmd>"""
    if last:
        spl = refin.split(text)
        if len(spl) <= 1:
            return text
        if len(spl) == 3:  # start, splitter, cmd, end
            if not spl[2][1:].strip():  # starts with ')\n'
                return spl[0] + partial
    text = refin.sub(subst, text)
    return text


def file_changed(text, original):
    """Additional modifications when the command file was changed.

    Arguments:
        text (str): Text of a command file.
        original (str): Path of original file.

    Returns:
        str: Changed content.
    """
    add = f"""# original filename
__file__ = r"{original}"

"""
    return add + text


def change_procdir(text):
    """Insert command to change into the 'proc.N' directory with N the rank of
    the MPI process.

    Arguments:
        text (str): Text of a command file.

    Returns:
        str: Changed content.
    """
    # 1. Do not use 'CA.MPI' that would start 'CA.init()'
    # 2. Usual mpi runs start from the workdir, so sys.path "." is expanded to
    # the workdir. That's why "." is inserted here again.
    add = """
import os
import sys
import time
from mpi4py import MPI

os.chdir(f"proc.{MPI.COMM_WORLD.Get_rank()}")
sys.path.insert(0, ".")
with open(".pid", "w") as fpid:
    fpid.write(str(os.getpid()))

delay = int(os.environ.get("WAIT_FOR_DDT", 0))
if delay:
    print(f"waiting {delay} seconds before starting...")
    time.sleep(delay)

del delay

"""
    return add + text
