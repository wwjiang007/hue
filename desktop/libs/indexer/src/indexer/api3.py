#!/usr/bin/env python
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

import chardet
import json
import logging
import StringIO

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from desktop.lib import django_mako
from desktop.lib.django_util import JsonResponse
from desktop.lib.exceptions_renderable import PopupException
from desktop.lib.i18n import smart_unicode
from desktop.models import Document2
from librdbms.server import dbms as rdbms
from libsentry.conf import is_enabled
from metadata.manager_client import ManagerApi
from notebook.connectors.base import get_api, Notebook
from notebook.decorators import api_error_handler
from notebook.models import make_notebook, MockedDjangoRequest, escape_rows

from indexer.controller import CollectionManagerController
from indexer.file_format import HiveFormat
from indexer.fields import Field
from indexer.indexers.envelope import EnvelopeIndexer
from indexer.indexers.morphline import MorphlineIndexer
from indexer.indexers.rdbms import RdbmsIndexer, run_sqoop
from indexer.indexers.sql import SQLIndexer
from indexer.solr_client import SolrClient, MAX_UPLOAD_SIZE
from metadata.kafka_api import get_topics


LOG = logging.getLogger(__name__)


try:
  from beeswax.server import dbms
except ImportError, e:
  LOG.warn('Hive and HiveServer2 interfaces are not enabled')

try:
  from filebrowser.views import detect_parquet
except ImportError, e:
  LOG.warn('File Browser interfaces are not enabled')


def _escape_white_space_characters(s, inverse = False):
  MAPPINGS = {
    "\n": "\\n",
    "\t": "\\t",
    "\r": "\\r",
    " ": "\\s"
  }

  to = 1 if inverse else 0
  from_ = 0 if inverse else 1

  for pair in MAPPINGS.iteritems():
    s = s.replace(pair[to], pair[from_]).encode('utf-8')

  return s


def _convert_format(format_dict, inverse=False):
  for field in format_dict:
    if isinstance(format_dict[field], basestring):
      format_dict[field] = _escape_white_space_characters(format_dict[field], inverse)


