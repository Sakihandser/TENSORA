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
This module represents Commands syntax for the documentation.
"""

import os
import re
import types
import unittest
from itertools import chain
from pathlib import Path

from ..Cata import Commands as CMD
from ..Cata.Language import DataStructure as LDS
from ..Cata.Language import Rules
from ..Cata.Language.Syntax import (
    EXCLUS,
    FACT,
    OPER,
    PRESENT_ABSENT,
    PRESENT_PRESENT,
    SIMP,
    UN_PARMI,
)
from ..Cata.Language.SyntaxObjects import IDS, Command
from ..Cata.Language.SyntaxUtils import add_none_sdprod
from ..Utilities import force_list

try:
    import debugpy

    HAS_DEBUGPY = True
except ImportError:
    HAS_DEBUGPY = False

if os.environ.get("DEBUG", "") == "syntax_repr" and HAS_DEBUGPY:
    debugpy.listen(3000)
    print("Waiting for debugger attach")
    debugpy.wait_for_client()
    debugpy.breakpoint()

# https://www.compart.com/fr/unicode/
REQ = chr(9670)
OPT = chr(9671)
DEF = chr(10192)
# DEF = chr(9931)
XOR = "/"
ALT = "|"
AND = "&"
INDENT = "    "
CMT = "#"

SHOW_RULES = False


def _symbol(status):
    return {"o": REQ, "f": OPT, "d": DEF}.get(status)


def _typ2name(typ):
    if issubclass(typ, LDS.UnitBaseType):
        return "unit"
    name = typ.__name__.lower().replace("_sdaster", "")
    # exception for ParallelMesh
    if name.endswith("_p"):
        name = name.replace("_p", "")
    return name


def _var(typ):
    name = {"I": "int", "R": "float", "C": "complex", "TXM": "text"}.get(typ)
    if not name:
        names = set([_typ2name(i) for i in force_list(typ)])
        name = f" {XOR} ".join(sorted(names))
    return name


class Rule:
    """Store Rules parameters."""

    def __init__(self, attrs, args, next=[], always=False, score=0) -> None:
        self._attrs = attrs
        self._args = args
        self._first = True
        self._next = next
        self._always = always
        self._score = score

    @classmethod
    def factory(cls, rule_object):
        """Create an instance from a Cata Rule object."""
        if isinstance(rule_object, Rules.ExactlyOne):
            return Rule([REQ, XOR], rule_object.ruleArgs, score=60)
        if isinstance(rule_object, Rules.AtLeastOne):
            return Rule([REQ, ALT], rule_object.ruleArgs, score=50)
        if isinstance(rule_object, Rules.NotEmpty):
            return Rule([REQ, ALT], rule_object.ruleArgs, always=True, score=40)
        if isinstance(rule_object, Rules.AtMostOne):
            return Rule([OPT, XOR], rule_object.ruleArgs, score=30)
        if isinstance(rule_object, Rules.AllTogether):
            return Rule([OPT, AND], rule_object.ruleArgs, score=20)
        if isinstance(rule_object, Rules.OnlyFirstPresent):
            next = [ALT] if len(rule_object.ruleArgs) > 2 else []
            return Rule([OPT, XOR], rule_object.ruleArgs, next=next, score=11)
        if isinstance(rule_object, Rules.IfFirstAllPresent):
            next = [REQ] if len(rule_object.ruleArgs) > 2 else []
            return Rule([OPT, AND], rule_object.ruleArgs, next=next, score=10)
        raise NotImplementedError(rule_object)

    def __lt__(self, other):
        """Sort rules by priority."""
        return self._score < other._score

    @property
    def args(self):
        """Return the involved keywords."""
        return self._args

    def consumed(self):
        """Mark the rule as consumed/started"""
        assert self._attrs
        # print("DEBUG: consumed", self._attrs, "to", end=" ")
        for i, symb in enumerate(self._attrs[:-1]):
            if symb.strip():
                self._attrs[i] = " "
                break
        if self._first:
            self._attrs.extend(self._next)
        self._first = False
        # print(self._attrs)

    def involved(self, keyword):
        """Tell if a keyword is involved in the rule"""
        return self._always or keyword in self._args


class BaseLine:
    """Base object"""

    def __init__(self, lvl, name) -> None:
        self._lvl = lvl
        self._name = name
        self._hide = None

    @property
    def hidden(self):
        """Tell if the block should be hidden"""
        return self._hide

    @property
    def offset(self):
        """Current offset/indentation"""
        return self._lvl

    @property
    def attrs(self):
        return ""

    def set(self, defs, rules):
        """Set block settings from the keyword definition"""
        pass


class KwdLine(BaseLine):
    """Common for simple and factor keyworeds."""

    def __init__(self, lvl, name) -> None:
        super().__init__(lvl, name)
        self._attrs = []
        self._attrstr = None
        self._rules = []

    def set(self, defs, rules):
        """Set block settings from the keyword definition"""
        symb = _symbol(defs.get("statut"))
        if not symb:
            return
        self._attrs.append(symb)
        self._rules = sorted([rule for rule in rules if rule.involved(self._name)], reverse=True)
        if SHOW_RULES and len(self._rules) > 1:
            print(
                f"INFO: {self._name} first: {self._rules[0]._score}, "
                f"ignored {[i._score for i in self._rules[1:]]}"
            )

    @property
    def attrs(self):
        """Return the current symbols as a string."""
        # only once, must not consumed attrs several times
        if self._attrstr is not None:
            return self._attrstr
        if self._rules:
            attrs = self._rules[0]._attrs[:]
            self._rules[0].consumed()
            self._attrstr = " ".join(attrs)
        else:
            self._attrstr = " ".join(self._attrs)
        return self._attrstr

    @property
    def offset(self):
        """Current offset/indentation"""
        return self._lvl + self.attrs + " "


class SimpKwdLine(KwdLine):
    """Content for :

    .. code-block:: text

        ♦     FICHIER = / 'GLOBALE',
        attrs  name   =   into         type
        ♦     FICHIER = text,

    Replace "[I]", "[TXM]" by "int", "text" as "value". No type when 'into' exists.
    + min/max, "l_int" ?
    """

    def __init__(self, lvl, name) -> None:
        super().__init__(lvl, name)
        self._into = []
        self._typ = None
        self._default = None
        self._max = 1

    @property
    def hidden(self):
        """Tell if the block should be hidden"""
        self._hide = not bool(self._attrs) or self._name == "reuse"
        return super().hidden

    def set(self, defs, rules):
        """Set block settings from the keyword definition"""
        super().set(defs, rules)
        self._typ = defs.get("typ")
        self._into = defs.get("into", [])
        self._default = defs.get("defaut")
        self._max = defs.get("max", 1)

    def _repr_value(self, value):
        if self._typ == "TXM":
            return f'"{value}"'
        return str(value)

    def repr(self):
        """Representation of the block."""
        prefix = self.offset + self._name + " = "
        if not self._into:
            try:
                value = _var(self._typ)
                if self._max != 1:
                    value = f"list[{value}]"
            except AttributeError:
                raise TypeError(self._name, self._typ)
            if self._default is not None:
                value += f" (défaut: {self._repr_value(self._default)})"
            value = [value]
        else:
            if len(self._into) == 1:
                value = [self._repr_value(self._into[0])]
                if self._default is None:
                    value[-1] += " (ou non renseigné)"
            else:
                value = []
                for i in self._into:
                    value.append(f"{XOR} {self._repr_value(i)}")
                    if self._default is not None and i == self._default:
                        value[-1] += " (par défaut)"
        value.sort()
        lines = [prefix + value.pop(0) + ","]
        for remain in value:
            lines.append(" " * len(prefix) + remain + ",")
        return os.linesep.join(lines)


class ReuseLine(KwdLine):
    """Content for :

    .. code-block:: text

        ♦     reuse = ...
    """

    def __init__(self, lvl, name) -> None:
        super().__init__(lvl, name)

    @property
    def hidden(self):
        """Tell if the block should be hidden"""
        self._hide = False
        return super().hidden

    def set(self, defs, rules):
        """Set block settings from the keyword definition"""
        super().set(defs, rules)
        self._value = defs.get("value")

    def repr(self):
        """Representation of the block."""
        prefix = self.offset + self._name + " = "
        lines = [prefix + f"<objet de {self._value}>" + ","]
        return os.linesep.join(lines)


class FactLine(KwdLine):
    """For factor keyword:

    .. code-block::text

        AFFE = _F(
            ...
    """

    def repr(self):
        """Representation of the block."""
        return self.offset + self._name + " = _F("


class CmdLine(BaseLine):
    """For command:

    .. code-block::text

        maillage = COMMAND(
            ...
    """

    def __init__(self, lvl, name) -> None:
        super().__init__(lvl, name)
        self._results = []
        self._reused = None

    def set(self, defs, rules):
        """Set block settings from the keyword definition"""
        reentr = defs.get("reentrant", "").split(":", 1)
        if reentr[0] in ("o", "f"):
            self._reused = reentr
        all_types = self._get_all_types(defs)
        try:
            all_types = list(chain.from_iterable(all_types))
        except TypeError:
            pass
        self._results = sorted(set([_var(typ) for typ in all_types if typ]))

    @staticmethod
    def _get_all_types(defs):
        # same function as in SyntaxObjects.Command
        sd_prod = defs.get("sd_prod")
        if type(sd_prod) is types.FunctionType:
            args = {}
            add_none_sdprod(sd_prod, args)
            args["__all__"] = True
            return force_list(sd_prod(**args))
        else:
            return (sd_prod,)

    def repr(self):
        """Representation of the block."""
        # + reuse + sd_prod
        lines = [""]
        if self._results:
            if len(self._results) == 1:
                lines = [self._results[0]]
            else:
                lines = [f"{XOR} " + res for res in self._results]
            lines[-1] += " = "
        lines[-1] += self._name + "("
        lines = [self.offset + line for line in lines]
        if self._reused:
            reusable = " ou ".join(["/".join(i.split(":")) for i in self._reused[1].split("|")])
            reuse = ReuseLine(self.offset + INDENT, "reuse")
            reuse.set({"statut": self._reused[0], "value": reusable}, [])
            lines.append(reuse.repr())
        return os.linesep.join(lines)


class CondLine(BaseLine):
    """For conditional blocks"""

    def repr(self):
        """Representation of the block."""
        # condition is passed as 'name'
        return self.offset + f"{CMT} Si: " + self._name.strip()


class CloseLine(BaseLine):
    """End of a block."""

    def __init__(self, parent, end=",") -> None:
        super().__init__(0, "")
        self._parent = parent
        self._mark = ")" + end

    @property
    def hidden(self):
        """Tell if the block should be hidden"""
        return isinstance(self._parent, CondLine)

    @property
    def offset(self):
        """Current offset/indentation"""
        return " " * len(self._parent.offset)

    def repr(self):
        """Representation of the block."""
        return self.offset + self._mark


class DocSyntax:
    """Visitor to the syntax of a Command"""

    def __init__(self, command):
        super().__init__()
        self._lines = []
        self._command = command
        self._mcsimp = None
        self._mcfact = None
        self._indent = [""]
        self._rstack = [[]]

    def _visitComposite(self, step, userDict=None):
        """Visit a composite object (containing BLOC, FACT and SIMP objects)"""
        extracted = step.entities
        entities = []
        rules = self._rstack[-1][:]
        while extracted:
            name, entity = extracted.popitem(last=False)
            entities.append((name, entity))
            for rule in rules:
                if rule.involved(name):
                    for kwd in rule.args:
                        ent = extracted.pop(kwd, None)
                        if ent:
                            entities.append((kwd, ent))

        for name, entity in entities:
            if entity.getCataTypeId() == IDS.simp:
                self._mcsimp = name
            elif entity.getCataTypeId() == IDS.fact:
                self._mcfact = name
            elif entity.getCataTypeId() == IDS.bloc:
                self._bloc = entity.getCondition()
            entity.accept(self)

    def _visitCompositeWrap(self, step, name, line_class, end, userDict=None):
        """Visit a Command object"""
        line = line_class(self.indent, name)
        line.set(step.definition, self._rstack[-1])
        self._rstack.append([Rule.factory(rule) for rule in step.rules])
        self._append(line)
        self._indent.append(INDENT + " " * len(line.attrs))
        self._visitComposite(step, userDict)
        self._indent.pop()
        self._append(CloseLine(line, end=end))
        self._rstack.pop()

    def visitCommand(self, step, userDict=None):
        """Visit a Command object"""
        self._visitCompositeWrap(step, self._command, CmdLine, "", userDict)

    def visitMacro(self, step, userDict=None):
        """Visit a MacroCommand object"""
        self.visitCommand(step, userDict)

    def visitBloc(self, step, userDict=None):
        """Visit a Bloc object"""
        self._visitCompositeWrap(step, self._bloc, CondLine, "", userDict)

    def visitFactorKeyword(self, step, userDict=None):
        """Visit a FactorKeyword object"""
        self._visitCompositeWrap(step, self._mcfact, FactLine, ",", userDict)

    def visitSimpleKeyword(self, step, skwValue):
        """Visit a SimpleKeyword object"""
        line = SimpKwdLine(self.indent, self._mcsimp)
        line.set(step.definition, self._rstack[-1])
        self._append(line)
        # print(line.repr())

    @property
    def indent(self):
        return "".join(self._indent)

    def _append(self, line):
        self._lines.append(line)

    def repr(self, legend=False, codeblock=False):
        """Text representation"""
        text = [i.repr() for i in self._lines if not i.hidden]
        if legend:
            text.extend(
                [
                    "",
                    f"{REQ} : obligatoire",
                    f"{OPT} : optionnel",
                    f"{DEF} : présent par défaut",
                    f"{AND} : ensemble",
                    f"{XOR} : un seul parmi",
                    f"{ALT} : plusieurs choix possibles",
                ]
            )
        text.append("")
        text = os.linesep.join(text)
        if codeblock:
            text = [INDENT + line for line in text.splitlines()]
            text.insert(0, "")
            text.insert(0, ".. code-block:: text")
            text.append("")
            text = os.linesep.join(text)
        return text


def repr_command(cmd, show=True, output_dir=None):
    """Show the representation of syntax of a Command.

    Arg:
        cmd (Command): Command catalog.
        show (bool, optional): if True, print syntax on stdout.
        output (Path, optional): Output directory (or None).

    Returns:
        str: Syntax representation.
    """
    try:
        text = TestDoc.repr_and_write(cmd, output_dir)
    except:
        print("ERROR: with command =", cmd.name)
        raise
    if show:
        print(text)
    return text


def loop_on_commands(output_dir=None):
    """Loop on all Commands.

    Args:
        output (Path, optional): Output directory (or None).
    """
    for name in dir(CMD):
        obj = getattr(CMD, name)
        if issubclass(type(obj), Command):
            repr_command(obj, show=False, output_dir=output_dir)


class TestDoc(unittest.TestCase):
    """Test for DocSyntax"""

    @classmethod
    def repr_and_write(cls, cmd, output=None):
        syntax = DocSyntax(cmd.name)
        cmd.accept(syntax)
        text = syntax.repr(legend=True, codeblock=True)
        if output:
            output = Path(output)
            output.mkdir(parents=True, exist_ok=True)
            with open(output / (cmd.name.lower() + ".rst"), "w") as frst:
                frst.write(text)
        return text

    def _test01_into(self):
        fact = FACT(
            statut="f",
            regles=(UN_PARMI("TOUT", "GROUP_MA"),),
            TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
            GROUP_MA=SIMP(statut="f", typ="TXM", max="**"),
            INFO=SIMP(statut="f", typ="I", defaut=1, into=(1, 2)),
        )
        syntax = DocSyntax("TEST")
        syntax._mcfact = "AFFE"
        fact.accept(syntax)
        text = syntax.repr()
        # print(text)
        self.assertTrue(f'{REQ} {XOR} TOUT = "OUI" (ou non renseigné),' in text, msg="TOUT")
        self.assertTrue(f"{OPT} INFO = {XOR} 1 (par défaut)," in text, msg="INFO default")
        self.assertTrue(f"             {XOR} 2," in text, msg="INFO 2")

    def _test01_onlyfirst(self):
        fact = FACT(
            statut="d",
            regles=(
                PRESENT_ABSENT(
                    "RESI_REFE_RELA", "RESI_GLOB_MAXI", "RESI_GLOB_RELA", "RESI_COMP_RELA"
                ),
            ),
            RESI_REFE_RELA=SIMP(statut="f", typ="R"),
            RESI_GLOB_MAXI=SIMP(statut="f", typ="R"),
            RESI_GLOB_RELA=SIMP(statut="f", typ="R"),
            RESI_COMP_RELA=SIMP(statut="f", typ="R"),
            ITER_GLOB_MAXI=SIMP(statut="f", typ="I", defaut=10),
            ITER_GLOB_ELAS=SIMP(statut="f", typ="I", defaut=25),
        )
        syntax = DocSyntax("TEST")
        syntax._mcfact = "CONVERGENCE"
        fact.accept(syntax)
        text = syntax.repr()
        # print(text)
        self.assertTrue(f"{DEF} CONVERGENCE = _F(" in text, msg="CONVERGENCE")
        self.assertTrue(f"{OPT} {XOR} RESI_REFE_RELA" in text, msg="RESI_REFE_RELA nook")
        self.assertTrue(f"{XOR} {ALT} RESI_GLOB_MAXI" in text, msg="RESI_GLOB_MAXI nook")
        self.assertTrue(f"  {ALT} RESI_GLOB_RELA" in text, msg="RESI_GLOB_RELA nook")
        self.assertTrue(f"  {ALT} RESI_COMP_RELA" in text, msg="RESI_COMP_RELA nook")

    def _test01_iffirst(self):
        cmd = OPER(
            regles=(PRESENT_PRESENT("MULTIFIBRE", "GEOM_FIBRE", "FAKE"),),
            MULTIFIBRE=FACT(
                statut="f",
                GROUP_FIBRE=SIMP(statut="o", typ="TXM", max="**"),
                PREC_INERTIE=SIMP(statut="f", typ="R", defaut=0.1),
            ),
            GEOM_FIBRE=SIMP(statut="f", max=1, typ="R"),
            FAKE=SIMP(statut="f", max=1, typ="R"),
            INFO=SIMP(statut="f", typ="I", defaut=1),
        )
        syntax = DocSyntax("TEST")
        syntax._command = "AFFE_CARA_ELEM"
        cmd.accept(syntax)
        text = syntax.repr()
        # print(text)
        self.assertTrue(f"{OPT} {AND} MULTIFIBRE = _F(" in text, msg="MULTIFIBRE")
        self.assertTrue(f"  {AND} {REQ} GEOM_FIBRE" in text, msg="GEOM_FIBRE")
        self.assertTrue(f"    {REQ} FAKE" in text, msg="FAKE")

    def _test02_group_by_rule(self):
        fact = FACT(
            statut="f",
            regles=(EXCLUS("NUME_ORDRE", "INST", "FREQ"), PRESENT_ABSENT("TOUT", "GROUP_MA")),
            NUME_ORDRE=SIMP(statut="f", typ="I", max="**"),
            TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
            CRITERE=SIMP(statut="f", typ="TXM", defaut="RELATIF", into=("RELATIF", "ABSOLU")),
            GROUP_MA=SIMP(statut="f", typ="TXM", max="**"),
            INST=SIMP(statut="f", typ="R", max="**"),
            FREQ=SIMP(statut="f", typ="R", max="**"),
        )
        syntax = DocSyntax("TEST")
        syntax._mcfact = "CALC_CHAMP"
        fact.accept(syntax)
        text = syntax.repr()
        # print(text)
        self.assertIsNotNone(
            re.search("NUME_ORDRE.*INST.*FREQ.*TOUT.*GROUP_MA.*CRITERE", text, re.DOTALL),
            msg="keywords order",
        )

    def _test03_results(self):
        cmd = OPER(sd_prod=LDS.maillage_sdaster, reentrant="n")
        syntax = DocSyntax("TEST")
        cmd.accept(syntax)
        text = syntax.repr()
        # print(text)
        self.assertTrue(text.startswith("maillage = TEST("), msg="with one result")
        self.assertFalse("reuse" in text, msg="not reusable")

        def sd_prod(**args):
            if args.get("__all__"):
                return (LDS.maillage_sdaster, LDS.squelette, LDS.grille_sdaster, LDS.maillage_p)

        cmd = OPER(sd_prod=sd_prod, reentrant="f:MAILLAGE|GRILLE")
        syntax = DocSyntax("TEST")
        cmd.accept(syntax)
        text = syntax.repr()
        # print(text)
        self.assertTrue(f"{XOR} maillage" in text, msg="maillage")
        self.assertTrue(f"{XOR} squelette" in text, msg="squelette")
        self.assertTrue(f"{XOR} grille" in text, msg="grille")
        self.assertIsNotNone(
            re.search(rf"\{XOR} (maillage|grille|squelette) = TEST\(", text), msg="last line"
        )
        self.assertTrue("reuse" in text, msg="reusable")

    def _test10_lire_maillage(self):
        text = self.repr_and_write(CMD.LIRE_MAILLAGE)
        # print(text)
        self.assertTrue(f"{DEF} VERI_MAIL = _F(" in text, msg="VERI_MAIL")
        self.assertTrue(f'{OPT} VERIF = {XOR} "OUI" (par défaut),' in text, msg="VERIF default")
        self.assertIsNotNone(re.search("#.*FORMAT.*MED", text), msg="condition FORMAT=MED")

    test01_into = _test01_into
    test01_onlyfirst = _test01_onlyfirst
    test01_iffirst = _test01_iffirst
    test02_group_by_rule = _test02_group_by_rule
    test03_results = _test03_results
    test10_all = staticmethod(loop_on_commands)
