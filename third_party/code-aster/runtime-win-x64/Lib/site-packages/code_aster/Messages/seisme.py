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
    9: _(
        """
 -------Échantillonnage temporel et fréquentiel des signaux -------
        fréquence de coupure     : %(r1).2f Hz
        pas de fréquence         : %(r2)f Hz
        intervalle de temps      : %(r4)f s
        pas de temps    : PAS_INST = %(r3)f s
        nombre de points: NB_POIN  = %(i1)d
        fréquence du filtre temporel passe-haut: FREQ_FILTRE = %(k1)s

"""
    ),
    10: _(
        """
 correction statique non prise en compte pour l'option: %(k1)s
"""
    ),
    17: _(
        """
   la nature de l'excitation est             : %(k1)s """
    ),
    18: _(
        """
   la règle de combinaison des réponses
   directionnelles est                       : %(k1)s """
    ),
    19: _(
        """
   la règle de combinaison des contributions
   de chaque mouvement d'appui est           : %(k1)s """
    ),
    35: _(
        """
Attention, FREQ_FOND < 0 à l'instant t= %(k1)s s.
"""
    ),
    36: _(
        """
Tolérance sur l'ajustement du spectre au tirage %(i1)d:
L'erreur %(k1)s vaut %(r1).2f %% ce qui est supérieur à la borne de %(r2).2f %% demandée.
"""
    ),
    37: _(
        """
La fréquence maximale du spectre vaut %(k1)s Hz.
Il faut des fréquences inférieures à 100 Hz pour la modélisation SPEC_FRACTILE.
"""
    ),
    38: _(
        """
Il faut faire plus d'un seul tirage avec l'option SPEC_MEDIANE.
"""
    ),
    39: _(
        """
Attention:
    La durée de la simulation vaut %(k1)s s. Elle est inférieure à 1.5 fois la phase forte.
    Ceci peut conduire à des résultats moins bons.
Conseil:
    Augmenter NB_POINT ou réduire la durée de la phase forte.
"""
    ),
    41: _(
        """
 Erreur minimale optimisation multi-objectifs = %(r1).2f %% à l'itération %(i1)d
 Erreur absolue maximale = %(r2).2f  %% pour la fréquence %(r3)f Hz
 Erreur négative max     = %(r4).2f  %% pour la fréquence %(r5)f Hz
 Erreur ZPA max = %(r6).3f %%
 Erreur RMS max = %(r7).3f %%
"""
    ),
    42: _(
        """
 Itération %(i1)d sur %(i2)d : erreur multi-objectifs = %(r1).2f %%
"""
    ),
    43: _(
        """
 Erreurs initiales à l'itération 0:
 Erreur ZPA = %(r1).2f %%, erreur max = %(r2).2f %%, erreur RMS = %(r3).2f %%
 Erreur multi-objectifs = %(r4).2f %%
"""
    ),
    44: _(
        """
 ------- Modulation temporelle         ----------------------------
        paramètres de la fonction de modulation %(k1)s: %(k2)s
        durée de phase forte: %(r1).2f s
        instants de début et de fin phase forte: %(r2).2f s et %(r3).2f s
"""
    ),
    45: _(
        """Il n'y a pas de fonctions d'excitation de type '%(k1)s'.

Conseil:
    Vérifier le mot-clé NOM_CHAM et que vous souhaitez bien faire un
    calcul de type multi-appui ou avec prise en compte de la correction statique.
"""
    ),
    48: _(
        """
 --- GRANDEURS MODALES DES MODES PRIS EN COMPTE---
 --- (*) FACTEUR DE PARTICIPATION CALCULE AVEC MOUVEMENT CORPS RIGIDE---
                              FACTEUR DE   MASSE MODALE
 MODE     FREQUENCE  DIR   PARTICIPATION(*)      EFFECTIVE
"""
    ),
    53: _(
        """
 --- VALEURS DU SPECTRE ACCE (CORRECTION PAR CORR_FREQ et NATURE INCLUSES) ---
 MODE      FREQUENCE    AMORTISSEMENT    DIR         SPECTRE
"""
    ),
    54: _(
        """ %(i1)4d   %(r1)12.5e     %(r2)12.5e      %(k1)s    %(r3)12.5e
"""
    ),
    56: _(
        """
 --- VALEURS LUES SUR LE SPECTRE ACCE POUR LA CORRECTION STATIQUE ---
 DIRECTION      FREQUENCE        SPECTRE        APPUI
"""
    ),
    57: _(
        """         %(k1)s    %(r1)12.5e    %(r2)12.5e    %(k2)s
"""
    ),
    58: _(
        """"Pour la combinaison modale COMB_MODE de TYPE = 'GUPTA', FREQ_1 doit être inférieure à FREQ_2.
"""
    ),
    59: _(
        """La combinaison modale COMB_MODE de TYPE = 'GUPTA' est uniquement disponible en MONO_APPUI.
"""
    ),
    60: _(
        """Il y a au moins un noeud qui appartenant à plusieurs appuis.
"""
    ),
    61: _(
        """Avec TYPE_COMB = 'DSC', les amortissements doivent être non nuls et inférieurs à 1.
"""
    ),
    62: _(
        """On ne trouve pas le champ '%(k1)s' dans la base modale fournie sous mot clé MODE_MECA.
"""
    ),
    63: _(
        """On ne trouve pas la direction '%(k1)s' dans la base modale fournie sous mot clé PSEUDO_MODE.
"""
    ),
    64: _(
        """Pour TYPE_ANALYSE = 'MONO_APPUI', il faut renseigner au maximum un spectre par axe global X, Y, Z.
"""
    ),
    65: _(
        """Pour TYPE_ANALYSE = 'ENVELOPPE', les mots clés %(k1)s sous le mot clé facteur SPECTRE
            doivent avoir la même valeur.
"""
    ),
    66: _(
        """On ne trouve pas NOEUD_CMP='%(k1)s' dans la base modale fournie sous le mot clé %(k2)s.
"""
    ),
    67: _(
        """Il est inutile de calculer la réponse d'entraînement pour l'option %(k1)s.
"""
    ),
    68: _(
        """Il manque des modes pour effectuer la correction statique sur l'appui %(k1)s, direction %(k2)s.

Vérifiez que la base modale fournie sous le mot clé PSEUDO_MODES contient :
    - soit un pseudo-mode pour chaque noeud de l'appui dans la direction %(k2)s (nommés ci-dessus)
    - soit un unique pseudo-mode pour l'appui dans la direction X (nommé '%(k3)s')
"""
    ),
    77: _(
        """  Les coordonnées du noeud de référence COOR_REFE sont : ( %(r1).2f   %(r2).2f   %(r3).2f )
"""
    ),
    78: _(
        """  Le temps d'arrivée est négatif:
                il faut changer les coordonnées du noeud de référence COOR_REFE.
"""
    ),
    79: _(
        """ évaluation de la cohérence pour la phase forte du signal:
        instants de début et de fin phase forte: %(r1).2f s et %(r2).2f s
"""
    ),
    80: _(
        """
Les signaux renseignés dans les opérandes %(k1)s et %(k2)s de EXCIT_SOL n'ont pas
le même nombres de valeurs.
"""
    ),
    81: _(
        """
Les valeurs numéro %(i1)d  des abscisses des signaux renseignés dans les opérandes
%(k1)s et %(k2)s de EXCIT_SOL sont différentes.
"""
    ),
    82: _(
        """
Il faut renseigner le spectre à un sigma jusque 0.1 Hz pour SPEC_FRACTILE.
"""
    ),
    83: _(
        """
        Le germe pour les tirages aléatoires vaut %(i1)d.
"""
    ),
    84: _(
        """
La valeur du mot-clé FREQ_MIN est inférieure à la fréquence minimale de la moyenne des spectres calculés
ou du spectre cible fourni dans SPEC_OSCI.
"""
    ),
    85: _(
        """
La valeur du mot-clé FREQ_MAX est supérieure à la fréquence maximale de la moyenne des spectres calculés
ou du spectre cible fourni dans SPEC_OSCI.
"""
    ),
    86: _(
        """
La moyenne des spectres calculées est supérieure ou égale au spectre cible sur tout l'intervalle définit
par FREQ_MIN et FREQ_MAX. Il n'y a pas de correction à apporter au spectre moyen.
"""
    ),
    87: _(
        """
Facteur de correction apporté au spectre moyen : %(r1).2f
"""
    ),
    88: _(
        """
La table fournie n'est pas issue de GENE_ACCE_SEISME.
"""
    ),
    89: _(
        """
La valeur du mot-clé DUREE est supérieure à la durée totale des accélérogrammes.

   Valeur fournie        : %(r1).2f
   Durée accélérogrammes : %(r2).2f
"""
    ),
    90: _(
        """
Les spectres fournis par les mots-clés SPEC_OSCI et SPEC_1_SIGMA n'ont pas
les mêmes valeurs de fréquence.

Le calcul du spectre cible "moins un sigma" n'est pas possible.
"""
    ),
    91: _(
        """
Vous avez renseigné le mot-clé RATIO_HV or il n'y a pas de spectre vertical
dans les données fournies. Ce mot-clé n'a donc aucun impact.
"""
    ),
    92: _(
        """
Il y a un spectre vertical dans les données fournies, cependant vous n'avez pas renseigné
le mot-clé RATIO_HV. Cette valeur est fixée à 1.
"""
    ),
    93: _(
        """ Mot_clé MODE_SIGNE_%(k1)s  requis !
"""
    ),
    94: _(
        """ Avec la combinaison CQC_SIGNE, COMB_DIRECTION doit être NEWMARK.
"""
    ),
    95: _(
        """
 Le mot_clé FREQ_COUP n'est pas saisi, la fréquence de coupure est prise égale à
 celle du dernier mode dans la base modale: FREQ_COUP = %(r1).2f Hz
"""
    ),
    96: _(
        """
 La fréquence de coupure saisi FREQ_COUP = %(r1).2f Hz est inférieure à celle du
 premier mode dans la base modale. Donc, zéro mode physique est pris en compte dans la
 réponse.
"""
    ),
    97: _(
        """
 --- EN CAS DU MULT APPUI ---
 --- VALEURS DU SPECTRE ACCE (CORRECTION PAR CORR_FREQ et NATURE INCLUSES) ---
 MODE      FREQUENCE    AMORTISSEMENT    DIR         SPECTRE         APPUI         FACTEUR PARTICIPATION
"""
    ),
    98: _(
        """ %(i1)4d   %(r1)12.5e     %(r2)12.5e      %(k1)s    %(r3)12.5e    %(k2)s    %(r4)12.5e
"""
    ),
    99: _(
        """
Le numéro de mode demandé pour signer la réponse est invalide.
Direction : %(k1)s
Numéro de mode demandé : %(i1)d
Numéros de modes admis : %(k2)s
Vous devez choisir le mode à signer parmi les numéros de modes admis.
"""
    ),
}
