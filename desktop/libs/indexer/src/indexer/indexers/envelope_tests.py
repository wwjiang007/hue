#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.contrib.auth.models import User
from nose.tools import assert_equal, assert_true

from indexer.indexers.envelope import EnvelopeIndexer


def test_generate_from_kafka_to_file_csv():
  properties = {
    'app_name': 'Ingest',

    'inputFormat': 'stream',
    'streamSelection': 'kafka',
    'brokers': 'broker:9092',
    'topics': 'kafkaTopic',
    'kafkaFieldType': 'delimited',
    'kafkaFieldDelimiter': ',',
    'kafkaFieldNames': 'id,name',
    'kafkaFieldTypes': 'int,string',

    'ouputFormat': 'file',
    'path': '/tmp/output',
    'format': 'csv'
  }

  config = EnvelopeIndexer(username='test').generate_config(properties)

  assert_true('''steps {
    inputdata {
        input {
            type = kafka
                brokers = "broker:9092"
                topics = kafkaTopic
                encoding = string
                translator {
                    type = delimited
                    delimiter = ","
                    field.names = [id,name]
                    field.types = [int,string]
                }
                window {
                    enabled = true
                    milliseconds = 60000
                }
        
        }
    }

    outputdata {
        dependencies = [inputdata]
        planner = {
          type = overwrite
        }
        output = {
          type = filesystem
          path = /tmp/output
          format = csv
          header = true
        }
    }
}
''' in  config, config)


def test_generate_from_stream_sfdc_to_hive_table():
  properties = {
    'app_name': 'Ingest',

    'inputFormat': 'stream',    
    'streamSelection': 'sfdc',
    'streamUsername': 'test',
    'streamPassword': 'test',
    'streamToken': 'token',
    'streamEndpointUrl': 'http://sfdc/api',
    'streamObject': 'Opportunities',

    'ouputFormat': 'table',
    'output_table': 'sfdc',
    'format': 'text'
  }

  config = EnvelopeIndexer(username='test').generate_config(properties)

  assert_true('''steps {
    inputdata {
        input {
            type = sfdc
            mode = fetch-all
            sobject = Opportunities
            sfdc: {
              partner: {
                username = "test"
                password = "test"
                token = "token"
                auth-endpoint = "http://sfdc/api"
              }
            }
  
        }
    }

    outputdata {
        dependencies = [inputdata]
          planner {
              type = append
          }
          output {
              type = hive
              table.name = "sfdc"
          }
    }
}''' in  config, config)
  

def test_generate_from_stream_kafka_to_solr_index():
  properties = {
    'app_name': 'Ingest',

    'inputFormat': 'stream',
    'streamSelection': 'kafka',
    'brokers': 'broker:9092',
    'topics': 'kafkaTopic',
    'kafkaFieldType': 'delimited',
    'kafkaFieldDelimiter': ',',
    'kafkaFieldNames': 'id,name',
    'kafkaFieldTypes': 'int,string',

    'ouputFormat': 'index',
    'connection': 'http://hue.com:8983/solr/',
    'collectionName': 'traffic'
  }

  config = EnvelopeIndexer(username='test').generate_config(properties)

  assert_true('''steps {
    inputdata {
        input {
            type = kafka
                brokers = "broker:9092"
                topics = kafkaTopic
                encoding = string
                translator {
                    type = delimited
                    delimiter = ","
                    field.names = [id,name]
                    field.types = [int,string]
                }
                window {
                    enabled = true
                    milliseconds = 60000
                }
        
        }
    }

    outputdata {
        dependencies = [inputdata]
        planner {
            type = upstert
        }
        output {
            type = solr
            connection = "http://hue.com:8983/solr/"
            collection.name = "traffic"
        }
    }
}''' in  config, config)
