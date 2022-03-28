# -*- coding: utf-8 -*-
"""
Created on Mon Apr 26 10:26:43 2021

@author: Robin Grapin
"""
import numpy as np
from scipy.stats import norm
from smoot.montecarlo import MonteCarlo


class Criterion(object):
    def __init__(
        self,
        name,
        models,
        ref=None,
        s=None,
        hv=None,
        random_state=None,
        subcrit=None,
        transfo=None,
    ):
        self.models = models
        self.name = name
        self.ref = ref
        self.s = s
        self.hv = hv
        self.points = 100 * len(models)  # maybe 100 too slow ?
        self.random_state = random_state
        self.subcrit = subcrit
        self.transfo = transfo

    def __call__(self, x, means=None, variances=None, pareto_front=None):
        if self.name == "PI":
            return self.PI(x)
        if self.name == "EHVI":
            return self.EHVI(x)
        if self.name == "HV":
            return self.HV(x)
        if self.name == "WB2S":
            return self.WB2S(x)
        if self.name == "MPI":
            return self.MPI(x)

    def MPI(self, x):
        """
        Minimal Porbability of Improvement

        Parameters
        ----------
        x : list
            coordinate in the design point to evaluate.

        Returns
        -------
        float
            MPI(x).
        """
        x = np.asarray(x).reshape(1, -1)

        pf = Criterion._compute_pareto(self.models)
        variances = [mod.predict_variances for mod in self.models]
        etypes = [var(x)[0][0] ** 0.5 for var in variances]
        if 0 in etypes:  # training point
            return 0
        moyennes = [mod.predict_values for mod in self.models]
        moy = [m(x)[0][0] for m in moyennes]
        probas = [
            np.prod(
                [norm.cdf((moy[i] - f[i]) / etypes[i]) for i in range(len(moyennes))]
            )
            for f in pf
        ]

        return 1 - max(probas)  # min( 1 - P )

    def PI(self, x):
        """
        Probability of improvement of the point x for 2 objectives.
        If more than 2 objectives, computed using Monte-Carlo sampling instead

        Parameters
        ----------
        x : list
            coordinates in the design space of the point to evaluate.

        Returns
        -------
        pi_x : float
            PI(x) : probability that x is an improvement € [0,1]
        """

        x = np.asarray(x).reshape(1, -1)
        pareto_front = Criterion._compute_pareto(self.models)

        if len(self.models) > 2:
            y = np.asarray(
                [
                    mod.predict_values(x)[0][0]
                    - 3 * mod.predict_variances(x)[0][0] ** 0.5
                    for mod in self.models
                ]
            )
            if Criterion.is_dominated(y, pareto_front):
                return 0  # the point - 3sigma is dominated, almost no chances of improvement
            MC = MonteCarlo(random_state=self.random_state)
            q = MC.sampling(x, self.models, self.points)
            return (
                self.points
                - sum([Criterion.is_dominated(qi, pareto_front) for qi in q])
            ) / self.points  # maybe we can remove the division by self.points as there is the same amount of points for each call? It's just for scale here

        pareto_front.sort(key=lambda x: x[0])
        moyennes = [mod.predict_values for mod in self.models]
        variances = [mod.predict_variances for mod in self.models]
        sig1, sig2 = variances[0](x)[0][0] ** 0.5, variances[1](x)[0][0] ** 0.5
        moy1, moy2 = moyennes[0](x)[0][0], moyennes[1](x)[0][0]
        m = len(pareto_front)
        try:
            pi_x = norm.cdf((pareto_front[0][0] - moy1) / sig1)
            for i in range(1, m - 1):
                pi_x += (
                    norm.cdf((pareto_front[i + 1][0] - moy1) / sig1)
                    - norm.cdf((pareto_front[i][0] - moy1) / sig1)
                ) * norm.cdf((pareto_front[i + 1][1] - moy2) / sig2)
            pi_x += (1 - norm.cdf((pareto_front[m - 1][0] - moy1) / sig1)) * norm.cdf(
                (pareto_front[m - 1][1] - moy2) / sig2
            )
            return pi_x
        except ZeroDivisionError:  # for training points -> variances = 0
            return 0

    @staticmethod
    def psi(a, b, µ, s):
        return s * norm.pdf((b - µ) / s) + (a - µ) * norm.cdf((b - µ) / s)

    def EHVI(
        self,
        x,
    ):
        """
        Expected hypervolume improvement of the point x for 2 objectives.
        If more than 2 objectives, computed using Monte-Carlo sampling instead

        Parameters
        ----------
        x : list
            coordinates in the design space of the point to evaluate.

        Returns
        -------
        float
            Expected HVImprovement
        """

        x = np.asarray(x).reshape(1, -1)
        f = Criterion._compute_pareto(self.models)

        if len(self.models) > 2:
            y = np.asarray(
                [
                    mod.predict_values(x)[0][0]
                    - 3 * mod.predict_variances(x)[0][0] ** 0.5
                    for mod in self.models
                ]
            )
            if Criterion.is_dominated(y, f):
                return 0  # the point - 3sigma is dominated, no chances to improve hv
            MC = MonteCarlo(random_state=self.random_state)
            q = MC.sampling(x, self.models, self.points)
            return (
                sum([self.hv.calc(np.vstack((f, qi))) for qi in q]) / self.points
            )  # maybe we can remove the division by self.points as there is the same amount of points for each call? It's just for scale here

        variances = [mod.predict_variances for mod in self.models]
        s1, s2 = variances[0](x)[0][0] ** 0.5, variances[1](x)[0][0] ** 0.5
        if s1 == 0 or s2 == 0:  # training point
            return 0
        moyennes = [mod.predict_values for mod in self.models]
        µ1, µ2 = moyennes[0](x)[0][0], moyennes[1](x)[0][0]
        f.sort(key=lambda x: x[0])
        f.insert(0, np.array([self.ref[0], -1e15]))  # 1e15 to approximate infinity
        f.append(np.array([-1e15, self.ref[1]]))
        res1, res2 = 0, 0
        for i in range(len(f) - 1):
            res1 += (
                (f[i][0] - f[i + 1][0])
                * norm.cdf((f[i + 1][0] - µ1) / s1)
                * Criterion.psi(f[i + 1][1], f[i + 1][1], µ2, s2)
            )
            res2 += (
                Criterion.psi(f[i][0], f[i][0], µ1, s1)
                - Criterion.psi(f[i][0], f[i + 1][0], µ1, s1)
            ) * Criterion.psi(f[i][1], f[i][1], µ2, s2)
        return res1 + res2

    def HV(self, x):
        """
        hypervolume if x is the new point added. Only the mean is taken,
        so it doesn't explore as it doesn't take in account the incertitude.
        A good idea is to combine it with the var. (to do : look if ucb is doing this)

        Parameters
        ----------
        x : list
            coordinates in the design space of the point to evaluate.

        Returns
        -------
        out : float
            Hypervolume of the current front concatened with µ(x)
        """
        x = np.asarray(x).reshape(1, -1)
        pf = Criterion._compute_pareto(self.models)
        moyennes = [mod.predict_values for mod in self.models]
        y = np.asarray([moy(x)[0][0] for moy in moyennes])
        return self.hv.calc(np.vstack((pf, y)))

    def WB2S(self, x):
        """
        Criterion WB2S multi-objective adapted from the paper "Adapated
        modeling strategy for constrained optimization with application
        to aerodynamic wing design" :
        WB2S(x) = s*subcriterion(x) - transformation( µ(x) )

        Parameters
        ----------
        x : list
            coordinates in the design space of the point to evaluate.

        Returns
        -------
        WBS2 : float
        """
        x = np.asarray(x).reshape(1, -1)
        moyennes = [mod.predict_values for mod in self.models]
        µ = [moy(x)[0][0] for moy in moyennes]
        return self.s * self.subcrit(x) - self.transfo(µ)

    @staticmethod
    def _compute_pareto(modeles):
        """
        Set curr_pareto_front to the non-dominated training points.
        It allows to compute it once for a complete enrichment step
        """
        ydata = np.transpose(
            np.asarray([mod.training_points[None][0][1] for mod in modeles])
        )[0]
        pareto_index = Criterion.pareto(ydata)
        # self.curr_pareto_front = [ydata[i] for i in pareto_index]
        # I remove this and the associated self. variable beacause for a reason that I do not unserstand, it is way faster to recompute it at every call than to store it
        return [ydata[i] for i in pareto_index]

    @staticmethod
    def pareto(Y):
        """
        Parameters
        ----------
        Y : list of arrays
            list of the points to compare.

        Returns
        -------
        index : list
            list of the indexes in Y of the Pareto-optimal points.
        """
        index = []  # indexes of the best points (Pareto)
        n = len(Y)
        dominated = [False] * n
        for y in range(n):
            if not dominated[y]:
                for y2 in range(y + 1, n):
                    if not dominated[
                        y2
                    ]:  # if y2 is dominated (by y0), we already compared y0 to y
                        y_domine_y2, y2_domine_y = Criterion.dominate_min(Y[y], Y[y2])

                        if y_domine_y2:
                            dominated[y2] = True
                        if y2_domine_y:
                            dominated[y] = True
                            break
                if not dominated[y]:
                    index.append(y)
        return index

    # returns a-dominates-b , b-dominates-a !! for minimization !!
    @staticmethod
    def dominate_min(a, b):
        """
        Parameters
        ----------
        a : array or list
            coordinates in the objective space.
        b : array or list
            same thing than a.

        Returns
        -------
        bool
            a dominates b (in terms of minimization !).
        bool
            b dominates a (in terms of minimization !).
        """
        a_bat_b = False
        b_bat_a = False
        for i in range(len(a)):
            if a[i] < b[i]:
                a_bat_b = True
                if b_bat_a:
                    return False, False  # same front
            if a[i] > b[i]:
                b_bat_a = True
                if a_bat_b:
                    return False, False
        if a_bat_b and (not b_bat_a):
            return True, False
        if b_bat_a and (not a_bat_b):
            return False, True
        return False, False  # same values

    @staticmethod
    def is_dominated(y, pf):
        """True if y is dominated by a point of pf"""
        for z in pf:
            battu, _ = Criterion.dominate_min(z, y)
            if battu:
                return True
        return False

    @staticmethod
    def prob_of_feasability(x, const_modeles):
        """
        Product of the probabilities that x is a feasible solution,
        assuming that the constraints are independents, and modelized by
        gaussian models.
        """
        means = [mod.predict_values for mod in const_modeles]
        var = [mod.predict_variances for mod in const_modeles]
        x = np.asarray(x).reshape(1, -1)
        probs = [
            norm.cdf(-means[i](x)[0][0] / var[i](x)[0][0])
            for i in range(len(const_modeles))
        ]
        return np.prod(probs)