@api_error_handler
def guess_format(request):
  file_format = json.loads(request.POST.get('fileFormat', '{}'))

  if file_format['inputFormat'] == 'file':
    indexer = MorphlineIndexer(request.user, request.fs)
    if not request.fs.isfile(file_format["path"]):
      raise PopupException(_('Path %(path)s is not a file') % file_format)
    if is_enabled():
      parent_path = request.fs.parent_path(file_format["path"])
      if request.fs.stats(parent_path)["mode"] & 0700 != 0700:
        print 'not good ' + parent_path

    stream = request.fs.open(file_format["path"])
    if detect_parquet(stream):
      format_ = {"type": "parquet", "fieldSeparator": "", "hasHeader": False, "quoteChar": "", "recordSeparator": ""}
    else:
      stream.seek(0)
      format_ = indexer.guess_format({
        "file": {
          "stream": stream,
          "name": file_format['path']
        }
      })
      _convert_format(format_)
  elif file_format['inputFormat'] == 'table':
    db = dbms.get(request.user)
    try:
      table_metadata = db.get_table(database=file_format['databaseName'], table_name=file_format['tableName'])
    except Exception, e:
      raise PopupException(e.message if hasattr(e, 'message') and e.message else e)
    storage = {}
    for delim in table_metadata.storage_details:
      if delim['data_type']:
        if '=' in delim['data_type']:
          key, val = delim['data_type'].split('=', 1)
          storage[key] = val
        else:
          storage[delim['data_type']] = delim['comment']
    if table_metadata.details['properties']['format'] == 'text':
      format_ = {"quoteChar": "\"", "recordSeparator": '\\n', "type": "csv", "hasHeader": False, "fieldSeparator": storage.get('field.delim', ',')}
    elif table_metadata.details['properties']['format'] == 'parquet':
      format_ = {"type": "parquet", "hasHeader": False,}
    else:
      raise PopupException('Hive table format %s is not supported.' % table_metadata.details['properties']['format'])
  elif file_format['inputFormat'] == 'query':
    format_ = {"quoteChar": "\"", "recordSeparator": "\\n", "type": "csv", "hasHeader": False, "fieldSeparator": "\u0001"}
  elif file_format['inputFormat'] == 'rdbms':
    format_ = RdbmsIndexer(request.user, file_format['rdbmsType']).guess_format()
  elif file_format['inputFormat'] == 'stream':
    if file_format['streamSelection'] == 'kafka':
      format_ = {"type": "csv", "fieldSeparator": ",", "hasHeader": True, "quoteChar": "\"", "recordSeparator": "\\n", 'topics': get_topics()}
    elif file_format['streamSelection'] == 'sfdc':
      stream = StringIO.StringIO()
      stream.write("""AccountId,Amount,CampaignId,CloseDate,CreatedById,CreatedDate,CurrentGenerators__c,DeliveryInstallationStatus__c,Description,ExpectedRevenue,Fiscal,FiscalQuarter,FiscalYear,ForecastCategory,ForecastCategoryName,HasOpenActivity,HasOpportunityLineItem,HasOverdueTask,Id,IsClosed,IsDeleted,IsPrivate,IsWon,LastActivityDate,LastModifiedById,LastModifiedDate,LastReferencedDate,LastViewedDate,LeadSource,MainCompetitors__c,Name,NextStep,OrderNumber__c,OwnerId,Pricebook2Id,Probability,StageName,SystemModstamp,TotalOpportunityQuantity,TrackingNumber__c,Type
0014600000Ctb1UAAR,30000.0,,1489968000000,005460000012t2xAAA,1490625405000,,In progress,,30000.0,2015 2,2,2015,Closed,Closed,false,false,false,00646000003Ymn1AAC,true,false,false,true,,005460000012t2xAAA,1490625405000,,,Partner,,GenePoint SLA,,546512,005460000012t2xAAA,,100.0,Closed Won,1490625405000,,,Existing Customer - Upgrade
0014600000Ctb1NAAR,17000.0,,1486080000000,005460000012t2xAAA,1490625405000,,,,1700.0,2017 1,1,2017,Pipeline,Pipeline,false,false,false,00646000003YmmoAAC,false,false,false,false,,005460000012t2xAAA,1491321348000,,,Purchased List,Honda,Dickenson Mobile Generators,,,005460000012t2xAAA,,10.0,Qualification,1491389012000,,,New Customer
0014600000Ctb1PAAR,915000.0,,1488326400000,005460000012t2xAAA,1490625405000,John Deere,Completed,,915000.0,2015 2,2,2015,Closed,Closed,false,false,false,00646000003Ymn7AAC,true,false,false,true,,005460000012t2xAAA,1490625405000,,,Partner,"John Deere, Mitsubishi, Hawkpower",United Oil Refinery Generators,,744343,005460000012t2xAAA,,100.0,Closed Won,1491389012000,,830150301360,New Customer
0014600000Ctb1UAAR,85000.0,,1485302400000,005460000012t2xAAA,1490625405000,Honda,Completed,,85000.0,2015 1,1,2015,Closed,Closed,false,false,false,00646000003YmmrAAC,true,false,false,true,,005460000012t2xAAA,1490625405000,,,Partner,Honda,GenePoint Standby Generator,,908676,005460000012t2xAAA,,100.0,Closed Won,1490625405000,,830150301420,New Customer
0014600000Ctb1MAAR,100000.0,,1485734400000,005460000012t2xAAA,1490625405000,,,,10000.0,2015 1,1,2015,Pipeline,Pipeline,false,false,false,00646000003YmmyAAC,false,false,false,false,,005460000012t2xAAA,1490625405000,,,Phone Inquiry,,Pyramid Emergency Generators,,,005460000012t2xAAA,,10.0,Prospecting,1490625405000,,,""")

      indexer = MorphlineIndexer(request.user, request.fs)
      format_ = indexer.guess_format({
        "file": {
          "stream": stream,
          "name": file_format['path']
        }
      })
      _convert_format(format_)

  format_['status'] = 0
  return JsonResponse(format_)


