import unittest
import pytest
from pandas.testing import assert_series_equal, assert_frame_equal
from numpy.testing import assert_array_equal
# Below are needed for setting up tests
from sam.preprocessing import complete_timestamps
import pandas as pd
import numpy as np


class TestCompleteTimestamps(unittest.TestCase):

    def test_complete_timestamps(self):
        data = pd.DataFrame({
            "TIME": pd.to_datetime(['2018/01/01 15:45:09',
                                    '2018/01/01 16:03:09',
                                    '2018/01/01 16:10:09',
                                    '2018/01/01 16:22:09']),
            "ID": 1,
            "VALUE": [1, 2, 3, 4]
        }, columns=['TIME', 'ID', 'VALUE'])
        start_time = pd.to_datetime("2018/01/01 15:45:00")
        end_time = pd.to_datetime("2018/01/01 16:30:00")

        result = complete_timestamps(data, '15min', start_time, end_time)

        # Values are matched to their first left side matching time,
        # so the last value is np.NaN
        output = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:00', '2018/01/01 16:00:00',
                 '2018/01/01 16:15:00', '2018/01/01 16:30:00']),
            "ID": 1,
            "VALUE": [1, 2.5, 4, np.NaN]
        }, columns=['TIME', 'ID', 'VALUE'])
        assert_frame_equal(result, output)

    def test_fillna_method(self):
        data = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:09', '2018/01/01 16:03:09',
                 '2018/01/01 16:10:09', '2018/01/01 16:22:09']),
            "ID": 1,
            "VALUE": [1, 2, 3, 4]
        }, columns=['TIME', 'ID', 'VALUE'])
        start_time = pd.to_datetime("2018/01/01 15:45:00")
        end_time = pd.to_datetime("2018/01/01 16:30:00")

        # after ffill, the nan is filled in
        output = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:00', '2018/01/01 16:00:00',
                 '2018/01/01 16:15:00', '2018/01/01 16:30:00']),
            "ID": 1,
            "VALUE": [1, 2.5, 4, 4]
        }, columns=['TIME', 'ID', 'VALUE'])

        result = complete_timestamps(data,
                                     '15min',
                                     start_time,
                                     end_time,
                                     fillna_method='ffill')
        assert_frame_equal(result, output)

    def test_agg_method(self):
        # When using the sum, the sum of values 2 and 3 are taken within
        # the block 16:00 - 16:15 are taken

        data = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:09', '2018/01/01 16:03:09',
                 '2018/01/01 16:10:09', '2018/01/01 16:22:09']),
            "ID": 1,
            "VALUE": [1, 2, 3, 4]
        }, columns=['TIME', 'ID', 'VALUE'])
        start_time = pd.to_datetime("2018/01/01 15:45:00")
        end_time = pd.to_datetime("2018/01/01 16:30:00")

        # after ffill, the nan is filled in
        output = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:00', '2018/01/01 16:00:00',
                 '2018/01/01 16:15:00', '2018/01/01 16:30:00']),
            "ID": 1,
            "VALUE": [1, 5, 4, np.NaN]
        }, columns=['TIME', 'ID', 'VALUE'])

        result = complete_timestamps(data, '15min', start_time, end_time,
                                     aggregate_method='sum')
        output.equals(result)

    def test_empty_start_end_time(self):
        data = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:09', '2018/01/01 16:03:09',
                 '2018/01/01 16:10:09', '2018/01/01 16:22:09']),
            "ID": 1,
            "VALUE": [1, 2, 3, 4]
        }, columns=['TIME', 'ID', 'VALUE'])

        result = complete_timestamps(data, '15min', start_time='', end_time='')
        output = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:00', '2018/01/01 16:00:00',
                 '2018/01/01 16:15:00']),
            "ID": 1,
            "VALUE": [1, 2.5, 4]
        }, columns=['TIME', 'ID', 'VALUE'])
        assert_frame_equal(result, output)

    def test_multiple_ids(self):
        data = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:09', '2018/01/01 16:03:09',
                 '2018/01/01 15:45:09', '2018/01/01 16:22:09']),
            "ID": [1, 1, 2, 2],
            "VALUE": [1, 2, 3, 4]
        }, columns=['TIME', 'ID', 'VALUE'])
        start_time = pd.to_datetime("2018/01/01 15:45:00")
        end_time = pd.to_datetime("2018/01/01 16:15:00")

        result = complete_timestamps(data, '15min', start_time, end_time)

        output = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:00', '2018/01/01 15:45:00',
                 '2018/01/01 16:00:00', '2018/01/01 16:00:00',
                 '2018/01/01 16:15:00', '2018/01/01 16:15:00']),
            "ID": [1, 2, 1, 2, 1, 2],
            "VALUE": [1.0, 3.0, 2.0, np.NaN, np.NaN, 4.0]
        }, columns=['TIME', 'ID', 'VALUE'])
        assert_frame_equal(result, output)

    def test_multiple_ids_fillna_method(self):
        data = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:09', '2018/01/01 16:03:09',
                 '2018/01/01 15:45:09', '2018/01/01 16:22:09']),
            "ID": [1, 1, 2, 2],
            "VALUE": [1, 2, 3, 4]
        }, columns=['TIME', 'ID', 'VALUE'])
        start_time = pd.to_datetime("2018/01/01 15:45:00")
        end_time = pd.to_datetime("2018/01/01 16:15:00")

        result = complete_timestamps(data,
                                     '15min',
                                     start_time,
                                     end_time,
                                     fillna_method='ffill'
                                     )

        output = pd.DataFrame({
            "TIME": pd.to_datetime(
                ['2018/01/01 15:45:00', '2018/01/01 15:45:00',
                 '2018/01/01 16:00:00', '2018/01/01 16:00:00',
                 '2018/01/01 16:15:00', '2018/01/01 16:15:00']),
            "ID": [1, 2, 1, 2, 1, 2],
            "VALUE": [1.0, 3.0, 2.0, 3.0, 2.0, 4.0]
        }, columns=['TIME', 'ID', 'VALUE'])
        assert_frame_equal(result, output)

    def test_incorrect_input(self):
        data = pd.DataFrame({
            "TIME": pd.to_datetime(['2018/01/01 15:45:09', '2018/01/01 16:03:09',
                                    '2018/01/01 16:10:09', '2018/01/01 16:22:09']),
            "ID": 1,
            "VALUE": [1, 2, 3, 4]
        }, columns=['TIME', 'ID', 'VALUE'])
        start_time = pd.to_datetime("2018/01/01 15:45:00")
        end_time = pd.to_datetime("2018/01/01 16:30:00")

        # half uur is invalid timeunit
        self.assertRaises(ValueError,
                          complete_timestamps,
                          data,
                          'half uur',
                          start_time,
                          end_time)
        # wrong is not a time
        # integers are actually allowed, they are interpreted as UNIX time
        self.assertRaises(ValueError,
                          complete_timestamps,
                          data,
                          '15min',
                          'wrong',
                          end_time)

        data.columns = ["TIME", "ID", "SOMETHINGELSE"]
        self.assertRaises(Exception, complete_timestamps,
                          data, '15min', start_time, end_time, 'sum')

        self.assertRaises(Exception, complete_timestamps, data, '15min',
                          start_time, end_time, 'unknown_fun', '')
        self.assertRaises(Exception, complete_timestamps, data, '15min',
                          start_time, end_time, '', 'unknown_fun')


if __name__ == '__main__':
    unittest.main()
