#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Estimator for classifier error distributions."""

__docformat__ = 'restructuredtext'

import numpy as N

from mvpa.base import externals, warning
from mvpa.misc.state import Stateful, StateVariable

if __debug__:
    from mvpa.base import debug


class Nonparametric(object):
    """Non-parametric 1d distribution -- derives cdf based on stored values.

    Introduced to complement parametric distributions present in scipy.stats.
    """

    def __init__(self, dist_samples):
        self._dist_samples = N.ravel(dist_samples)


    @staticmethod
    def fit(dist_samples):
        return [dist_samples]


    def cdf(self, x):
        """Returns the cdf value at `x`.
        """
        return N.vectorize(lambda v:(self._dist_samples <= v).mean())(x)


def _pvalue(x, cdf_func, tail):
    """Helper function to return p-value(x) given cdf and tail
    """
    is_scalar = N.isscalar(x)
    if is_scalar:
        x = [x]

    cdf = cdf_func(x)
    if tail == 'left':
        pass
    elif tail == 'right':
        cdf = 1 - cdf
    elif tail == 'any':
        right_tail = (cdf >= 0.5)
        cdf[right_tail] = 1.0 - cdf[right_tail]

    if is_scalar: return cdf[0]
    else:         return cdf


class NullDist(Stateful):
    """Base class for null-hypothesis testing.

    """

    # Although base class is not benefiting from states, derived
    # classes do (MCNullDist). For the sake of avoiding multiple
    # inheritance and associated headache -- let them all be Stateful,
    # performance hit should be negligible in most of the scenarios
    _ATTRIBUTE_COLLECTIONS = ['states']

    def __init__(self, tail='left', **kwargs):
        """Cheap initialization.

        :Parameter:
          tail: str ['left', 'right', 'any']
            Which tail of the distribution to report. For 'any' it chooses
            the tail it belongs to based on the comparison to p=0.5
        """
        Stateful.__init__(self, **kwargs)

        self._tail = tail

        # sanity check
        if tail not in ['left', 'right', 'any']:
            raise ValueError, 'Unknown value "%s" to `tail` argument.' \
                  % tail


    def fit(self, measure, wdata, vdata=None):
        """Implement to fit the distribution to the data."""
        raise NotImplementedError


    def cdf(self, x):
        """Implementations return the value of the cumulative distribution
        function (left or right tail dpending on the setting).
        """
        raise NotImplementedError


    def p(self, x):
        """Returns the p-value for values of `x`.
        Returned values are determined left, right, or from any tail
        depending on the constructor setting.

        In case a `FeaturewiseDatasetMeasure` was used to estimate the
        distribution the method returns an array. In that case `x` can be
        a scalar value or an array of a matching shape.
        """
        return _pvalue(x, self.cdf, self._tail)



