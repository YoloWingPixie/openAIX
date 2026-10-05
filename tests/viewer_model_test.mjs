import test from 'node:test';
import assert from 'node:assert/strict';
import { createIndex, searchObjects, resolve, objectLink, readRoute, typeLabel, constraints, constraintSummary, fieldSummary, examplesFor, noteText } from '../viewer/pages/explorer/model.mjs';

const data = {schemas: [
  {path: 'schemas/measures/volume.schema.json', document: {$id: 'urn:volume', title: 'Volume', description: 'A reserved block of airspace.', properties: {altitude: {$ref: 'urn:common#/$defs/Altitude'}}}},
  {path: 'schemas/common.schema.json', document: {$id: 'urn:common', $defs: {Altitude: {type: 'number', minimum: 0}, 'a/b~c': {type: 'boolean'}, denied: false, Recursive: {$ref: '#/$defs/Recursive'}}}},
], authorities: {}, catalogue: {types: [{schema: 'urn:volume', code: 'ROZ'}]}, examples: []};

test('catalogue search combines aliases, descriptions, fields and family filtering', () => {
  const index = createIndex(data);
  assert.deepEqual(searchObjects(index, 'roz altitude', 'Measures').map(item => item.name), ['Volume']);
  assert.equal(searchObjects(index, 'reserved block').length, 1);
  assert.equal(searchObjects(index, 'roz', 'Orders & publications').length, 0);
  assert.equal(searchObjects(index, 'does-not-exist').length, 0);
});

test('point source labels resolve to one searchable object', () => {
  const point = {path: 'schemas/measures/point.schema.json', document: {$id: 'urn:point', title: 'Point', 'x-navigation-profile': 'point', properties: {roles: {type: 'array', items: {enum: ['control', 'initial', 'fix']}}}}};
  const index = createIndex({...data, schemas: [...data.schemas, point], catalogue: {types: [...data.catalogue.types, ...['CP', 'IP', 'ACP', 'BULLSEYE'].map(code => ({schema: 'urn:point', code}))]}});
  for (const alias of ['CP', 'IP', 'ACP', 'BULLSEYE']) assert.deepEqual(searchObjects(index, alias, 'Navigation & facilities').map(item => item.name), ['Point']);
  assert.equal(index.objects.filter(item => item.document.$id === 'urn:point').length, 1);
});

test('references retain document context, escaped pointers and boolean schemas', () => {
  const index = createIndex(data);
  assert.equal(resolve(index, 'urn:volume', 'urn:common#/$defs/Altitude').node.minimum, 0);
  assert.equal(resolve(index, 'urn:common', '#/$defs/a~1b~0c').node.type, 'boolean');
  assert.equal(resolve(index, 'urn:common', '#/$defs/denied').node, false);
  assert.equal(resolve(index, 'urn:common', '#/$defs/Recursive').node.$ref, '#/$defs/Recursive');
  assert.equal(resolve(index, 'urn:common', '#/$defs/missing'), null);
  assert.equal(resolve(index, 'urn:missing', ''), null);
  assert.equal(resolve(index, 'urn:common', '#/%invalid'), null);
});

test('object links preserve identifiers and nested definition routes', () => {
  const route = {id: 'urn:openaix:schema:common:0.1', pointer: '/$defs/a~1b~0c'};
  assert.deepEqual(readRoute(objectLink(route.id, route.pointer)), route);
});

test('constraint presentation retains false, zero and nullable alternatives', () => {
  assert.equal(typeLabel({const: false}), 'false');
  assert.equal(typeLabel({type: ['number', 'null']}), 'number or null');
  assert.deepEqual(constraints({minimum: 0, default: false, deprecated: true}),
    [['Minimum', '0'], ['Documented default', 'false'], ['Deprecated', 'true']]);
});

test('outline labels expose list elements and short enum or nullable choices', () => {
  assert.equal(typeLabel({type: 'array', items: {$ref: 'urn:common#/$defs/AirspaceComponent'}}), 'AirspaceComponent[]');
  assert.equal(typeLabel({enum: ['left', 'right']}), '"left" | "right"');
  assert.equal(typeLabel({anyOf: [{$ref: '#/$defs/Altitude'}, {type: 'null'}]}), 'Altitude | null');
  assert.equal(typeLabel({enum: ['A', 'B', 'C', 'D']}), '4 choices');
});

