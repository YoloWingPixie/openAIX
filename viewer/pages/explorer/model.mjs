export function createIndex(data) {
  const schemas = new Map(data.schemas.map(item => [item.document.$id, item]));
  const definitions = new Map();
  for (const entry of data.catalogue.types) {
    if (!definitions.has(entry.schema)) definitions.set(entry.schema, []);
    definitions.get(entry.schema).push(entry);
  }
  const objects = data.schemas.map(item => {
    const aliases = data.catalogue.types.filter(entry => entry.schema === item.document.$id).map(entry => entry.code);
    const filename = item.path.split('/').at(-1).replace('.schema.json', '');
    const name = (item.document.title || filename).replace(/^openAIX\s*/i, '');
    const family = item.document['x-navigation-profile'] ? 'Navigation & facilities' : item.path.includes('/measures/') ? 'Measures' :
      ['ato', 'aco', 'opord', 'spins', 'frago', 'jiptl', 'tst'].includes(filename) ? 'Orders & publications' : 'Resources & shared types';
    return {...item, name, family, aliases, search: [name, filename, ...aliases, JSON.stringify(item.document)].join(' ').toLowerCase()};
  }).sort((a, b) => a.name.localeCompare(b.name));
  return {schemas, definitions, objects, examples: data.examples, pairs: data.example_pairs || {}, authorities: data.authorities || {}};
}

export function searchObjects(index, query, family = '') {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return index.objects.filter(item => (!family || item.family === family) && words.every(word => item.search.includes(word)));
}

export function objectLink(id, pointer = '') {
  return '#' + new URLSearchParams({id, pointer}).toString();
}

export function readRoute(hash) {
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  return {id: params.get('id'), pointer: params.get('pointer') || ''};
}

export function resolve(index, base, reference) {
  const [documentId, fragment = ''] = reference.split('#');
  const id = documentId || base;
  let node = index.schemas.get(id)?.document;
  let pointer;
  try { pointer = decodeURIComponent(fragment); }
  catch { return null; }
  if (pointer && !pointer.startsWith('/')) return null;
  for (const token of pointer.split('/').slice(1)) {
    const key = token.replace(/~1/g, '/').replace(/~0/g, '~');
    if (!node || typeof node !== 'object' || !Object.hasOwn(node, key)) return null;
    node = node[key];
  }
  return node === undefined ? null : {id, pointer, node};
}

export function typeLabel(node) {
  if (node === true) return 'Any value';
  if (node === false) return 'Not permitted';
  if (Object.hasOwn(node, 'const')) return JSON.stringify(node.const);
  if (node.$ref) return node.$ref.split('/').at(-1).split(':').slice(-2, -1)[0] || node.$ref.split('/').at(-1);
  if (node.enum) return node.enum.length <= 3 ? node.enum.map(value => JSON.stringify(value)).join(' | ') : `${node.enum.length} choices`;
  if (node.type === 'array') return typeLabel(node.items || {}) + '[]';
  if (node.type) return Array.isArray(node.type) ? node.type.join(' or ') : node.type;
  if (node.oneOf || node.anyOf) {
    const alternatives = node.oneOf || node.anyOf;
    if (alternatives.length <= 3 && alternatives.every(child => child.$ref || child.type || Object.hasOwn(child, 'const'))) return alternatives.map(typeLabel).join(' | ');
    return `${node.oneOf ? 'one of' : 'any of'} ${alternatives.length} types`;
  }
  if (node.allOf) return 'Combined constraints';
  if (node.if) return 'Conditional rule';
  if (node.properties) return 'Object fields';
  if (node.required) return 'Required fields';
  return 'Any value';
}

export function constraints(node) {
  const labels = {minimum: 'Minimum', maximum: 'Maximum', exclusiveMinimum: 'Greater than', exclusiveMaximum: 'Less than',
    minLength: 'Minimum characters', maxLength: 'Maximum characters', minItems: 'Minimum items', maxItems: 'Maximum items',
    minProperties: 'Minimum fields', maxProperties: 'Maximum fields', pattern: 'Pattern', format: 'Format', multipleOf: 'Multiple of',
    default: 'Documented default', uniqueItems: 'Unique items', deprecated: 'Deprecated', 'x-catalog': 'References catalogue', 'x-measure-kinds': 'Allowed referenced objects', 'x-point-roles': 'Allowed point roles'};
  return Object.entries(labels).filter(([key]) => Object.hasOwn(node, key)).map(([key, label]) => [label, JSON.stringify(node[key])]);
}

const ANNOTATION_LABELS = new Set(['Documented default', 'Deprecated']);

export function fieldSummary(node) {
  if (typeof node === 'boolean') return typeLabel(node);
  const rules = constraints(node).filter(([label]) => !ANNOTATION_LABELS.has(label));
  return [typeLabel(node), ...rules.map(([label, value]) => `${label}: ${value}`)].join(' · ');
}