def guess_field_types(request):
  file_format = json.loads(request.POST.get('fileFormat', '{}'))

  if file_format['inputFormat'] == 'file':
    indexer = MorphlineIndexer(request.user, request.fs)
    stream = request.fs.open(file_format["path"])
    encoding = chardet.detect(stream.read(10000)).get('encoding')
    stream.seek(0)
    _convert_format(file_format["format"], inverse=True)

    format_ = indexer.guess_field_types({
      "file": {
          "stream": stream,
          "name": file_format['path']
        },
      "format": file_format['format']
    })

    # Note: Would also need to set charset to table (only supported in Hive)
    if 'sample' in format_:
      format_['sample'] = escape_rows(format_['sample'], nulls_only=True, encoding=encoding)
    for col in format_['columns']:
      col['name'] = smart_unicode(col['name'], errors='replace', encoding=encoding)

  elif file_format['inputFormat'] == 'table':
    sample = get_api(request, {'type': 'hive'}).get_sample_data({'type': 'hive'}, database=file_format['databaseName'], table=file_format['tableName'])
    db = dbms.get(request.user)
    table_metadata = db.get_table(database=file_format['databaseName'], table_name=file_format['tableName'])

    format_ = {
        "sample": sample['rows'][:4],
        "columns": [
            Field(col.name, HiveFormat.FIELD_TYPE_TRANSLATE.get(col.type, 'string')).to_dict()
            for col in table_metadata.cols
        ]
    }
  elif file_format['inputFormat'] == 'query':
    query_id = file_format['query']['id'] if file_format['query'].get('id') else file_format['query']

    notebook = Notebook(document=Document2.objects.document(user=request.user, doc_id=query_id)).get_data()
    snippet = notebook['snippets'][0]
    db = get_api(request, snippet)

    if file_format.get('sampleCols'):
      columns = file_format.get('sampleCols')
      sample = file_format.get('sample')
    else:
      snippet['query'] = snippet['statement']
      try:
        sample = db.fetch_result(notebook, snippet, 4, start_over=True)['rows'][:4]
      except Exception, e:
        LOG.warn('Skipping sample data as query handle might be expired: %s' % e)
        sample = [[], [], [], [], []]
      columns = db.autocomplete(snippet=snippet, database='', table='')
      columns = [
          Field(col['name'], HiveFormat.FIELD_TYPE_TRANSLATE.get(col['type'], 'string')).to_dict()
          for col in columns['extended_columns']
      ]
    format_ = {
        "sample": sample,
        "columns": columns,
    }
  elif file_format['inputFormat'] == 'rdbms':
    query_server = rdbms.get_query_server_config(server=file_format['rdbmsType'])
    db = rdbms.get(request.user, query_server=query_server)
    sample = RdbmsIndexer(request.user, file_format['rdbmsType']).get_sample_data(mode=file_format['rdbmsMode'], database=file_format['rdbmsDatabaseName'], table=file_format['rdbmsTableName'])
    table_metadata = db.get_columns(file_format['rdbmsDatabaseName'], file_format['rdbmsTableName'], names_only=False)

    format_ = {
        "sample": list(sample['rows'])[:4],
        "columns": [
            Field(col['name'], HiveFormat.FIELD_TYPE_TRANSLATE.get(col['type'], 'string')).to_dict()
            for col in table_metadata
        ]
    }
  elif file_format['inputFormat'] == 'stream':
    # Note: mocked here, should come from SFDC or Kafka API or sampling job
    if file_format['streamSelection'] == 'kafka':
      data = """%(kafkaFieldNames)s
%(data)s""" % {
        'kafkaFieldNames': file_format['kafkaFieldNames'],
        'data': '\n'.join([','.join(['...'] * len(file_format['kafkaFieldTypes'].split(',')))] * 5)
      }
    elif file_format['streamSelection'] == 'sfdc':
      data = """AccountId,Amount,CampaignId,CloseDate,CreatedById,CreatedDate,CurrentGenerators__c,DeliveryInstallationStatus__c,Description,ExpectedRevenue,Fiscal,FiscalQuarter,FiscalYear,ForecastCategory,ForecastCategoryName,HasOpenActivity,HasOpportunityLineItem,HasOverdueTask,Id,IsClosed,IsDeleted,IsPrivate,IsWon,LastActivityDate,LastModifiedById,LastModifiedDate,LastReferencedDate,LastViewedDate,LeadSource,MainCompetitors__c,Name,NextStep,OrderNumber__c,OwnerId,Pricebook2Id,Probability,StageName,SystemModstamp,TotalOpportunityQuantity,TrackingNumber__c,Type
0014600000Ctb1UAAR,30000.0,,1489968000000,005460000012t2xAAA,1490625405000,,In progress,,30000.0,2015 2,2,2015,Closed,Closed,false,false,false,00646000003Ymn1AAC,true,false,false,true,,005460000012t2xAAA,1490625405000,,,Partner,,GenePoint SLA,,546512,005460000012t2xAAA,,100.0,Closed Won,1490625405000,,,Existing Customer - Upgrade
0014600000Ctb1NAAR,17000.0,,1486080000000,005460000012t2xAAA,1490625405000,,,,1700.0,2017 1,1,2017,Pipeline,Pipeline,false,false,false,00646000003YmmoAAC,false,false,false,false,,005460000012t2xAAA,1491321348000,,,Purchased List,Honda,Dickenson Mobile Generators,,,005460000012t2xAAA,,10.0,Qualification,1491389012000,,,New Customer
0014600000Ctb1PAAR,915000.0,,1488326400000,005460000012t2xAAA,1490625405000,John Deere,Completed,,915000.0,2015 2,2,2015,Closed,Closed,false,false,false,00646000003Ymn7AAC,true,false,false,true,,005460000012t2xAAA,1490625405000,,,Partner,"John Deere, Mitsubishi, Hawkpower",United Oil Refinery Generators,,744343,005460000012t2xAAA,,100.0,Closed Won,1491389012000,,830150301360,New Customer
0014600000Ctb1UAAR,85000.0,,1485302400000,005460000012t2xAAA,1490625405000,Honda,Completed,,85000.0,2015 1,1,2015,Closed,Closed,false,false,false,00646000003YmmrAAC,true,false,false,true,,005460000012t2xAAA,1490625405000,,,Partner,Honda,GenePoint Standby Generator,,908676,005460000012t2xAAA,,100.0,Closed Won,1490625405000,,830150301420,New Customer
0014600000Ctb1MAAR,100000.0,,1485734400000,005460000012t2xAAA,1490625405000,,,,10000.0,2015 1,1,2015,Pipeline,Pipeline,false,false,false,00646000003YmmyAAC,false,false,false,false,,005460000012t2xAAA,1490625405000,,,Phone Inquiry,,Pyramid Emergency Generators,,,005460000012t2xAAA,,10.0,Prospecting,1490625405000,,,"""

    stream = StringIO.StringIO()
    stream.write(data)

    _convert_format(file_format["format"], inverse=True)

    indexer = MorphlineIndexer(request.user, request.fs)
    format_ = indexer.guess_field_types({
      "file": {
          "stream": stream,
          "name": file_format['path']
        },
      "format": file_format['format']
    })

    if file_format['streamSelection'] == 'kafka':
      type_mapping = dict(zip(file_format['kafkaFieldNames'].split(','), file_format['kafkaFieldTypes'].split(',')))
      for col in format_['columns']:
        col['keyType'] = type_mapping[col['name']]
        col['type'] = type_mapping[col['name']]

  return JsonResponse(format_)