test('conditional summaries explain the condition and preserve optional-field semantics', () => {
  const rule = {if: {properties: {airspace_type: {const: 'ClassB'}}, required: ['airspace_type']},
    then: {properties: {airspace_class_code: {enum: ['B', ' ', '']}}}};
  assert.equal(constraintSummary(rule), 'If airspace_type: = "ClassB" → airspace_class_code (if supplied): one of "B", " ", ""');
  assert.equal(constraintSummary({if: {properties: {reference: {const: 'FL'}}}, then: {required: ['unit']}, else: {not: {required: ['unit']}}}),
    'If reference is absent or (= "FL") → required: unit; otherwise unit must be absent');
});

test('presence and exclusion summaries preserve all/any/exactly-one distinctions', () => {
  assert.equal(constraintSummary({if: {anyOf: [{required: ['tacan']}, {required: ['refueling_method']}]}, then: {properties: {role: {const: 'refueling'}}, required: ['role']}}),
    'If at least one of (tacan is present | refueling_method is present) → role: = "refueling"');
  assert.equal(constraintSummary({required: ['target', 'changes'], not: {required: ['base_order']}}), 'required: target, changes; base_order must be absent');
  assert.equal(constraintSummary({not: {required: ['a', 'b']}}), 'a, b must not all be present');
  assert.equal(constraintSummary({oneOf: [{required: ['position']}, {required: ['description']}]}), 'exactly one of (required: position | required: description)');
});

test('summaries retain numeric boundaries, false values and unsupported rules', () => {
  assert.equal(fieldSummary({type: 'number', minimum: 0, exclusiveMaximum: 360}), 'number · Minimum: 0 · Less than: 360');
  assert.equal(constraintSummary({const: false}), '= false');
  assert.equal(constraintSummary({additionalProperties: false}), 'additional fields forbidden');
  assert.match(constraintSummary({dependentRequired: {a: ['b']}}), /dependentRequired.*a.*b/);
  assert.equal(constraintSummary({$ref: '#/$defs/Altitude', minimum: 0}), 'Altitude; Minimum: 0');
  assert.equal(fieldSummary({$ref: '#/$defs/ControlMeasureSelection', 'x-point-roles': ['initial', 'fix']}), 'ControlMeasureSelection · Allowed point roles: ["initial","fix"]');
  assert.equal(constraintSummary({'x-point-roles': ['egress', 'gate', 'fix']}), 'Allowed point roles: ["egress","gate","fix"]');
});

test('minimal and maximal examples come first, then the curated examples; definitions use their own pair', () => {
  const pairs = {
    'urn:volume': {minimal: {document: {id: 'roz'}, yaml: 'id: roz\n'}, maximal: {document: {id: 'roz', name: 'ROZ'}, yaml: 'id: roz\nname: ROZ\n'},
      notes: [{path: 'resources', reason: 'alternative', instead_of: ['resources_ref']}], definitions: {}},
    'urn:common': {minimal: {document: {}}, maximal: {document: {}}, notes: [], definitions: {'a/b~c': {minimal: {document: true, yaml: 'true\n'}, maximal: {document: false, yaml: 'false\n'}, notes: []}}},
  };
  const index = createIndex({...data, example_pairs: pairs, examples: [{path: 'examples/roz.json', document: {$schema: 'urn:volume'}}]});
  assert.deepEqual(examplesFor(index, 'urn:volume', '').map(item => item.path), ['Minimal', 'Maximal', 'examples/roz.json']);
  assert.equal(examplesFor(index, 'urn:volume', '')[1].notes.length, 1);
  assert.deepEqual(examplesFor(index, 'urn:common', '/$defs/a~1b~0c').map(item => item.document), [true, false]);
  assert.deepEqual(examplesFor(index, 'urn:common', '/$defs/a~1b~0c/properties'), []);
});

test('notes say which branch an example uses and why a field is left out', () => {
  assert.equal(noteText({path: 'resources_ref', reason: 'alternative', instead_of: ['resources']}), 'resources_ref: left out; it is an alternative to resources.');
  assert.equal(noteText({path: '/', selected: 'resources', alternatives: ['resources_ref']}), 'Document: uses the resources branch; the other branches are resources_ref.');
  assert.match(noteText({path: 'a/b', reason: 'conditional'}), /^a\/b: left out; a conditional rule/);
});
