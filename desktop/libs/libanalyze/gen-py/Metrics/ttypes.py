#
# Autogenerated by Thrift Compiler (0.9.3)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py:new_style
#

from builtins import object
from thrift.Thrift import TType, TMessageType, TException, TApplicationException

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None


class TUnit(object):
  UNIT = 0
  UNIT_PER_SECOND = 1
  CPU_TICKS = 2
  BYTES = 3
  BYTES_PER_SECOND = 4
  TIME_NS = 5
  DOUBLE_VALUE = 6
  NONE = 7
  TIME_MS = 8
  TIME_S = 9
  TIME_US = 10

  _VALUES_TO_NAMES = {
    0: "UNIT",
    1: "UNIT_PER_SECOND",
    2: "CPU_TICKS",
    3: "BYTES",
    4: "BYTES_PER_SECOND",
    5: "TIME_NS",
    6: "DOUBLE_VALUE",
    7: "NONE",
    8: "TIME_MS",
    9: "TIME_S",
    10: "TIME_US",
  }

  _NAMES_TO_VALUES = {
    "UNIT": 0,
    "UNIT_PER_SECOND": 1,
    "CPU_TICKS": 2,
    "BYTES": 3,
    "BYTES_PER_SECOND": 4,
    "TIME_NS": 5,
    "DOUBLE_VALUE": 6,
    "NONE": 7,
    "TIME_MS": 8,
    "TIME_S": 9,
    "TIME_US": 10,
  }

class TMetricKind(object):
  GAUGE = 0
  COUNTER = 1
  PROPERTY = 2
  STATS = 3
  SET = 4
  HISTOGRAM = 5

  _VALUES_TO_NAMES = {
    0: "GAUGE",
    1: "COUNTER",
    2: "PROPERTY",
    3: "STATS",
    4: "SET",
    5: "HISTOGRAM",
  }

  _NAMES_TO_VALUES = {
    "GAUGE": 0,
    "COUNTER": 1,
    "PROPERTY": 2,
    "STATS": 3,
    "SET": 4,
    "HISTOGRAM": 5,
  }

