from __future__ import division
from copy import deepcopy
import numpy as np
import scipy.optimize
from .parameter import ParameterSet

class Curve(object):
    def __init__(self, name, model, data, weights=None, **user_args):
        # These shalln't be mutated
        self.name = name
        self.model = model
        self.data = data
        self.weights = weights
        self.user_args = user_args
        
    def eval_packed(self, params, **user_args):
        """ Evaluate the model """
        args = self.user_args.copy()
        args.update(user_args)
        return self.model(params, **args)

    def residuals_packed(self, params, **user_args):
        """ Compute the weighed residuals """
        residuals = self.eval_packed(params, **user_args) - self.data
        if self.weights is not None:
            residuals *= self.weights
        return residuals

class Fit(object):
    """
    This represents a fit configuration.
    """

    def __init__(self):
        self._curves = []
        self.param_set = ParameterSet()
    
    def param(self, name=None, initial=None):
        return self.param_set.param(name, initial=None)

    def add_curve(self, name, model, data, weights=None, **user_args):
        curve = Curve(name, model, data, weights, **user_args)
        self._curves.append(curve)
        
    def eval_packed(self, params, **user_args):
        """ Evaluate the model against packed parameters values """
        return {curve.name: curve.eval_packed(params, **user_args)
                for curve in self._curves}

    def residuals_packed(self, params, **user_args):
        """ Compute the weighed residuals against packed paramater values """
        return {curve.name: curve.residuals_packed(params, **user_args)
                for curve in self._curves}

    def eval(self, params, **user_args):
        """ Evaluate the model against a dictionary of parameters """
        return self.eval_packed(self.param_set._pack(params), **user_args)

    def residuals(self, params, **user_args):
        """ Evaluate the weighted model residuals against a dictionary of parameters """
        return self.residuals_packed(self.param_set._pack(params), **user_args)

    def fit(self, params0=None, **user_args):
        unpacked = self.param_set.initial_params()
        if params0 is not None:
            unpacked.update(params0)
        packed0 = self.param_set._pack(unpacked)
        def fit_func(p):
            res = self.residuals_packed(p, **user_args)
            return np.hstack(res.values())
        packed, cov, info, mesg, ier = scipy.optimize.leastsq(fit_func, packed0, full_output=True)
        if cov is None:
            unpacked_cov = None
        else:
            unpacked_cov = {name: self.param_set._unpack(inner)
                            for name, inner in self.param_set._unpack(cov).items()}
        params = self.param_set._unpack(packed)
        fit = FitResult(deepcopy(self), params0, params, unpacked_cov)
        return fit

class CurveResult(object):
    def __init__(self, fit_result, curve):
        params = fit_result.params
        self.fit_result = fit_result
        self.curve = curve
        self.npoints = len(self.curve.data)
        self.degrees_of_freedom = self.npoints - self.curve.model.count_params()
        self.residuals = self.curve.residuals_packed(self.fit_result.fit.param_set._pack(params))
        self.chi_sqr = sum(self.residuals**2)
        self.reduced_chi_sqr = self.chi_sqr / self.degrees_of_freedom
        
class FitResult(object):
    def __init__(self, fit, initial_params, params, covar):
        self.fit = fit
        self.initial_params = initial_params
        self.params = params
        print self.params
        self.covar = covar
        self.curves = {curve.name: CurveResult(self, curve)
                       for curve in fit._curves}