@api_error_handler
def importer_submit(request):
  source = json.loads(request.POST.get('source', '{}'))
  outputFormat = json.loads(request.POST.get('destination', '{}'))['outputFormat']
  destination = json.loads(request.POST.get('destination', '{}'))
  destination['ouputFormat'] = outputFormat # Workaround a very weird bug
  start_time = json.loads(request.POST.get('start_time', '-1'))

  if source['inputFormat'] == 'file':
    source['path'] = request.fs.netnormpath(source['path']) if source['path'] else source['path']
  if destination['ouputFormat'] in ('database', 'table'):
    destination['nonDefaultLocation'] = request.fs.netnormpath(destination['nonDefaultLocation']) if destination['nonDefaultLocation'] else destination['nonDefaultLocation']

  if destination['ouputFormat'] == 'index':
    source['columns'] = destination['columns']
    index_name = destination["name"]

    if destination['indexerRunJob']:
      _convert_format(source["format"], inverse=True)
      job_handle = _large_indexing(request, source, index_name, start_time=start_time, lib_path=destination['indexerJobLibPath'])
    else:
      client = SolrClient(request.user)
      job_handle = _small_indexing(request.user, request.fs, client, source, destination, index_name)
  elif destination['ouputFormat'] == 'database':
    job_handle = _create_database(request, source, destination, start_time)
  elif source['inputFormat'] == 'rdbms':
    if destination['outputFormat'] in ('file', 'table', 'hbase'):
      job_handle = run_sqoop(request, source, destination, start_time)
  elif source['inputFormat'] == 'stream':
    job_handle = _envelope_job(request, source, destination, start_time=start_time, lib_path=destination['indexerJobLibPath'])
  else:
    job_handle = _create_table(request, source, destination, start_time)

  request.audit = {
    'operation': 'EXPORT',
    'operationText': 'User %(username)s exported %(inputFormat)s to %(ouputFormat)s: %(name)s' % {
        'username': request.user.username,
        'inputFormat': source['inputFormat'],
        'ouputFormat': destination['ouputFormat'],
        'name': destination['name'],
    },
    'allowed': True
  }

  return JsonResponse(job_handle)


