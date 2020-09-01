import unittest

if __name__ == '__main__':
    test_suite = unittest.TestLoader().discover('functional')
    unittest.TextTestRunner().run(test_suite)
