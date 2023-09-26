# coding: utf-8


__all__ = ["UtilTest"]


import unittest

from order.util import create_hash


class UtilTest(unittest.TestCase):

    def test_create_hash(self):
        data = (1, "2", True, (42,))

        # test different variations
        self.assertEqual(create_hash(data), "6c98c78722")
        self.assertEqual(create_hash(data, algo="sha512"), "75bd8c75c8")
        self.assertEqual(create_hash(data, l=12), "6c98c7872207")
        self.assertEqual(create_hash(data, to_int=True), 466419681058)
