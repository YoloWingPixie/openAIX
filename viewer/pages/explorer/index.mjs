import { createIndex, searchObjects, objectLink, readRoute, resolve, typeLabel, constraints, constraintSummary, fieldSummary, examplesFor, noteText } from './model.mjs';

function el(tag, className = '', text = '') {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== '') node.textContent = text;
  return node;
}

function link(text, href) {
  const node = el('a', 'text-link', text);
  node.href = href;
  return node;
}

function disclosure(label, render) {
  const details = el('details', 'disclosure');
  details.append(el('summary', '', label));
  details.addEventListener('toggle', () => {
    if (details.open && details.children.length === 1) details.append(render());
  });
  return details;
}

function codeView(value, yaml = null) {
  const body = el('div', 'code-view');
  const text = yaml ?? JSON.stringify(value, null, 2);
  const copy = el('button', 'copy-button', yaml === null ? 'Copy JSON' : 'Copy YAML');
  copy.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(text); copy.textContent = 'Copied'; }
    catch { copy.textContent = 'Select the text below to copy'; }
  });
  body.append(copy, el('pre', 'raw-schema', text));
  return body;
}

function schemaView(index, node, base, trail = new Set(), expandReference = false) {
  const body = el('div', 'schema-body');
  if (typeof node === 'boolean') {
    body.append(el('p', '', typeLabel(node)));
    return body;
  }
  if (node.description) body.append(el('p', 'description', node.description));
  if (node.$ref) {
    const target = resolve(index, base, node.$ref);
    if (!target) body.append(el('p', 'notice error', 'Unresolved reference: ' + node.$ref));
    else {
      const key = target.id + '#' + target.pointer;
      const name = target.node.title || target.pointer.split('/').at(-1) || typeLabel(node);
      body.append(link('Open ' + name + ' ↗', objectLink(target.id, target.pointer)));
      if (trail.has(key)) body.append(el('p', 'muted', 'Recursive reference — follow the link to review this type.'));
      else if (expandReference) body.append(schemaView(index, target.node, target.id, new Set([...trail, key]), true));
      else body.append(disclosure('Expand ' + name, () => schemaView(index, target.node, target.id, new Set([...trail, key]))));
    }
  }
  const rules = constraints(node);
  if (rules.length) {
    const list = el('dl', 'constraints');
    for (const [name, value] of rules) list.append(el('dt', '', name), el('dd', '', value));
    body.append(list);
  }
  if (node.enum || Object.hasOwn(node, 'const')) {
    const choices = el('div', 'choices');
    for (const value of node.enum || [node.const]) {
      const choice = el('div', 'choice');
      choice.append(el('code', '', JSON.stringify(value)));
      if (node['x-enum-descriptions']?.[value]) choice.append(el('span', 'muted', node['x-enum-descriptions'][value]));
      choices.append(choice);
    }
    body.append(choices);
  }
  if (node.properties) {
    const fields = el('div', 'fields');
    for (const [name, field] of Object.entries(node.properties)) {
      const card = el('article', 'field');
      const details = disclosure('', () => schemaView(index, field, base, trail, true));
      details.classList.add('field-details');
      const heading = details.querySelector('summary');
      heading.className = 'field-heading';
      heading.append(el('code', 'field-name', name), el('span', node.required?.includes(name) ? 'badge required' : 'badge', node.required?.includes(name) ? 'Required' : 'Optional'), el('span', 'field-type', fieldSummary(field)));
      card.append(details);
      fields.append(card);
    }
    body.append(fields);
  }
  if (node.required?.length && !node.properties) body.append(el('p', 'notice', 'Required together: ' + node.required.join(', ')));
  for (const [keyword, label] of [['oneOf', 'Exactly one alternative'], ['anyOf', 'At least one alternative'], ['allOf', 'All constraints apply']]) {
    if (!node[keyword]) continue;
    const group = el('section', 'composition');
    group.append(el('h3', '', label));
    node[keyword].forEach((branch, i) => group.append(disclosure(`${i + 1}. ${constraintSummary(branch)}`, () => schemaView(index, branch, base, trail))));
    body.append(group);
  }
  for (const [keyword, label] of [['items', 'List items'], ['additionalProperties', 'Additional fields'], ['propertyNames', 'Field names'], ['if', 'When this condition matches'], ['then', 'Apply when matched'], ['else', 'Apply otherwise'], ['not', 'Must not match'], ['contains', 'List must contain']]) {
    if (!Object.hasOwn(node, keyword)) continue;
    if (typeof node[keyword] === 'boolean') body.append(el('p', 'muted', label + ': ' + (node[keyword] ? 'allowed' : 'not allowed')));
    else body.append(disclosure(label + ' — ' + constraintSummary(node[keyword]), () => schemaView(index, node[keyword], base, trail)));
  }
  for (const [pattern, child] of Object.entries(node.patternProperties || {})) body.append(disclosure('Keys matching ' + pattern, () => schemaView(index, child, base, trail)));
  if (node.$defs) {
    const types = el('section', 'composition');
    types.append(el('h3', '', 'Defined types'));
    const links = el('div', 'definition-links');
    for (const name of Object.keys(node.$defs)) links.append(link(name, objectLink(base, '/$defs/' + name.replace(/~/g, '~0').replace(/\//g, '~1'))));
    types.append(links);
    body.append(types);
  }
  return body;
}

function sourceView(index, id) {
  const body = el('div', 'source-view');
  const entries = index.definitions.get(id) || [];
  if (!entries.length) return el('p', 'notice', 'No catalogue entry is recorded for this schema.');
  body.append(el('h2', '', 'Definition sources'));
  for (const entry of entries) {
    const card = el('article', 'source-card');
    card.append(el('h3', '', entry.code + ' · ' + entry.name));
    const citation = entry.definition_source;
    const source = citation && index.authorities[citation.source];
    if (source) {
      const url = new URL(source.url);
      card.append(['https:', 'http:'].includes(url.protocol) ? link(source.title + ' ↗', source.url) : el('strong', '', source.title));
      card.append(el('p', 'muted', source.publisher + ' · ' + source.edition));
      card.append(el('p', '', citation.locator));
    } else {
      card.append(el('p', 'muted', 'No definition source is recorded in the catalogue.'));
    }
    body.append(card);
  }
  return body;
}

export async function mountExplorer(root) {
  try {
    const response = await fetch('/api/review');
    if (!response.ok) throw new Error('Server returned ' + response.status);
    const index = createIndex(await response.json());
    root.replaceChildren();
    root.className = 'workspace';
    const sidebar = el('aside', 'sidebar');
    const intro = el('div', 'sidebar-intro');
    intro.append(el('p', 'eyebrow', 'SCHEMA EXPLORER'), el('h1', '', 'Explore the contract'), el('p', 'muted', `${index.objects.length} objects · one shared language`));
    const searchLabel = el('label', 'control-label', 'Find an object or field');
    const search = el('input', 'search');
    search.type = 'search'; search.placeholder = 'Airspace, CAP, altitude…'; search.id = 'object-search'; searchLabel.htmlFor = search.id;
    const familyLabel = el('label', 'control-label', 'Object family');
    const family = el('select', 'family'); family.id = 'family'; familyLabel.htmlFor = family.id;
    for (const name of ['', ...new Set(index.objects.map(item => item.family))]) {
      const option = el('option', '', name || 'All families'); option.value = name; family.append(option);
    }
    const count = el('p', 'result-count'); count.setAttribute('aria-live', 'polite');
    const list = el('nav', 'object-list'); list.setAttribute('aria-label', 'Schema objects');
    sidebar.append(intro, searchLabel, search, familyLabel, family, count, list);
    const content = el('main', 'content'); content.id = 'content'; content.tabIndex = -1;
    root.append(sidebar, content);
    let tab = 'Fields';
    let selectedId;

    function renderList() {
      list.replaceChildren();
      const results = searchObjects(index, search.value, family.value);
      count.textContent = `${results.length} ${results.length === 1 ? 'object' : 'objects'}`;
      for (const item of results) {
        const anchor = link('', objectLink(item.document.$id)); anchor.className = 'object-link';
        if (item.document.$id === selectedId) anchor.setAttribute('aria-current', 'page');
        anchor.append(el('span', 'object-name', item.name), el('span', 'object-family', item.aliases.join(' · ') || item.family));
        list.append(anchor);
      }
      if (!results.length) list.append(el('p', 'empty', 'No matches. Try a field name or clear the filters.'));
    }

    function renderContent() {
      const route = readRoute(location.hash);
      const item = index.objects.find(item => item.document.$id === route.id) ||
        (route.id ? undefined : index.objects.find(item => item.path.endsWith('/orbit.schema.json')));
      content.replaceChildren();
      selectedId = item?.document.$id;
      renderList();
      if (!item) { content.append(el('h1', '', 'Object not found'), el('p', '', 'Choose an object from the list.')); return; }
      selectedId = item.document.$id;
      const selected = resolve(index, selectedId, '#' + route.pointer);
      if (!selected) { content.append(el('h1', '', 'Definition not found'), link('Return to ' + item.name, objectLink(selectedId))); return; }
      const node = selected.node;
      const header = el('section', 'object-header');
      header.append(el('p', 'eyebrow', item.family.toUpperCase()));
      if (route.pointer) header.append(link('← ' + item.name, objectLink(selectedId)));
      header.append(el('h1', '', route.pointer ? node.title || route.pointer.split('/').at(-1) : item.name));
      if (node.description) header.append(el('p', 'lead', node.description));
      const meta = el('div', 'object-meta');
      meta.append(el('span', 'badge', 'Draft'), el('span', 'muted', item.path + route.pointer));
      header.append(meta);
      const nav = el('nav', 'view-tabs'); nav.setAttribute('aria-label', 'Object views');
      const panel = el('section', 'panel');
      for (const name of ['Fields', 'Examples', 'Sources', 'Schema']) {
        const button = el('button', 'view-tab', name); button.type = 'button'; button.setAttribute('aria-pressed', String(tab === name));
        button.addEventListener('click', () => { tab = name; renderContent(); content.querySelectorAll('.view-tab')[[...nav.children].indexOf(button)].focus(); });
        nav.append(button);
      }
      content.append(header, nav, panel);
      if (tab === 'Fields') {
        panel.append(el('p', 'muted field-guide', 'Click a field to expand its shape and details. Conditional rules can add requirements.'));
        panel.append(schemaView(index, typeof node === 'boolean' ? node : {...node, description: undefined}, selectedId, new Set([selectedId + '#' + route.pointer])));
      }
      if (tab === 'Sources') panel.append(sourceView(index, selectedId));
      if (tab === 'Examples') {
        const examples = examplesFor(index, selectedId, route.pointer);
        panel.append(el('h2', '', 'Example documents'));
        if (examples.length) {
          const label = el('label', 'control-label', 'Example document'); label.htmlFor = 'example-document';
          const select = el('select', 'family'); select.id = 'example-document';
          examples.forEach((example, i) => { const option = el('option', '', example.path.replace('examples/', '')); option.value = String(i); select.append(option); });
          const preview = el('div', 'example-preview');
          const show = () => {
            const example = examples[Number(select.value)];
            preview.replaceChildren(codeView(example.document, example.yaml));
            if (example.notes?.length) preview.append(disclosure('Alternative branches and fields left out', () => {
              const list = el('ul', 'example-notes');
              for (const note of example.notes) list.append(el('li', '', noteText(note)));
              return list;
            }));
          };
          select.addEventListener('change', show); show();
          panel.append(label, select, preview);
        }
        if (!examples.length) panel.append(el('p', 'notice', 'No standalone example is recorded for this schema. Shared types appear inside their consuming documents.'));
      }
      if (tab === 'Schema') {
        panel.append(codeView(node));
      }
    }
    search.addEventListener('input', renderList);
    family.addEventListener('change', renderList);
    window.addEventListener('hashchange', () => { tab = 'Fields'; renderContent(); content.focus(); });
    renderContent();
  } catch (error) {
    root.replaceChildren(el('h1', '', 'The schema viewer could not load'), el('p', '', error.message));
    const retry = el('button', 'copy-button', 'Try again'); retry.addEventListener('click', () => mountExplorer(root)); root.append(retry);
  }
}