def _small_indexing(user, fs, client, source, destination, index_name):
  unique_key_field = destination['indexerPrimaryKey'] and destination['indexerPrimaryKey'][0] or None
  df = destination['indexerDefaultField'] and destination['indexerDefaultField'][0] or None
  kwargs = {}
  errors = []

  if source['inputFormat'] not in ('manual', 'table', 'query_handle'):
    stats = fs.stats(source["path"])
    if stats.size > MAX_UPLOAD_SIZE:
      raise PopupException(_('File size is too large to handle!'))

  indexer = MorphlineIndexer(user, fs)
  fields = indexer.get_field_list(destination['columns'])
  skip_fields = [field['name'] for field in fields if not field['keep']]

  kwargs['fieldnames'] = ','.join([field['name'] for field in fields])
  for field in fields:
    for operation in field['operations']:
      if operation['type'] == 'split':
        field['multiValued'] = True # Solr requires multiValued to be set when splitting
        kwargs['f.%(name)s.split' % field] = 'true'
        kwargs['f.%(name)s.separator' % field] = operation['settings']['splitChar'] or ','

  if skip_fields:
    kwargs['skip'] = ','.join(skip_fields)
    fields = [field for field in fields if field['name'] not in skip_fields]

  if not unique_key_field:
    unique_key_field = 'hue_id'
    fields += [{"name": unique_key_field, "type": "string"}]
    kwargs['rowid'] = unique_key_field

  if not destination['hasHeader']:
    kwargs['header'] = 'false'
  else:
    kwargs['skipLines'] = 1

  if not client.exists(index_name):
    client.create_index(
        name=index_name,
        config_name=destination.get('indexerConfigSet'),
        fields=fields,
        unique_key_field=unique_key_field,
        df=df,
        shards=destination['indexerNumShards'],
        replication=destination['indexerReplicationFactor']
    )

  if source['inputFormat'] == 'file':
    data = fs.read(source["path"], 0, MAX_UPLOAD_SIZE)

  if client.is_solr_six_or_more():
    kwargs['processor'] = 'tolerant'
    kwargs['map'] = 'NULL:'

  try:
    if source['inputFormat'] == 'query':
      query_id = source['query']['id'] if source['query'].get('id') else source['query']

      notebook = Notebook(document=Document2.objects.document(user=user, doc_id=query_id)).get_data()
      request = MockedDjangoRequest(user=user)
      snippet = notebook['snippets'][0]

      searcher = CollectionManagerController(user)
      columns = [field['name'] for field in fields if field['name'] != 'hue_id']
      fetch_handle = lambda rows, start_over: get_api(request, snippet).fetch_result(notebook, snippet, rows=rows, start_over=start_over) # Assumes handle still live
      rows = searcher.update_data_from_hive(index_name, columns, fetch_handle=fetch_handle, indexing_options=kwargs)
      # TODO if rows == MAX_ROWS truncation warning
    else:
      response = client.index(name=index_name, data=data, **kwargs)
      errors = [error.get('message', '') for error in response['responseHeader'].get('errors', [])]
  except Exception, e:
    try:
      client.delete_index(index_name, keep_config=False)
    except Exception, e2:
      LOG.warn('Error while cleaning-up config of failed collection creation %s: %s' % (index_name, e2))
    raise e

  return {'status': 0, 'on_success_url': reverse('indexer:indexes', kwargs={'index': index_name}), 'pub_sub_url': 'assist.collections.refresh', 'errors': errors}


def _create_database(request, source, destination, start_time):
  database = destination['name']
  comment = destination['description']

  use_default_location = destination['useDefaultLocation']
  external_path = destination['nonDefaultLocation']

  sql = django_mako.render_to_string("gen/create_database_statement.mako", {
      'database': {
          'name': database,
          'comment': comment,
          'use_default_location': use_default_location,
          'external_location': external_path,
          'properties': [],
      }
    }
  )

  editor_type = destination['apiHelperType']
  on_success_url = reverse('metastore:show_tables', kwargs={'database': database})

  notebook = make_notebook(
      name=_('Creating database %(name)s') % destination,
      editor_type=editor_type,
      statement=sql,
      status='ready',
      on_success_url=on_success_url,
      last_executed=start_time,
      is_task=True
  )
  return notebook.execute(request, batch=False)


