# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
'''Unit tests for basic constraints functionality.'''


from mvpa2.testing import *
import unittest

from mvpa2.base.constraints import * 

class SimpleConstraintsTests(unittest.TestCase):

    def test_int(self):
        c = EnsureInt()
        # this should always work
        assert_equal(c(7), 7)
        assert_equal(c(7.0), 7)
        assert_equal(c('7'), 7)
        assert_equal(c([7,3]), [7,3])
        # this should always fail
        self.assertRaises(ValueError, lambda: c('fail'))
        self.assertRaises(ValueError, lambda: c([3, 'fail']))
        # this will also fail
        self.assertRaises(ValueError, lambda: c('17.0'))

    def test_float(self):
        c = EnsureFloat()
        # this should always work
        assert_equal(c(7.0), 7.0)
        assert_equal(c(7), 7.0)
        assert_equal(c('7'), 7.0)
        assert_equal(c([7.0,'3.0']), [7.0,3.0])
        # this should always fail
        self.assertRaises(ValueError, lambda: c('fail'))
        self.assertRaises(ValueError, lambda: c([3.0, 'fail']))

    def test_bool(self):
        c = EnsureBool()
        # this should always work
        assert_equal(c(True), True)
        assert_equal(c(False), False)
        # all that resuls in True
        assert_equal(c('true'), True)
        assert_equal(c('1'), True)
        assert_equal(c('yes'), True)
        assert_equal(c('on'), True)
        assert_equal(c('enable'), True)
        # all that resuls in False
        assert_equal(c('false'), False)
        assert_equal(c('0'), False)
        assert_equal(c('no'), False)
        assert_equal(c('off'), False)
        assert_equal(c('disable'), False)
        # this should always fail
        self.assertRaises(ValueError, lambda: c('True'))
        self.assertRaises(ValueError, lambda: c('False'))
        self.assertRaises(ValueError, lambda: c(0))
        self.assertRaises(ValueError, lambda: c(1))
        
    def test_str(self):
        c = EnsureStr()
        # this should always work
        assert_equal(c('hello'), 'hello')
        assert_equal(c('7.0'), '7.0')
        # this should always fail        
        self.assertRaises(ValueError, lambda: c(['ab']))
        self.assertRaises(ValueError, lambda: c(['a', 'b']))
        self.assertRaises(ValueError, lambda: c(('a', 'b')))
        # no automatic conversion attempted
        self.assertRaises(ValueError, lambda: c(7.0))         

    def test_none(self):
        c = EnsureNone()
        # this should always work
        assert_equal(c(None), None)
        # this should always fail
        self.assertRaises(ValueError, lambda: c('None'))
        self.assertRaises(ValueError, lambda: c([]))

    def test_choice(self):
        c = EnsureChoice('choice1', 'choice2', None)
        # this should always work
        assert_equal(c('choice1'), 'choice1')
        assert_equal(c(None), None)
        # this should always fail        
        self.assertRaises(ValueError, lambda: c('fail'))
        self.assertRaises(ValueError, lambda: c('None'))

    def test_range(self):
        c = EnsureRange(min=3, max=7)
        # this should always work
        assert_equal(c(3.0), 3.0)
        # this should always fail
        self.assertRaises(ValueError, lambda: c(2.9999999))
        self.assertRaises(ValueError, lambda: c(77))
        self.assertRaises(ValueError, lambda: c('fail'))
        self.assertRaises(ValueError, lambda: c((3,4)))
        # since no type checks are performed
        self.assertRaises(ValueError, lambda: c('7'))
        

class ComplexConstraintsTests(unittest.TestCase):
    
    def test_constraints(self):
        # this should always work
        c = Constraints(EnsureFloat())
        assert_equal(c(7.0), 7.0)
        c = Constraints(EnsureFloat(), EnsureRange(min=4.0))
        assert_equal(c(7.0), 7.0)
        c = Constraints(EnsureFloat(), EnsureRange(min=4), EnsureRange(max=9))
        assert_equal(c(7.0), 7.0)
        # this should always fail
        c = Constraints(EnsureFloat(), EnsureRange(max=4), EnsureRange(min=9))
        self.assertRaises(ValueError, lambda: c(1.0))
        
    def test_altconstraints(self):
        # this should always work
        c = AltConstraints(EnsureFloat())
        assert_equal(c(7.0), 7.0)
        c = AltConstraints(EnsureFloat(), EnsureNone())
        assert_equal(c(7.0), 7.0)
        assert_equal(c(None), None)
        # this should always fail
        c = Constraints(EnsureRange(min=0, max=4), EnsureRange(min=9, max=11))
        self.assertRaises(ValueError, lambda: c(7.0))
        
    def test_both(self):
        # this should always work
        c= AltConstraints(Constraints(EnsureFloat(),\
                                      EnsureRange(min=7.0,max=44.0)),\
                                      EnsureNone())
        assert_equal(c(7.0), 7.0)
        assert_equal(c(None), None)
        # this should always fail
        self.assertRaises(ValueError, lambda: c(77.0))              
                                     
        
        

if __name__ == '__main__':  # pragma: no cover
    import runner
    runner.run()
    

