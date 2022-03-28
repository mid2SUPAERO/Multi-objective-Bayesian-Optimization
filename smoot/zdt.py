# -*- coding: utf-8 -*-
"""
Created on Tue Apr  6 10:07:51 2021

@author: robin
"""

import numpy as np
from smt.problems.problem import Problem


class ZDT(Problem):
    """
    ZDT toolkit
    x = {x1.. xn}
    y = {x1.. xj} = {y1.. yj}
    z = {x(j+1).. xn} = {z1.. zk}
    Testing functions with the shape :
        f1 : y -> f1(y)
        f2 : y,z -> g(z)h(f1(y),g(z))
    xbounds = [0,1]**n
    """

    def _initialize(self):
        self.options.declare("ndim", 2, types=int)
        self.options.declare("name", "ZDT", types=str)
        self.options.declare(
            "type", 1, values=[1, 2, 3, 4, 5], types=int
        )  # one of the 5 test functions

    def _setup(self):
        self.xlimits[:, 1] = 1.0

    def _evaluate(self, x, kx=None):
        """
        Arguments
        ---------
        x : ndarray[ne, n_dim]
            Evaluation points.

        Returns
        -------
        [ndarray[ne, 1],ndarray[ne, 1]]
            Functions values.
        """
        ne, nx = x.shape
        j = min(1, nx - 1)  # if one entry then no bug
        f1 = np.zeros((ne, 1))

        if self.options["type"] < 5:
            f1[:, 0] = x[:, 0]
        else:
            f1[:, 0] = 1 - np.exp(-4 * x[:, 0]) * np.sin(6 * np.pi * x[:, 0]) ** 6

        # g
        g = np.zeros((ne, 1))
        if self.options["type"] < 4:
            for i in range(ne):
                g[i, 0] = 1 + 9 / (nx - j) * sum(x[i, j:nx])
        elif self.options["type"] == 4:
            for i in range(ne):
                g[i, 0] = (
                    1
                    + 10 * (nx - j)
                    + sum(x[i, j:nx] ** 2 - 10 * np.cos(4 * np.pi * x[i, j + 1 : nx]))
                )
        else:
            for i in range(ne):
                g[i, 0] = 1 + 9 * (sum(x[i, j:nx]) / (nx - j)) ** 0.25

        # h
        h = np.zeros((ne, 1))
        if self.options["type"] == 1 or self.options["type"] == 4:
            for i in range(ne):
                h[i, 0] = 1 - np.sqrt(f1[i, 0] / g[i, 0])
        elif self.options["type"] == 2 or self.options["type"] == 5:
            for i in range(ne):
                h[i, 0] = 1 - (f1[i, 0] / g[i, 0]) ** 2
        else:
            for i in range(ne):
                h[i, 0] = (
                    1
                    - np.sqrt(f1[i, 0] / g[i, 0])
                    - f1[i, 0] / g[i, 0] * np.sin(10 * np.pi * f1[i, 0])
                )

        return np.hstack((f1, g * h))

    def pareto(self, npoints=300, random_state=None):
        """
        Give points of the pareto set and front, useful for plots and
        solver's quality comparition. Pareto reached when g = 0 in ZDT,
        what means that only x1 is not null.

        Parameters
        ----------
        npoints : int, optional
            NUmber of points to generate. The default is 300.

        Returns
        -------
        X,Y : ndarray[npoints, ndim] , [ndarray[npoints, 1],ndarray[npoints, 1]]
            X are points from the pareto set, Y their values.

        """
        rand = np.random.RandomState(random_state)
        X = np.zeros((npoints, self.options["ndim"]))
        if self.options["type"] == 3:
            F = [
                [0, 0.0830015349],
                [0.4093136748, 0.4538821041],
                [0.6183967944, 0.6525117038],
                [0.8233317983, 0.8518328654],
            ]
            b1 = F[0][1]
            b2 = b1 + F[1][1] - F[1][0]
            b3 = b2 + F[2][1] - F[2][0]
            b4 = b3 + F[3][1] - F[3][0]  # sum([inter[1]-inter[0] for inter in F ])
            for i in range(npoints):
                pt = rand.uniform(0, b4)
                if pt > b3:
                    X[i, 0] = F[3][0] + pt - b3
                elif pt > b2:
                    X[i, 0] = F[2][0] + pt - b2
                elif pt > b1:
                    X[i, 0] = F[1][0] + pt - b1
                else:
                    X[i, 0] = pt
        else:
            X[:, 0] = rand.uniform(0, 1, npoints)
        return X, self._evaluate(X)