def _create_table(request, source, destination, start_time=-1):
  notebook = SQLIndexer(user=request.user, fs=request.fs).create_table_from_a_file(source, destination, start_time)
  return notebook.execute(request, batch=False)


def _large_indexing(request, file_format, collection_name, query=None, start_time=None, lib_path=None):
  indexer = MorphlineIndexer(request.user, request.fs)

  unique_field = indexer.get_unique_field(file_format)
  is_unique_generated = indexer.is_unique_generated(file_format)

  schema_fields = indexer.get_kept_field_list(file_format['columns'])
  if is_unique_generated:
    schema_fields += [{"name": unique_field, "type": "string"}]

  client = SolrClient(user=request.user)

  if not client.exists(collection_name):
    client.create_index(
      name=collection_name,
      fields=request.POST.get('fields', schema_fields),
      unique_key_field=unique_field
      # No df currently
    )

  if file_format['inputFormat'] == 'table':
    db = dbms.get(request.user)
    table_metadata = db.get_table(database=file_format['databaseName'], table_name=file_format['tableName'])
    input_path = table_metadata.path_location
  elif file_format['inputFormat'] == 'file':
    input_path = '${nameNode}%s' % file_format["path"]
  else:
    input_path = None

  morphline = indexer.generate_morphline_config(collection_name, file_format, unique_field, lib_path=lib_path)

  return indexer.run_morphline(request, collection_name, morphline, input_path, query, start_time=start_time, lib_path=lib_path)


def _envelope_job(request, file_format, destination, start_time=None, lib_path=None):
  collection_name = destination['name']
  indexer = EnvelopeIndexer(request.user, request.fs)

  lib_path = lib_path or '/tmp/envelope-0.5.0.jar'
  input_path = None

  if file_format['inputFormat'] == 'table':
    db = dbms.get(request.user)
    table_metadata = db.get_table(database=file_format['databaseName'], table_name=file_format['tableName'])
    input_path = table_metadata.path_location
  elif file_format['inputFormat'] == 'file':
    input_path = '${nameNode}%s' % file_format["path"]
    properties = {
      'format': 'json'
    }
  elif file_format['inputFormat'] == 'stream':
    if file_format['streamSelection'] == 'sfdc':
      properties = {
        'streamSelection': file_format['streamSelection'],
        'streamUsername': file_format['streamUsername'],
        'streamPassword': file_format['streamPassword'],
        'streamToken': file_format['streamToken'],
        'streamEndpointUrl': file_format['streamEndpointUrl'],
        'streamObject': file_format['streamObject'],
      }
    elif file_format['streamSelection'] == 'kafka':
      manager = ManagerApi()
      properties = {
        "brokers": manager.get_kafka_brokers(),
        "output_table": "impala::%s" % collection_name,
        "topics": file_format['kafkaSelectedTopics'],
        "kafkaFieldType": file_format['kafkaFieldType'],
        "kafkaFieldDelimiter": file_format['kafkaFieldDelimiter'],
        "kafkaFieldNames": file_format['kafkaFieldNames'],
        "kafkaFieldTypes": file_format['kafkaFieldTypes']
      }

    if destination['outputFormat'] == 'table':
      if destination['isTargetExisting']:
        # Todo: check if format matches
        pass
      else:
        sql = SQLIndexer(user=request.user, fs=request.fs).create_table_from_a_file(file_format, destination).get_str()
        print sql
      properties["output_table"] = "impala::%s" % collection_name
      properties["kudu_master"] = manager.get_kudu_master()
    elif destination['outputFormat'] == 'file':
      properties['path'] = file_format["path"]
      properties['format'] = file_format['tableFormat'] # or csv

  properties["app_name"] = 'Data Ingest'
  properties["inputFormat"] = file_format['inputFormat']
  properties["ouputFormat"] = destination['ouputFormat']
  properties["streamSelection"] = file_format["streamSelection"]

  morphline = indexer.generate_config(properties)

  return indexer.run(request, collection_name, morphline, input_path, start_time=start_time, lib_path=lib_path)
