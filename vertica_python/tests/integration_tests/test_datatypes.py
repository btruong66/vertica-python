# Copyright (c) 2018-2023 Open Text.
# Copyright (c) 2018 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Copyright (c) 2013-2017 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import print_function, division, absolute_import

from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzoffset
from decimal import Decimal
from math import isnan
from uuid import UUID

from .base import VerticaPythonIntegrationTestCase


class TypeTestCase(VerticaPythonIntegrationTestCase):
    def test_decimal_query(self):
        value = Decimal(0.42)
        query = "SELECT {0}::numeric".format(value)
        res = self._query_and_fetchone(query)
        self.assertAlmostEqual(res[0], value)

    def test_boolean_query__true(self):
        value = True
        query = "SELECT {0}::boolean".format(value)
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], value)

    def test_boolean_query__false(self):
        value = False
        query = "SELECT {0}::boolean".format(value)
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], value)

    def test_uuid_query(self):
        self.require_protocol_at_least(3 << 16 | 8)
        value = UUID('00010203-0405-0607-0809-0a0b0c0d0e0f')
        query = "SELECT '{0}'::uuid".format(value)
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], value)


exec(TypeTestCase.createPrepStmtClass())

class InsertComplexTypeTestCase(VerticaPythonIntegrationTestCase):
    """
    Python objects (list, set, dict) convert to SQL literal (ARRAY, SET, ROW)
    Only for client-side bindings (use_prepared_statements=False)
    """
    def setUp(self):
        super(InsertComplexTypeTestCase, self).setUp()
        self.require_protocol_at_least(3 << 16 | 12)
        self._table = 'insert_complex_types_test'

    def tearDown(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"DROP TABLE IF EXISTS {self._table}")
        super(InsertComplexTypeTestCase, self).tearDown()

    def _test_insert_complex_type(self, col_type, values, expected=None):
        if expected is None:
            expected = values
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"DROP TABLE IF EXISTS {self._table}")
            cur.execute(f"CREATE TABLE {self._table} (a INT, b {col_type})")
            a = 1
            for value in values:
                # Some cases need explicit typecasting
                cur.execute(f"INSERT INTO {self._table} (a, b) VALUES (%s, %s::{col_type})", [a, value], use_prepared_statements=False)
                a += 1
            rows = cur.execute(f"SELECT b FROM {self._table} ORDER BY a").fetchall()
            results = [row[0] for row in rows]
            self.assertEqual(results, expected)

    #######################
    # tests for ARRAY type
    #######################
    def test_Array_boolean_type(self):
        self._test_insert_complex_type('ARRAY[BOOL]', [[True, False, None], None, [], [None]])

    def test_Array_integer_type(self):
        self._test_insert_complex_type('ARRAY[INT]', [[1,-2,3], [4,None,5], None, [], [None]])
        self._test_insert_complex_type('ARRAY[ARRAY[INT]]', [[[1,2], [3,4], None, [5,None], []],
            None, [], [None]])
        self._test_insert_complex_type('ARRAY[ARRAY[ARRAY[ARRAY[INT]]]]', [[[[None,[1,2,3],None,[1,None,3],[None,None,None],[4,5],[],None]]],
            None, [], [None]])

    def test_Array_float_type(self):
        self._test_insert_complex_type('ARRAY[FLOAT]', [[1.23456e-18,float('Inf'),float('-Inf'),None,-1.234,0.0], None, [], [None]])

    def test_Array_numeric_type(self):
        self._test_insert_complex_type('ARRAY[NUMERIC]', [[Decimal('-1.1200000000'), Decimal('0E-10'), None, Decimal('1234567890123456789.0123456789')],
            None, [], [None]])

    def test_Array_char_type(self):
        self._test_insert_complex_type('ARRAY[CHAR(3)]', [['a', u'\u16b1', None, 'foo'], None, [], [None]], [['a  ', u'\u16b1', None, 'foo'], None, [], [None]])

    def test_Array_varchar_type(self):
        self._test_insert_complex_type('ARRAY[VARCHAR(10)]', [['', u'\u16b1\nb', None, 'foo'], None, [], [None]])

    def test_Array_date_type(self):
        self._test_insert_complex_type('ARRAY[DATE]', [[date(2021, 6, 10),None,date(221, 5, 2)], None, [], [None]])

    def test_Array_time_type(self):
        self._test_insert_complex_type('ARRAY[TIME(3)]', [[time(0, 0, 0),None,time(22, 36, 33, 124000)], None, [], [None]])

    def test_Array_timetz_type(self):
        self._test_insert_complex_type('ARRAY[TIMETZ(3)]', [[time(22, 36, 33, 123000, tzinfo=tzoffset(None, 23400)),None,
            time(22, 36, 33, 123000, tzinfo=tzoffset(None, -10800))], None, [], [None]])

    def test_Array_timestamp_type(self):
        self._test_insert_complex_type('ARRAY[TIMESTAMP]', [[datetime(276, 12, 1, 11, 22, 33),None,datetime(2001, 12, 1, 0, 30, 45, 87000)], None, [], [None]])

    def test_Array_timestamptz_type(self):
        self._test_insert_complex_type('ARRAY[TIMESTAMPTZ]', [[datetime(276, 11, 30, 23, 32, 57, tzinfo=tzoffset(None, 3600)),None,datetime(2001, 12, 1, 0, 30, 45, 87000, tzinfo=tzoffset(None, -18000))], None, [], [None]])

    def test_Array_UUID_type(self):
        self._test_insert_complex_type('ARRAY[UUID]', [[UUID('00010203-0405-0607-0809-0a0b0c0d0e0f'),None,UUID('123e4567-e89b-12d3-a456-426655440a00')], None, [], [None]])

    #####################
    # tests for SET type
    #####################
    def test_1DSet_boolean_type(self):
        self._test_insert_complex_type('SET[BOOL]', [{True, False, None}, None, set(), {None}])

    def test_1DSet_integer_type(self):
        self._test_insert_complex_type('SET[INT]', [{0, 1, -2, 3, None}, None, set(), {None}])

    def test_1DSet_float_type(self):
        self._test_insert_complex_type('SET[FLOAT]', [{float('Inf'), float('-Inf'), None, -1.234, 0.0, 1.23456e-18}, None, set(), {None}])

    def test_1DSet_numeric_type(self):
        self._test_insert_complex_type('SET[NUMERIC]', [{Decimal('-1.12'), Decimal('0E-15'), None, Decimal('1234567890123456789.0123456789')},
            None, set(), {None}])

    def test_1DSet_char_type(self):
        self._test_insert_complex_type('SET[CHAR(3)]', [{'a  ', u'\u16b1', None, 'foo'}, None, set(), {None}])

    def test_1DSet_varchar_type(self):
        self._test_insert_complex_type('SET[VARCHAR(10)]', [{'', u'\u16b1\nb', None, 'foo'}, None, set(), {None}])

    def test_1DSet_date_type(self):
        self._test_insert_complex_type('SET[DATE]', [{date(2021, 6, 10), None, date(221, 5, 2)}, None, set(), {None}])

    def test_1DSet_time_type(self):
        self._test_insert_complex_type('SET[TIME(3)]', [{time(0, 0, 0), None, time(22, 36, 33, 124000)}, None, set(), {None}])

    def test_1DSet_timetz_type(self):
        self._test_insert_complex_type('SET[TIMETZ(3)]', [{time(22, 36, 33, 123000, tzinfo=tzoffset(None, 23400)),None,
            time(22, 36, 33, 123000, tzinfo=tzoffset(None, -10800))}, None, set(), {None}])

    def test_1DSet_timestamp_type(self):
        self._test_insert_complex_type('SET[TIMESTAMP]', [{datetime(276, 12, 1, 11, 22, 33),None,datetime(2001, 12, 1, 0, 30, 45, 87000)}, None, set(), {None}])

    def test_1DSet_timestamptz_type(self):
        self._test_insert_complex_type('SET[TIMESTAMPTZ]', [{datetime(276, 11, 30, 23, 32, 57, tzinfo=tzoffset(None, 3600)),None,
            datetime(2001, 12, 1, 0, 30, 45, 87000, tzinfo=tzoffset(None, -18000))}, None, set(), {None}])

    def test_1DSet_UUID_type(self):
        self._test_insert_complex_type('SET[UUID]', [{UUID('00010203-0405-0607-0809-0a0b0c0d0e0f'),None,UUID('123e4567-e89b-12d3-a456-426655440a00')}, None, set(), {None}])

    #####################
    # tests for ROW type
    #####################
    def test_row_boolean_type(self):
        self._test_insert_complex_type('ROW(BOOL, ARRAY[BOOL], ROW(BOOL, ARRAY[BOOL]))', [
                {'f0': True, 'f1': [None, False], 'f2': {'f0': False, 'f1': [True, None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_integer_type(self):
        self._test_insert_complex_type('ROW(INT, ARRAY[INT], ROW(INT, ARRAY[INT]))', [
                {'f0': -10, 'f1': [None, 1, 2], 'f2': {'f0': 90, 'f1': [0, None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
                {'f0': 5, 'f1': [], 'f2': None},
            ])

    def test_row_float_type(self):
        self._test_insert_complex_type('ROW(FLOAT, ARRAY[FLOAT], ROW(FLOAT, ARRAY[FLOAT]))', [
                {'f0': 0.0, 'f1': [None, 1.23456e-18], 'f2': {'f0': float('-Inf'), 'f1': [-1.2, None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_numeric_type(self):
        self._test_insert_complex_type('ROW(NUMERIC, ARRAY[NUMERIC], ROW(NUMERIC, ARRAY[NUMERIC]))', [
                {'f0': Decimal('-1.12'), 'f1': [None, Decimal('0E-15')], 'f2': {'f0': Decimal('1234567890123456789.0123456789'), 'f1': [Decimal(10), None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_char_type(self):
        self._test_insert_complex_type('ROW(CHAR(3), ARRAY[CHAR(3)], ROW(CHAR(3), ARRAY[CHAR(3)]))', [
                {'f0': 'a  ', 'f1': [None, 'foo'], 'f2': {'f0': '\u16b1', 'f1': [' b ', None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_varchar_type(self):
        self._test_insert_complex_type('ROW(VARCHAR, ARRAY[VARCHAR], ROW(VARCHAR, ARRAY[VARCHAR]))', [
                {'f0': 'a', 'f1': [None, 'foo'], 'f2': {'f0': '\u16b1\nb', 'f1': ['', None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_date_type(self):
        self._test_insert_complex_type('ROW(DATE, ARRAY[DATE], ROW(DATE, ARRAY[DATE]))', [
                {'f0': date(2021, 6, 10), 'f1': [None, date(2021, 6, 11)], 'f2': {'f0': date(221, 5, 2), 'f1': [date(2023, 1, 1), None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_time_type(self):
        self._test_insert_complex_type('ROW(TIME(3), ARRAY[TIME(3)], ROW(TIME(3), ARRAY[TIME(3)]))', [
                {'f0': time(0, 0, 0), 'f1': [None, time(8, 30, 10)], 'f2': {'f0': time(22, 36, 33, 124000), 'f1': [time(0, 0, 0, 500000), None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_timetz_type(self):
        self._test_insert_complex_type('ROW(TIMETZ(3), ARRAY[TIMETZ], ROW(TIMETZ, ARRAY[TIMETZ(3)]))', [
                {'f0': time(22, 36, 33, 123000, tzinfo=tzoffset(None, 23400)), 'f1': [None, time(8, 30, 10, tzinfo=tzoffset(None, -23400))],
                 'f2': {'f0': time(22, 36, 33, 123000, tzinfo=tzoffset(None, -10800)), 'f1': [time(0, 0, tzinfo=tzoffset(None, 10800)), None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_timestamp_type(self):
        self._test_insert_complex_type('ROW(TIMESTAMP, ARRAY[TIMESTAMP], ROW(TIMESTAMP, ARRAY[TIMESTAMP]))', [
                {'f0': datetime(276, 12, 1, 11, 22, 33), 'f1': [None, datetime(2001, 12, 1, 0, 30, 45, 87000)],
                 'f2': {'f0': datetime(2023, 12, 1, 11, 30, 45, 87000), 'f1': [datetime(1998, 12, 1, 11, 22, 33), None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_timestamptz_type(self):
        self._test_insert_complex_type('ROW(TIMESTAMPTZ, ARRAY[TIMESTAMPTZ], ROW(TIMESTAMPTZ, ARRAY[TIMESTAMPTZ]))', [
                {'f0': datetime(276, 11, 30, 23, 32, 57, tzinfo=tzoffset(None, 23400)),
                 'f1': [None, datetime(2001, 12, 1, 0, 30, 45, 87000, tzinfo=tzoffset(None, -18000))],
                 'f2': {'f0':  datetime(2011, 12, 1, 0, 30, 45, 57000, tzinfo=tzoffset(None, 18000)),
                        'f1': [datetime(2023, 12, 1, 11, 30, 45, tzinfo=tzoffset(None, -23400)), None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])

    def test_row_UUID_type(self):
        self._test_insert_complex_type('ROW(UUID, ARRAY[UUID], ROW(UUID, ARRAY[UUID]))', [
                {'f0': UUID('00010203-0405-0607-0809-0a0b0c0d0e0f'), 'f1': [None, UUID('123e4567-e89b-12d3-a456-426655440a00')],
                 'f2': {'f0': UUID('123e4567-e89b-12d3-a456-426655440a00'), 'f1': [UUID('00010203-0405-0607-0809-0a0b0c0d0e0f'), None]}},
                {'f0': None, 'f1': [None], 'f2': {'f0': None, 'f1': []}},
            ])


class ComplexTypeTestCase(VerticaPythonIntegrationTestCase):
    """
    SQL data types (ARRAY, SET, ROW) convert to Python objects (list, set, dict)
    """
    def setUp(self):
        super(ComplexTypeTestCase, self).setUp()
        self.require_protocol_at_least(3 << 16 | 12)

    ######################################################
    # tests for connection option 'request_complex_types'
    ######################################################
    def test_connection_option(self):
        self._conn_info['request_complex_types'] = False
        with self._connect() as conn:
            cur = conn.cursor()
            res = self._query_and_fetchone("SELECT ARRAY[-500, 0, null, 500]::ARRAY[INT]")
            self.assertEqual(res[0], '[-500,0,null,500]')

    #######################
    # tests for ARRAY type
    #######################
    def test_1DArray_boolean_type(self):
        query = "SELECT ARRAY['t', 'f', null]::ARRAY[BOOL], ARRAY[]::ARRAY[BOOL], null::ARRAY[BOOL]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [True, False, None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_integer_type(self):
        query = "SELECT ARRAY[-500, 0, null, 500]::ARRAY[INT], ARRAY[]::ARRAY[INT], null::ARRAY[INT]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [-500, 0, None, 500])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_float_type(self):
        query = ("SELECT ARRAY['Infinity'::float, '-Infinity'::float, null, -1.234, 0, 1.23456e-18]::ARRAY[FLOAT],"
                 " ARRAY[]::ARRAY[FLOAT], null::ARRAY[FLOAT], ARRAY['NaN'::float]::ARRAY[FLOAT]")
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [float('Inf'), float('-Inf'), None, -1.234, 0.0, 1.23456e-18])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)
        self.assertTrue(isnan(res[3][0]))

    def test_1DArray_numeric_type(self):
        query = "SELECT ARRAY[-1.12, 0, null, 1234567890123456789.0123456789]::ARRAY[NUMERIC], ARRAY[]::ARRAY[DECIMAL], null::ARRAY[NUMERIC]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [Decimal('-1.1200000000'), Decimal('0E-10'), None, Decimal('1234567890123456789.0123456789')])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_char_type(self):
        query = u"SELECT ARRAY['a', '\u16b1b', null, 'foo']::ARRAY[CHAR(3)], ARRAY[]::ARRAY[CHAR(4)], null::ARRAY[CHAR(5)]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], ['a  ', u'\u16b1', None, 'foo'])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_varchar_type(self):
        query = u"SELECT ARRAY['', '\u16b1\nb', null, 'foo']::ARRAY[VARCHAR(10),4], ARRAY[]::ARRAY[VARCHAR(4)], null::ARRAY[VARCHAR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], ['', u'\u16b1\nb', None, 'foo'])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_date_type(self):
        query = "SELECT ARRAY['2021-06-10', null, '0221-05-02']::ARRAY[DATE], ARRAY[]::ARRAY[DATE], null::ARRAY[DATE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [date(2021, 6, 10), None, date(221, 5, 2)])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_time_type(self):
        query = "SELECT ARRAY['00:00:00.00', null, '22:36:33.123956']::ARRAY[TIME(3)], ARRAY[]::ARRAY[TIME(4)], null::ARRAY[TIME]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [time(0, 0, 0), None, time(22, 36, 33, 124000)])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_timetz_type(self):
        query = "SELECT ARRAY['22:36:33.12345+0630', null, '800-02-03 22:36:33.123456 America/Cayman']::ARRAY[TIMETZ(3)], ARRAY[]::ARRAY[TIMETZ(4)], null::ARRAY[TIMETZ]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [time(22, 36, 33, 123000, tzinfo=tzoffset(None, 23400)), None, 
                                  time(22, 36, 33, 123000, tzinfo=tzoffset(None, -19176))])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_timestamp_type(self):
        query = "SELECT ARRAY['276-12-1 11:22:33', '2001-12-01 00:30:45.087', null]::ARRAY[TIMESTAMP], ARRAY[]::ARRAY[TIMESTAMP(4)], null::ARRAY[TIMESTAMP]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [datetime(276, 12, 1, 11, 22, 33), datetime(2001, 12, 1, 0, 30, 45, 87000), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_timestamptz_type(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SET TIMEZONE 'America/Cayman'") # set session's time zone
            cur.fetchall()
            query = "SELECT ARRAY['276-12-1 11:22:33+0630', '2001-12-01 00:30:45.087 America/Cayman', null]::ARRAY[TIMESTAMPTZ], ARRAY[]::ARRAY[TIMESTAMPTZ(4)], null::ARRAY[TIMESTAMPTZ]"
            cur.execute(query)
            res = cur.fetchone()
            self.assertEqual(res[0], [datetime(276, 11, 30, 23, 32, 57, tzinfo=tzoffset(None, -19176)),
                                datetime(2001, 12, 1, 0, 30, 45, 87000, tzinfo=tzoffset(None, -18000)), None])
            self.assertEqual(res[1], [])
            self.assertEqual(res[2], None)

    def test_1DArray_interval_type(self):
        query = "SELECT ARRAY['1 02:03:04.0005', '1 02:03:04', '02:03:04.0005', '02:03', null]::ARRAY[INTERVAL DAY TO SECOND], ARRAY[]::ARRAY[INTERVAL DAY TO SECOND], null::ARRAY[INTERVAL DAY TO SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(days=+1, hours=+2, minutes=+3, seconds=+4, microseconds=+500),
                relativedelta(days=+1, hours=+2, minutes=+3, seconds=+4),
                relativedelta(hours=+2, minutes=+3, seconds=+4, microseconds=+500),
                relativedelta(hours=+2, minutes=+3), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['1 02:03', '02:03', null]::ARRAY[INTERVAL DAY TO MINUTE], ARRAY[]::ARRAY[INTERVAL DAY TO MINUTE], null::ARRAY[INTERVAL DAY TO MINUTE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(days=+1, hours=+2, minutes=+3), relativedelta(hours=+2, minutes=+3), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['1 02:03', '6', '02:03', null]::ARRAY[INTERVAL DAY TO HOUR], ARRAY[]::ARRAY[INTERVAL DAY TO HOUR], null::ARRAY[INTERVAL DAY TO HOUR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(days=+1, hours=+2), relativedelta(days=+6), relativedelta(hours=+2), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['123', '-6', null]::ARRAY[INTERVAL DAY], ARRAY[]::ARRAY[INTERVAL DAY], null::ARRAY[INTERVAL DAY]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(days=+123), relativedelta(days=-6), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['02:03:04', '02:03:04.0005', '02:03', null]::ARRAY[INTERVAL HOUR TO SECOND], ARRAY[]::ARRAY[INTERVAL HOUR TO SECOND], null::ARRAY[INTERVAL HOUR TO SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(hours=+2, minutes=+3, seconds=+4),
                relativedelta(hours=+2, minutes=+3, seconds=+4, microseconds=+500),
                relativedelta(hours=+2, minutes=+3), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['02:03:04', '-02:03', null]::ARRAY[INTERVAL HOUR TO MINUTE], ARRAY[]::ARRAY[INTERVAL HOUR TO MINUTE], null::ARRAY[INTERVAL HOUR TO MINUTE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(hours=+2, minutes=+3), relativedelta(hours=-2, minutes=-3), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['32', '-03', null]::ARRAY[INTERVAL HOUR], ARRAY[]::ARRAY[INTERVAL HOUR], null::ARRAY[INTERVAL HOUR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(days=+1, hours=+8), relativedelta(hours=-3), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['00:04.0005', '03:04', null]::ARRAY[INTERVAL MINUTE TO SECOND], ARRAY[]::ARRAY[INTERVAL MINUTE TO SECOND], null::ARRAY[INTERVAL MINUTE TO SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(seconds=+4, microseconds=+500), relativedelta(minutes=+3, seconds=+4), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['03', '-34', null]::ARRAY[INTERVAL MINUTE], ARRAY[]::ARRAY[INTERVAL MINUTE], null::ARRAY[INTERVAL MINUTE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(minutes=+3), relativedelta(minutes=-34), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['216901.024', '216901', null]::ARRAY[INTERVAL SECOND], ARRAY[]::ARRAY[INTERVAL SECOND], null::ARRAY[INTERVAL SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(days=+2, hours=+12, minutes=+15, seconds=+1, microseconds=+24000),
                                  relativedelta(days=+2, hours=+12, minutes=+15, seconds=+1), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_intervalYM_type(self):
        query = "SELECT ARRAY['1y 10m', '1y', '10m ago', null]::ARRAY[INTERVAL YEAR TO MONTH], ARRAY[]::ARRAY[INTERVAL YEAR TO MONTH], null::ARRAY[INTERVAL YEAR TO MONTH]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(years=+1, months=+10), relativedelta(years=+1), relativedelta(months=-10), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['1y ago', '2y', null]::ARRAY[INTERVAL YEAR], ARRAY[]::ARRAY[INTERVAL YEAR], null::ARRAY[INTERVAL YEAR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(years=-1), relativedelta(years=+2), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY['1y 10m', '1y', '10m ago', null]::ARRAY[INTERVAL MONTH], ARRAY[]::ARRAY[INTERVAL MONTH], null::ARRAY[INTERVAL MONTH]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [relativedelta(years=+1, months=+10), relativedelta(years=+1), relativedelta(months=-10), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_UUID_type(self):
        query = "SELECT ARRAY['00010203-0405-0607-0809-0a0b0c0d0e0f', null]::ARRAY[UUID], ARRAY[]::ARRAY[UUID], null::ARRAY[UUID]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [UUID('00010203-0405-0607-0809-0a0b0c0d0e0f'), None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_binary_type(self):
        query = "SELECT ARRAY[hex_to_binary('0x41'), hex_to_binary('0x4243'), null]::ARRAY[BINARY(2)], ARRAY[]::ARRAY[BINARY(4)], null::ARRAY[BINARY]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [b'A\x00', b'BC', None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_1DArray_varbinary_type(self):
        query = "SELECT ARRAY[hex_to_binary('0x41'), hex_to_binary('0x4210'), null]::ARRAY[VARBINARY(2)], ARRAY[]::ARRAY[VARBINARY(4)], null::ARRAY[VARBINARY]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [b'A', b'B\x10', None])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

    def test_Array_dummy_type(self):
        query = "SELECT ARRAY[]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [])

        query = "SELECT ARRAY[ARRAY[]]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [[]])

    def test_NDArray_type(self):
        query = "SELECT ARRAY[ARRAY[1,2],ARRAY[3,4],null,ARRAY[5,null],ARRAY[]]::ARRAY[ARRAY[INT]], ARRAY[]::ARRAY[ARRAY[INT]], null::ARRAY[ARRAY[INT]]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [[1,2], [3,4], None, [5,None], []])
        self.assertEqual(res[1], [])
        self.assertEqual(res[2], None)

        query = "SELECT ARRAY[ARRAY[ARRAY[null,ARRAY[1,2,3],null,ARRAY[1,null,3],ARRAY[null,null,null]::ARRAY[INT],ARRAY[4,5],ARRAY[],null]]]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [[[None,[1,2,3],None,[1,None,3],[None,None,None],[4,5],[],None]]])

        query = "SELECT ARRAY[ARRAY[0.0,0.1,0.2],ARRAY[-1.0,-1.1,-1.2],ARRAY['Infinity'::float, '-Infinity'::float, null, 1.23456e-18]]::ARRAY[ARRAY[FLOAT]]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [[0.0,0.1,0.2], [-1.0,-1.1,-1.2], [float('Inf'), float('-Inf'), None, 1.23456e-18]])

    def test_Array_with_Row_type(self):
        query = "SELECT ARRAY[ROW('Amy' AS name, 2 AS id, '2021-06-10'::DATE AS date),ROW('Fred' AS first_name, 4 AS id, '1998-02-24'::DATE)]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], [{"first_name":"Amy","id":2,"date":date(2021, 6, 10)},{"first_name":"Fred","id":4,"date":date(1998, 2, 24)}])


    #####################
    # tests for SET type
    #####################
    def test_1DSet_boolean_type(self):
        query = "SELECT SET['t', 'f', null]::SET[BOOL], SET[]::SET[BOOL], null::SET[BOOL]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {True, False, None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_integer_type(self):
        query = "SELECT SET[0,1,-2,3,null]::SET[INT], SET[]::SET[INT], null::SET[INT]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {0, 1, -2, 3, None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_float_type(self):
        query = ("SELECT SET['Infinity'::float, '-Infinity'::float, null, -1.234, 0, 1.23456e-18]::SET[FLOAT],"
                 " SET[]::SET[FLOAT], null::SET[FLOAT]")
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {float('Inf'), float('-Inf'), None, -1.234, 0.0, 1.23456e-18})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_numeric_type(self):
        query = "SELECT SET[-1.12, 0, null, 1234567890123456789.0123456789]::SET[NUMERIC], SET[]::SET[DECIMAL], null::SET[NUMERIC]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {Decimal('-1.1200000000'), Decimal('0E-10'), None, Decimal('1234567890123456789.0123456789')})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_char_type(self):
        query = u"SELECT SET['a', '\u16b1b', null, 'foo']::SET[CHAR(3)], SET[]::SET[CHAR(4)], null::SET[CHAR(5)]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {'a  ', u'\u16b1', None, 'foo'})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_varchar_type(self):
        query = u"SELECT SET['', '\u16b1\nb', null, 'foo']::SET[VARCHAR(10),4], SET[]::SET[VARCHAR(4)], null::SET[VARCHAR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {'', u'\u16b1\nb', None, 'foo'})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_date_type(self):
        query = "SELECT SET['2021-06-10', null, '0221-05-02']::SET[DATE], SET[]::SET[DATE], null::SET[DATE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {date(2021, 6, 10), None, date(221, 5, 2)})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_time_type(self):
        query = "SELECT SET['00:00:00.00', null, '22:36:33.123956']::SET[TIME(3)], SET[]::SET[TIME(4)], null::SET[TIME]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {time(0, 0, 0), None, time(22, 36, 33, 124000)})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_timetz_type(self):
        query = "SELECT SET['22:36:33.12345+0630', null, '800-02-03 22:36:33.123456 America/Cayman']::SET[TIMETZ(3)], SET[]::SET[TIMETZ(4)], null::SET[TIMETZ]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {time(22, 36, 33, 123000, tzinfo=tzoffset(None, 23400)), None, 
                                  time(22, 36, 33, 123000, tzinfo=tzoffset(None, -19176))})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_timestamp_type(self):
        query = "SELECT SET['276-12-1 11:22:33', '2001-12-01 00:30:45.087', null]::SET[TIMESTAMP], SET[]::SET[TIMESTAMP(4)], null::SET[TIMESTAMP]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {datetime(276, 12, 1, 11, 22, 33), datetime(2001, 12, 1, 0, 30, 45, 87000), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_timestamptz_type(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SET TIMEZONE 'America/Cayman'") # set session's time zone
            cur.fetchall()
            query = "SELECT SET['276-12-1 11:22:33+0630', '2001-12-01 00:30:45.087 America/Cayman', null]::SET[TIMESTAMPTZ], SET[]::SET[TIMESTAMPTZ(4)], null::SET[TIMESTAMPTZ]"
            cur.execute(query)
            res = cur.fetchone()
            self.assertEqual(res[0], {datetime(276, 11, 30, 23, 32, 57, tzinfo=tzoffset(None, -19176)),
                                datetime(2001, 12, 1, 0, 30, 45, 87000, tzinfo=tzoffset(None, -18000)), None})
            self.assertEqual(res[1], set())
            self.assertEqual(res[2], None)

    def test_1DSet_interval_type(self):
        query = "SELECT SET['1 02:03:04.0005', '1 02:03:04', '02:03:04.0005', '02:03', null]::SET[INTERVAL DAY TO SECOND], SET[]::SET[INTERVAL DAY TO SECOND], null::SET[INTERVAL DAY TO SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(days=+1, hours=+2, minutes=+3, seconds=+4, microseconds=+500),
                relativedelta(days=+1, hours=+2, minutes=+3, seconds=+4),
                relativedelta(hours=+2, minutes=+3, seconds=+4, microseconds=+500),
                relativedelta(hours=+2, minutes=+3), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['1 02:03', '02:03', null]::SET[INTERVAL DAY TO MINUTE], SET[]::SET[INTERVAL DAY TO MINUTE], null::SET[INTERVAL DAY TO MINUTE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(days=+1, hours=+2, minutes=+3), relativedelta(hours=+2, minutes=+3), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['1 02:03', '6', '02:03', null]::SET[INTERVAL DAY TO HOUR], SET[]::SET[INTERVAL DAY TO HOUR], null::SET[INTERVAL DAY TO HOUR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(days=+1, hours=+2), relativedelta(days=+6), relativedelta(hours=+2), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['123', '-6', null]::SET[INTERVAL DAY], SET[]::SET[INTERVAL DAY], null::SET[INTERVAL DAY]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(days=+123), relativedelta(days=-6), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['02:03:04', '02:03:04.0005', '02:03', null]::SET[INTERVAL HOUR TO SECOND], SET[]::SET[INTERVAL HOUR TO SECOND], null::SET[INTERVAL HOUR TO SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(hours=+2, minutes=+3, seconds=+4),
                relativedelta(hours=+2, minutes=+3, seconds=+4, microseconds=+500),
                relativedelta(hours=+2, minutes=+3), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['02:03:04', '-02:03', null]::SET[INTERVAL HOUR TO MINUTE], SET[]::SET[INTERVAL HOUR TO MINUTE], null::SET[INTERVAL HOUR TO MINUTE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(hours=+2, minutes=+3), relativedelta(hours=-2, minutes=-3), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['32', '-03', null]::SET[INTERVAL HOUR], SET[]::SET[INTERVAL HOUR], null::SET[INTERVAL HOUR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(days=+1, hours=+8), relativedelta(hours=-3), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['00:04.0005', '03:04', null]::SET[INTERVAL MINUTE TO SECOND], SET[]::SET[INTERVAL MINUTE TO SECOND], null::SET[INTERVAL MINUTE TO SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(seconds=+4, microseconds=+500), relativedelta(minutes=+3, seconds=+4), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['03', '-34', null]::SET[INTERVAL MINUTE], SET[]::SET[INTERVAL MINUTE], null::SET[INTERVAL MINUTE]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(minutes=+3), relativedelta(minutes=-34), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['216901.024', '216901', null]::SET[INTERVAL SECOND], SET[]::SET[INTERVAL SECOND], null::SET[INTERVAL SECOND]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(days=+2, hours=+12, minutes=+15, seconds=+1, microseconds=+24000),
                                  relativedelta(days=+2, hours=+12, minutes=+15, seconds=+1), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_intervalYM_type(self):
        query = "SELECT SET['1y 10m', '1y', '10m ago', null]::SET[INTERVAL YEAR TO MONTH], SET[]::SET[INTERVAL YEAR TO MONTH], null::SET[INTERVAL YEAR TO MONTH]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(years=+1, months=+10), relativedelta(years=+1), relativedelta(months=-10), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['1y ago', '2y', null]::SET[INTERVAL YEAR], SET[]::SET[INTERVAL YEAR], null::SET[INTERVAL YEAR]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(years=-1), relativedelta(years=+2), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

        query = "SELECT SET['1y 10m', '1y', '10m ago', null]::SET[INTERVAL MONTH], SET[]::SET[INTERVAL MONTH], null::SET[INTERVAL MONTH]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {relativedelta(years=+1, months=+10), relativedelta(years=+1), relativedelta(months=-10), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_UUID_type(self):
        query = "SELECT SET['00010203-0405-0607-0809-0a0b0c0d0e0f', null]::SET[UUID], SET[]::SET[UUID], null::SET[UUID]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {UUID('00010203-0405-0607-0809-0a0b0c0d0e0f'), None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_binary_type(self):
        query = "SELECT SET[hex_to_binary('0x41'), hex_to_binary('0x4243'), null]::SET[BINARY(2)], SET[]::SET[BINARY(4)], null::SET[BINARY]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {b'A\x00', b'BC', None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_1DSet_varbinary_type(self):
        query = "SELECT SET[hex_to_binary('0x41'), hex_to_binary('0x4210'), null]::SET[VARBINARY(2)], SET[]::SET[VARBINARY(4)], null::SET[VARBINARY]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {b'A', b'B\x10', None})
        self.assertEqual(res[1], set())
        self.assertEqual(res[2], None)

    def test_Set_dummy_type(self):
        query = "SELECT SET[]"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], set())

    #####################
    # tests for ROW type
    #####################
    def test_1DRow_type(self):
        query = "SELECT ROW(null, 'Amy', -3::int, '-Infinity'::float, 2.5::numeric, '2021-10-23'::DATE, false::bool, hex_to_binary('0x4210')::VARBINARY), null::ROW(a VARCHAR)"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {"f0":None,"f1":"Amy","f2":-3,"f3":float('-Inf'),"f4":Decimal('2.5'),"f5":date(2021, 10, 23),"f6":False, "f7":b'B\x10'})
        self.assertEqual(res[1], None)

    def test_NDRow_type(self):
        query = "SELECT ROW('Amy',ARRAY[1.5,-2,3.75],ARRAY[ARRAY[false::bool,null,true::bool]])::ROW(name varchar, b ARRAY[NUMERIC], c ARRAY[ARRAY[BOOL]])"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {"name":"Amy","b":[Decimal('1.5'),Decimal('-2'),Decimal('3.75')],"c":[[False,None,True]]})

        query = "SELECT ROW(ROW(ARRAY[ROW(ARRAY[1,2,3]),ROW(ARRAY[4,5,6]),ROW(ARRAY[7,8,9])]::ARRAY[ROW(d3 ARRAY[INTERVAL DAY])] AS d2) AS d1)"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {"d1":{"d2":[
            {"d3":[relativedelta(days=+1),relativedelta(days=+2),relativedelta(days=+3)]},
            {"d3":[relativedelta(days=+4),relativedelta(days=+5),relativedelta(days=+6)]},
            {"d3":[relativedelta(days=+7),relativedelta(days=+8),relativedelta(days=+9)]}]}})

    def test_Row_dummy_type(self):
        query = "SELECT ROW()"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {})

        query = "SELECT ROW(ROW()), ROW(ARRAY[])"
        res = self._query_and_fetchone(query)
        self.assertEqual(res[0], {"f0":{}})
        self.assertEqual(res[1], {"f0":[]})

exec(ComplexTypeTestCase.createPrepStmtClass())