class MCNullDist(NullDist):
    """Null-hypothesis distribution is estimated from randomly permuted data labels.

    The distribution is estimated by calling fit() with an appropriate
    `DatasetMeasure` or `TransferError` instance and a training and a
    validation dataset (in case of a `TransferError`). For a customizable
    amount of cycles the training data labels are permuted and the
    corresponding measure computed. In case of a `TransferError` this is the
    error when predicting the *correct* labels of the validation dataset.

    The distribution can be queried using the `cdf()` method, which can be
    configured to report probabilities/frequencies from `left` or `right` tail,
    i.e. fraction of the distribution that is lower or larger than some
    critical value.

    This class also supports `FeaturewiseDatasetMeasure`. In that case `cdf()`
    returns an array of featurewise probabilities/frequencies.
    """

    _DEV_DOC = """
    TODO automagically decide on the number of samples/permutations needed
    Caution should be paid though since resultant distributions might be
    quite far from some conventional ones (e.g. Normal) -- it is expected to
    them to be bimodal (or actually multimodal) in many scenarios.
    """

    dist_samples = StateVariable(enabled=False,
                                 doc='Samples obtained for each permutation')

    def __init__(self, dist_class=Nonparametric, permutations=100, **kwargs):
        """Initialize Monte-Carlo Permutation Null-hypothesis testing

        :Parameter:
          dist_class: class
            This can be any class which provides parameters estimate
            using `fit()` method to initialize the instance, and
            provides `cdf(x)` method for estimating value of x in CDF.
            All distributions from SciPy's 'stats' module can be used.
          permutations: int
            This many permutations of label will be performed to
            determine the distribution under the null hypothesis.
        """
        NullDist.__init__(self, **kwargs)

        self._dist_class = dist_class
        self._dist = []                 # actual distributions

        self.__permutations = permutations
        """Number of permutations to compute the estimate the null
        distribution."""



    def fit(self, measure, wdata, vdata=None):
        """Fit the distribution by performing multiple cycles which repeatedly
        permuted labels in the training dataset.

        :Parameter:
          measure: (`Featurewise`)`DatasetMeasure` | `TransferError`
            TransferError instance used to compute all errors.
          wdata: `Dataset` which gets permuted and used to compute the
            measure/transfer error multiple times.
          vdata: `Dataset` used for validation.
            If provided measure is assumed to be a `TransferError` and
            working and validation dataset are passed onto it.
        """
        dist_samples = []
        """Holds the values for randomized labels."""

        # decide on the arguments to measure
        if not vdata is None:
            measure_args = [vdata, wdata]
        else:
            measure_args = [wdata]

        # estimate null-distribution
        for p in xrange(self.__permutations):
            # new permutation all the time
            # but only permute the training data and keep the testdata constant
            #
            # TODO this really needs to be more clever! If data samples are
            # shuffled within a class it really makes no difference for the
            # classifier, hence the number of permutations to estimate the
            # null-distribution of transfer errors can be reduced dramatically
            # when the *right* permutations (the ones that matter) are done.
            wdata.permuteLabels(True, perchunk=False)

            # compute and store the measure of this permutation
            # assume it has `TransferError` interface
            dist_samples.append(measure(*measure_args))

        # restore original labels
        wdata.permuteLabels(False, perchunk=False)

        # store samples
        self.dist_samples = dist_samples = N.asarray(dist_samples)

        # fit distribution per each element

        # to decide either it was done on scalars or vectors
        shape = dist_samples.shape
        nshape = len(shape)
        # if just 1 dim, original data was scalar, just create an
        # artif dimension for it
        if nshape == 1:
            dist_samples = dist_samples[:, N.newaxis]

        # fit per each element.
        # XXX could be more elegant? may be use N.vectorize?
        dist_samples_rs = dist_samples.reshape((shape[0], -1))
        dist = []
        for samples in dist_samples_rs.T:
            params = self._dist_class.fit(samples)
            if __debug__ and 'STAT' in debug.active:
                debug('STAT', 'Estimated parameters for the %s are %s'
                      % (self._dist_class, str(params)))
            dist.append(self._dist_class(*params))
        self._dist = dist


    def cdf(self, x):
        """Return value of the cumulative distribution function at `x`.
        """
        if self._dist is None:
            # XXX We might not want to descriminate that way since
            # usually generators also have .cdf where they rely on the
            # default parameters. But then what about Nonparametric
            raise RuntimeError, "Distribution has to be fit first"

        is_scalar = N.isscalar(x)
        if is_scalar:
            x = [x]

        # assure x is a 1D array now
        x = N.asanyarray(x).reshape((-1,))

        if len(self._dist) != len(x):
            raise ValueError, 'Distribution was fit for structure with %d' \
                  ' elements, whenever now queried with %d elements' \
                  % (len(self._dist), len(x))

        # extract cdf values per each element
        cdfs = [ dist.cdf(v) for v, dist in zip(x, self._dist) ]
        return N.array(cdfs)


    def clean(self):
        """Clean stored distributions

        Storing all of the distributions might be too expensive
        (e.g. in case of Nonparametric), and the scope of the object
        might be too broad to wait for it to be destroyed. Clean would
        bind dist_samples to empty list to let gc revoke the memory.
        """
        self._dist = []



class FixedNullDist(NullDist):
    """Proxy/Adaptor class for SciPy distributions.

    All distributions from SciPy's 'stats' module can be used with this class.

    >>> import numpy as N
    >>> from scipy import stats
    >>> from mvpa.clfs.stats import FixedNullDist
    >>>
    >>> dist = FixedNullDist(stats.norm(loc=2, scale=4))
    >>> dist.p(2)
    0.5
    >>>
    >>> dist.cdf(N.arange(5))
    array([ 0.30853754,  0.40129367,  0.5       ,  0.59870633,  0.69146246])
    >>>
    >>> dist = FixedNullDist(stats.norm(loc=2, scale=4), tail='right')
    >>> dist.p(N.arange(5))
    array([ 0.69146246,  0.59870633,  0.5       ,  0.40129367,  0.30853754])
    """
    def __init__(self, dist, **kwargs):
        """
        :Parameter:
          dist: distribution object
            This can be any object the has a `cdf()` method to report the
            cumulative distribition function values.
        """
        NullDist.__init__(self, **kwargs)

        self._dist = dist


    def fit(self, measure, wdata, vdata=None):
        """Does nothing since the distribution is already fixed."""
        pass


    def cdf(self, x):
        """Return value of the cumulative distribution function at `x`.
        """
        return self._dist.cdf(x)

