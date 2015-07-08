from __future__ import print_function, division
from nose.tools import eq_, raises

from proccer.common import parse_interval


def test_int_interval():
    got = parse_interval(1)
    eq_(got.total_seconds(), 1)


def test_str_interval():
    got = parse_interval('1 hours')
    eq_(got.total_seconds(), 3600)


@raises(ValueError)
def test_bad_interval():
    parse_interval('1s')
