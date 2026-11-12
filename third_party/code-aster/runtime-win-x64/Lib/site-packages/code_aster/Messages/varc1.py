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

from ..Utilities import _

cata_msg = {
    1: _(
        """
 Vous utilisez la variable de commande de température alors que votre problème est couplé.
 Ce n'est pas possible.
"""
    ),
    2: _(
        """
 Erreur d'utilisation (AFFE_MATERIAU/AFFE_VARC) :
  Le maillage associé au calcul est différent de celui associé aux champs affectés dans AFFE_MATERIAU/AFFE_VARC.

 Conseil :
  Il faut corriger AFFE_MATERIAU.
"""
    ),
    3: _(
        """
La grandeur physique pour la variable de commande %(k1)s doit être  %(k2)s  mais elle est  %(k3)s.
"""
    ),
    4: _(
        """
   Le champ de la variable de commande %(k1)s est associé à un modèle qui n'est pas celui du calcul.
"""
    ),
    5: _(
        """
   Le champ de la variable de commande %(k1)s est associé à une option %(k2)s qui n'est pas 'INIT_VARC'
   Ce champ n'a sans doute pas été produit par PROJ_CHAMP / METHODE='SOUS_POINT'
"""
    ),
    6: _(
        """
Erreur utilisateur dans la commande AFFE_MATERIAU / AFFE_VARC
  Pour la variable de commande %(k1)s, la grandeur associée du champ doit être %(k2)s  mais elle est %(k3)s.
"""
    ),
    7: _(
        """
  Pour la variable de commande %(k1)s, le champ est de type %(k2)s, ce n'est pas possible.
"""
    ),
    8: _(
        """
  Pour la variable de commande %(k1)s, le champ a %(i1)d variables, or on en attend %(i2)d.
"""
    ),
    9: _(
        """
 Erreur d'utilisation (préparation des variables de commande) :
 Pour la variable de commande %(k1)s, il y a une incohérence du
 nombre de "sous-points" entre le CARA_ELEM (%(i1)d) et le CHAM_MATER (%(i2)d).

 Conseil :
 N'avez-vous pas défini plusieurs CARA_ELEM conduisant à des nombres de
 "sous-points" différents (COQUE_NCOU, TUYAU_NCOU, ...) ?
"""
    ),
}