if externals.exists('scipy'):
    import scipy.stats
    from scipy.stats import kstest
    """
    Thoughts:

    So we can use `scipy.stats.kstest` (Kolmogorov-Smirnov test) to
    check/reject H0 that samples come from a given distribution. But
    since it is based on a full range of data, we might better of with
    some ad-hoc checking by the detection power of the values in the
    tail of a tentative distribution.

    """

    def matchDistribution(data, test='kstest', distributions=None,
                          **kwargs):
        """Determine best matching distribution.

        Can be used for 'smelling' the data, as well to choose a
        parametric distribution for data obtained from non-parametric
        testing (e.g. `MCNullDist`).

        WiP: use with caution, API might change

        :Parameters:
          data : N.ndarray
            Array of the data for which to deduce the distribution. It has
            to be sufficiently large to make a reliable conclusion
          test : basestring
            What kind of testing to do. Choices:
             'p-roc' : detection power for a given ROC. Needs two
               parameters: `p=0.05` and `tail='any'`
             'kstest' : 'full-body' distribution comparison. The best
               choice is made by minimal reported distance after estimating
               parameters of the distribution. Parameter `p=0.05` sets
               threshold to reject null-hypothesis that distribution is the
               same
          distributions : None or list of basestring
            Distributions to check. If None, all known in scipy.stats are
            tested.
          **kwargs
            Additional arguments which are needed for each particular test
            (see above)
        """

        # Handle parameters
        _KNOWN_TESTS = ['p-roc', 'kstest']
        if not test in _KNOWN_TESTS:
            raise ValueError, 'Unknown kind of test %s. Known are %s' \
                  % (test, _KNOWN_TESTS)

        p_thr = kwargs.get('p', 0.05)
        if test == 'p-roc':
            tail = kwargs.get('tail', 'any')
            data = N.ravel(data)
            data_p = _pvalue(data, Nonparametric(data).cdf, tail)
            data_p_thr = data_p <= p_thr
            true_positives = N.sum(data_p_thr)
            if true_positives == 0:
                raise ValueError, "Provided data has no elements in non-" \
                      "parametric distribution under p<=%.3f. Please " \
                      "increase the size of data or value of p" % p
            if __debug__:
                debug('STAT_', 'Number of positives in non-parametric '
                      'distribution is %d' % true_positives)

        if distributions is None:
            distributions = scipy.stats.distributions.__all__
        results = []
        for d in distributions:
            # perform actions which might puke for some distributions
            try:
                dist_gen = getattr(scipy.stats, d)
                dist_params = dist_gen.fit(data)
                if __debug__:
                    debug('STAT__', 'Got distribution parameters %s for %s' % (dist_params, d))
                if test == 'p-roc':
                    cdf_func = lambda x: dist_gen.cdf(x, *dist_params)
                    # We need to compare detection under given p
                    cdf_p = _pvalue(data, cdf_func, tail)
                    cdf_p_thr = cdf_p <= p_thr
                    D, p = N.sum(N.abs(data_p_thr - cdf_p_thr))*1.0/true_positives, 1
                    if __debug__: res_sum = 'D=%.2f' % D
                elif test == 'kstest':
                    D, p = kstest(data, d, args=dist_params)
                    if __debug__: res_sum = 'D=%.3f p=%.3f' % (D, p)
            except:
                if __debug__:
                    debug('STAT__', 'Testing for %s distribution failed' % d)
                continue

            if p > p_thr and not N.isnan(D):
                results += [ (D, d, dist_params) ]
                if __debug__:
                    debug('STAT_', 'Testing for %s dist.: %s' % (d, res_sum))
            else:
                if __debug__:
                    debug('STAT__', 'Cannot consider %s dist. with %s'
                          % (d, res_sum))
                continue

        # sort in ascending order, so smaller is better
        results.sort()

        if __debug__ and 'STAT' in debug.active:
            # find the best and report it
            nresults = len(results)
            sresult = lambda r:'%s(%s)=%.2f' % (r[1], ', '.join(map(str, r[2])), r[0])
            if nresults>0:
                nnextbest = min(2, nresults-1)
                snextbest = ', '.join(map(sresult, results[1:1+nnextbest]))
                debug('STAT', 'Best distribution %s. Next best: %s'
                          % (sresult(results[0]), snextbest))
            else:
                debug('STAT', 'Could not find suitable distribution')

        # return all the results
        return results

