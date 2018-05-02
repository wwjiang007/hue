#!/usr/bin/env python
# -- coding: utf-8 --
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

import logging

from django.core.cache import cache
from django.utils.translation import ugettext as _

from desktop.lib.rest.http_client import RestException, HttpClient
from desktop.lib.rest.resource import Resource
from desktop.lib.i18n import smart_unicode
from metadata.conf import MANAGER


LOG = logging.getLogger(__name__)
VERSION = 'v19'


class ManagerApiException(Exception):
  def __init__(self, message=None):
    self.message = message or _('No error message, please check the logs.')

  def __str__(self):
    return str(self.message)

  def __unicode__(self):
    return smart_unicode(self.message)


class ManagerApi(object):
  """
  https://cloudera.github.io/cm_api/
  """

  def __init__(self, user=None, security_enabled=False, ssl_cert_ca_verify=False):
    self._api_url = '%s/%s' % (MANAGER.API_URL.get().strip('/'), VERSION)
    self._username = 'hue' #get_navigator_auth_username()
    self._password = 'hue' #get_navigator_auth_password()

    self.user = user
    self._client = HttpClient(self._api_url, logger=LOG)

    if security_enabled:
      self._client.set_kerberos_auth()
    else:
      self._client.set_basic_auth(self._username, self._password)

    self._client.set_verify(ssl_cert_ca_verify)
    self._root = Resource(self._client)


  def tools_echo(self):
    try:
      params = (
        ('message', 'hello'),
      )

      LOG.info(params)
      return self._root.get('tools/echo', params=params)
    except RestException, e:
      raise ManagerApiException(e)


  def get_kafka_brokers(self, cluster_name=None):
    try:
      cluster = self._get_services(cluster_name)
      services = self._root.get('clusters/%(name)s/services' % cluster)['items']

      service = [service for service in services if service['type'] == 'KAFKA'][0]
      broker_hosts = self._get_roles(cluster['name'], service['name'], 'KAFKA_BROKER')
      broker_hosts_ids = [broker_host['hostRef']['hostId'] for broker_host in broker_hosts]

      hosts = self._root.get('hosts')['items']
      brokers_hosts = [host['hostname'] + ':9092' for host in hosts if host['hostId'] in broker_hosts_ids]

      return ','.join(brokers_hosts)
    except RestException, e:
      raise ManagerApiException(e)


  def get_kudu_master(self, cluster_name=None):
    try:
      cluster = self._get_services(cluster_name)
      services = self._root.get('clusters/%(name)s/services' % cluster)['items']

      service = [service for service in services if service['type'] == 'KUDU'][0]
      master = self._get_roles(cluster['name'], service['name'], 'KUDU_MASTER')[0]

      master_host = self._root.get('hosts/%(hostId)s' % master['hostRef'])

      return master_host['hostname']
    except RestException, e:
      raise ManagerApiException(e)


  def get_kafka_topics(self, broker_host):
    try:
      _client = HttpClient('%s:24042' % broker_host, logger=LOG)
      _root = Resource(self._client)
      
      return self._root.get('/api/topics')
    except RestException, e:
      return {"traffic":{"partitions":[{"replicas":[70],"partitionId":0,"leader":70,"isr":[70]}],"topicProps":None,"isInternal":False},"__consumer_offsets":{"partitions":[{"replicas":[69,68,70],"partitionId":23,"leader":69,"isr":[69,68,70]},{"replicas":[69,68,70],"partitionId":41,"leader":69,"isr":[69,68,70]},{"replicas":[69,70,68],"partitionId":32,"leader":69,"isr":[69,70,68]},{"replicas":[69,68,70],"partitionId":17,"leader":69,"isr":[69,68,70]},{"replicas":[69,70,68],"partitionId":8,"leader":69,"isr":[69,70,68]},{"replicas":[69,68,70],"partitionId":35,"leader":69,"isr":[69,68,70]},{"replicas":[69,70,68],"partitionId":44,"leader":69,"isr":[69,70,68]},{"replicas":[69,70,68],"partitionId":26,"leader":69,"isr":[69,70,68]},{"replicas":[69,68,70],"partitionId":11,"leader":69,"isr":[69,68,70]},{"replicas":[69,68,70],"partitionId":47,"leader":69,"isr":[69,68,70]},{"replicas":[69,70,68],"partitionId":38,"leader":69,"isr":[69,70,68]},{"replicas":[69,68,70],"partitionId":29,"leader":69,"isr":[69,68,70]},{"replicas":[69,70,68],"partitionId":20,"leader":69,"isr":[69,70,68]},{"replicas":[69,70,68],"partitionId":2,"leader":69,"isr":[69,70,68]},{"replicas":[69,68,70],"partitionId":5,"leader":69,"isr":[69,68,70]},{"replicas":[69,70,68],"partitionId":14,"leader":69,"isr":[69,70,68]},{"replicas":[68,70,69],"partitionId":46,"leader":68,"isr":[68,70,69]},{"replicas":[68,70,69],"partitionId":40,"leader":68,"isr":[68,70,69]},{"replicas":[68,69,70],"partitionId":49,"leader":68,"isr":[68,69,70]},{"replicas":[68,69,70],"partitionId":13,"leader":68,"isr":[68,69,70]},{"replicas":[68,70,69],"partitionId":4,"leader":68,"isr":[68,70,69]},{"replicas":[68,69,70],"partitionId":31,"leader":68,"isr":[68,69,70]},{"replicas":[68,70,69],"partitionId":22,"leader":68,"isr":[68,70,69]},{"replicas":[68,70,69],"partitionId":16,"leader":68,"isr":[68,70,69]},{"replicas":[68,69,70],"partitionId":7,"leader":68,"isr":[68,69,70]},{"replicas":[68,69,70],"partitionId":43,"leader":68,"isr":[68,69,70]},{"replicas":[68,69,70],"partitionId":25,"leader":68,"isr":[68,69,70]},{"replicas":[68,70,69],"partitionId":34,"leader":68,"isr":[68,70,69]},{"replicas":[68,70,69],"partitionId":10,"leader":68,"isr":[68,70,69]},{"replicas":[68,69,70],"partitionId":37,"leader":68,"isr":[68,69,70]},{"replicas":[68,69,70],"partitionId":1,"leader":68,"isr":[68,69,70]},{"replicas":[68,69,70],"partitionId":19,"leader":68,"isr":[68,69,70]},{"replicas":[68,70,69],"partitionId":28,"leader":68,"isr":[68,70,69]},{"replicas":[70,69,68],"partitionId":45,"leader":70,"isr":[70,69,68]},{"replicas":[70,69,68],"partitionId":27,"leader":70,"isr":[70,69,68]},{"replicas":[70,68,69],"partitionId":36,"leader":70,"isr":[70,68,69]},{"replicas":[70,68,69],"partitionId":18,"leader":70,"isr":[70,68,69]},{"replicas":[70,69,68],"partitionId":9,"leader":70,"isr":[70,69,68]},{"replicas":[70,68,69],"partitionId":48,"leader":70,"isr":[70,68,69]},{"replicas":[70,69,68],"partitionId":21,"leader":70,"isr":[70,69,68]},{"replicas":[70,69,68],"partitionId":3,"leader":70,"isr":[70,69,68]},{"replicas":[70,68,69],"partitionId":12,"leader":70,"isr":[70,68,69]},{"replicas":[70,68,69],"partitionId":30,"leader":70,"isr":[70,68,69]},{"replicas":[70,69,68],"partitionId":39,"leader":70,"isr":[70,69,68]},{"replicas":[70,69,68],"partitionId":15,"leader":70,"isr":[70,69,68]},{"replicas":[70,68,69],"partitionId":42,"leader":70,"isr":[70,68,69]},{"replicas":[70,68,69],"partitionId":24,"leader":70,"isr":[70,68,69]},{"replicas":[70,68,69],"partitionId":6,"leader":70,"isr":[70,68,69]},{"replicas":[70,69,68],"partitionId":33,"leader":70,"isr":[70,69,68]},{"replicas":[70,68,69],"partitionId":0,"leader":70,"isr":[70,68,69]}],"topicProps":None,"isInternal":True}}
      raise ManagerApiException(e)
    

  def _get_services(self, cluster_name=None):
    clusters = self._root.get('clusters/')['items']

    if cluster_name is not None:
      cluster = [cluster for cluster in clusters if cluster['name'] == cluster_name]
    else:
      cluster = clusters[0]

    return cluster


  def _get_roles(self, cluster_name, service_name, role_type):
    roles = self._root.get('clusters/%(cluster_name)s/services/%(service_name)s/roles' % {'cluster_name': cluster_name, 'service_name': service_name})['items']
    return [role for role in roles if role['type'] == role_type]
