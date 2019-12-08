// Licensed to Cloudera, Inc. under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  Cloudera, Inc. licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import * as ko from 'knockout';

const proxiedKoRegister = ko.components.register;
const registeredComponents = [];

ko.components.register = function() {
  // This guarantees a ko component is only registered once
  // Some currently get registered twice when switching between notebook and editor
  if (registeredComponents.indexOf(arguments[0]) === -1) {
    registeredComponents.push(arguments[0]);
    return proxiedKoRegister.apply(this, arguments);
  }
};
