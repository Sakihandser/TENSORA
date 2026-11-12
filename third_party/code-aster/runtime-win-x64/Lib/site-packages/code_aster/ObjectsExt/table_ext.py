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
:py:class:`Table` --- Representation of tables
**********************************************
"""

import aster
from libaster import Table, TableContainer, TableOfFunctions

from ..Objects.table_py import Table as TablePy
from ..Utilities import injector

from ..Objects.Serialization import InternalStateBuilder


class TableStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *Table*."""

    def restore(self, table):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            mesh (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(table)
        table.build()


@injector(Table)
class ExtendedTable:
    cata_sdj = "SD.sd_table.sd_table"
    internalStateBuilder = TableStateBuilder

    def __getitem__(self, key):
        """Retourne la valeur d'une cellule de la table.
        Exemple : TAB['INST', 1] retourne la 1ère valeur de la colonne 'INST'."""
        try:
            para, numlign = key
        except (TypeError, ValueError):
            raise RuntimeError("Table.__getitem__ takes exactly 2 arguments.")
        if para not in self.getParameters() or numlign > self.get_nrow():
            raise KeyError

        column = self.get_column(para)
        return column[numlign - 1]

    def get_column(self, para):
        """Retourne la colonne para"""
        exists, columnI, columnR, columnC, columnK = self.getValues(para)
        typ = self.getColumnType(para)
        if typ == "I":
            column = columnI
        elif typ == "R":
            column = columnR
        elif typ == "C":
            column = columnC
        else:
            column = columnK
        return [x if y else None for x, y in zip(column, exists)]

    def TITRE(self):
        """Retourne le titre d'une table Aster
        (Utile pour récupérer le titre et uniquement le titre d'une table dont
        on souhaite manipuler la dérivée).
        """
        titr = self.getTitle()
        if titr is None:
            titr = ""
        return titr

    def get_nrow(self):
        """Renvoie le nombre de lignes"""
        return self.getNumberOfLines()

    def get_nom_para(self):
        """Produit une liste des noms des colonnes"""
        return self.getParameters()

    def EXTR_TABLE(self, para=None):
        """Produit un objet TablePy à partir du contenu d'une table Aster.
        On peut limiter aux paramètres listés dans 'para'.
        """

        l_para = self.getParameters()
        if not l_para:
            return TablePy(titr=self.TITRE(), nom=self.getName())

        l_type = [self.getColumnType(para) for para in l_para]
        d_column = {para: self.get_column(para) for para in l_para}

        l_dic_values = []
        for i in range(self.get_nrow()):
            l_dic_values.append({para: d_column[para][i] for para in l_para})

        return TablePy(l_dic_values, l_para, l_type, self.TITRE(), self.getName())


@injector(TableOfFunctions)
class ExtendedTableOfFunctions:
    cata_sdj = "SD.sd_table_fonction.sd_table_fonction"


@injector(TableContainer)
class ExtendedTableContainer:
    cata_sdj = "SD.sd_table_container.sd_table_container"