export function constraintSummary(node, mode = 'rule') {
  if (typeof node === 'boolean') return node ? 'any value allowed' : 'no value allowed';
  const parts = [];
  const handled = new Set(['$schema', '$id', '$defs', 'title', 'description', 'default', 'deprecated', 'examples', 'readOnly', 'writeOnly']);
  if (node.$ref) { parts.push(typeLabel({$ref: node.$ref})); handled.add('$ref'); }
  if (node.if) {
    let rule = 'If ' + constraintSummary(node.if, 'condition');
    if (Object.hasOwn(node, 'then')) rule += ' → ' + constraintSummary(node.then);
    if (Object.hasOwn(node, 'else')) rule += '; otherwise ' + constraintSummary(node.else);
    parts.push(rule);
    ['if', 'then', 'else'].forEach(key => handled.add(key));
  }
  if (Object.hasOwn(node, 'const')) { parts.push('= ' + JSON.stringify(node.const)); handled.add('const'); }
  if (node.enum) { parts.push('one of ' + node.enum.map(value => JSON.stringify(value)).join(', ')); handled.add('enum'); }
  if (node.type) { parts.push(typeLabel({type: node.type})); handled.add('type'); }
  const required = new Set(node.required || []);
  for (const [name, field] of Object.entries(node.properties || {})) {
    if (mode === 'condition' && !required.has(name)) parts.push(name + ' is absent or (' + constraintSummary(field) + ')');
    else parts.push(name + (required.has(name) ? '' : ' (if supplied)') + ': ' + constraintSummary(field));
    required.delete(name);
  }
  if (required.size) parts.push(mode === 'condition' ? [...required].join(' and ') + (required.size === 1 ? ' is present' : ' are present') : 'required: ' + [...required].join(', '));
  handled.add('properties'); handled.add('required');
  for (const [keyword, label] of [['allOf', 'all of'], ['anyOf', 'at least one of'], ['oneOf', 'exactly one of']]) {
    if (node[keyword]) parts.push(label + ' (' + node[keyword].map(child => constraintSummary(child, mode)).join(' | ') + ')');
    handled.add(keyword);
  }
  if (node.not) {
    const fields = node.not.required;
    if (fields?.length && Object.keys(node.not).length === 1) {
      parts.push(fields.join(', ') + (fields.length === 1 ? ' must be absent' : ' must not all be present'));
    } else parts.push('must not match (' + constraintSummary(node.not) + ')');
    handled.add('not');
  }
  for (const [keyword, label] of [['items', 'each item'], ['contains', 'contains'], ['propertyNames', 'field names']]) {
    if (Object.hasOwn(node, keyword)) parts.push(label + ': ' + constraintSummary(node[keyword]));
    handled.add(keyword);
  }
  if (Object.hasOwn(node, 'additionalProperties')) {
    parts.push(typeof node.additionalProperties === 'boolean'
      ? 'additional fields ' + (node.additionalProperties ? 'allowed' : 'forbidden')
      : 'additional fields: ' + constraintSummary(node.additionalProperties));
    handled.add('additionalProperties');
  }
  for (const [label, value] of constraints(node)) {
    if (!ANNOTATION_LABELS.has(label)) parts.push(label + ': ' + value);
  }
  for (const key of Object.keys(node)) {
    if (handled.has(key) || key.startsWith('x-')) continue;
    if (constraints({[key]: node[key]}).length) continue;
    parts.push(key + ': ' + JSON.stringify(node[key]));
  }
  return parts.join('; ') || 'any value allowed';
}

export function noteText(note) {
  const path = note.path === '/' ? 'Document' : note.path;
  if (note.selected) return `${path}: uses the ${note.selected} branch; the other branches are ${note.alternatives.join(', ')}.`;
  if (note.reason === 'alternative') return `${path}: left out; it is an alternative to ${note.instead_of.join(', ')}.`;
  if (note.reason === 'conditional') return `${path}: left out; a conditional rule of the schema does not let it occur with these values.`;
  return `${path}: left out; the OIR scenario has no value for it.`;
}

export function examplesFor(index, id, pointer) {
  const pair = pointer ? index.pairs[id]?.definitions?.[pointer.replace(/^\/\$defs\//, '').replace(/~1/g, '/').replace(/~0/g, '~')] : index.pairs[id];
  const generated = pair && (!pointer || pointer.match(/^\/\$defs\/[^/]+$/)) ? ['minimal', 'maximal'].filter(name => pair[name]).map(name => ({
    path: name === 'minimal' ? 'Minimal' : 'Maximal', document: pair[name].document, yaml: pair[name].yaml, notes: name === 'maximal' ? pair.notes : []})) : [];
  return [...generated, ...(pointer ? [] : index.examples.filter(item => item.document.$schema === id))];
}
