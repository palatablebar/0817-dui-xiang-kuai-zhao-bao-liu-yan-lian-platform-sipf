import {element, pretty} from './client.js';

const labels = {READY:'通过', MISMATCH:'差异待复核', PENDING:'待复核', APPROVED:'已签发', HELD:'已暂缓',
  BLOCKED:'阻断', CARRY_OVER:'沿用', ADJUDICATED:'新裁', RETAINED:'保留', QUARANTINED:'隔离'};
const reasons = {CASE_INCOMPLETE:'控制行缺失', MATERIAL_CONFLICT:'材料冲突', IDENTITY_UNKNOWN:'身份不明', REFERENCE_CHANGED:'引用变化'};
const verdicts = {LEGAL_HOLD:'合法保全', LIVE_SNAPSHOT:'快照引用', RETENTION:'保留期', RECLAIM:'回收候选'};
const headers = ['业务分组', '输入行', '计算值', '参考值', '判定'];

export function badge(status) {
  return element('span', labels[status] || status, {class:'badge', 'data-result':status, title: status});
}

export function snapshot(report, selected, stage) {
  const stats = report.intake;
  document.querySelector('[data-metric="input"]').textContent = stats.input;
  document.querySelector('[data-metric="accepted"]').textContent = stats.accepted;
  document.querySelector('[data-metric="isolated"]').textContent = stats.rejected;
  document.querySelector('[data-metric="cases"]').textContent = report.cases?.length ?? '—';
  const table = document.querySelector('#rows');
  table.replaceChildren();
  const head = element('tr');
  const body = table.createTBody();
  if (stage === 'intake') {
    head.append(...['源行', '记录键', '业务分组', '原因码'].map(title => element('th', title, {scope:'col'})));
    for (const item of stats.isolation) {
      const tr = body.insertRow();
      tr.append(...[item.line,item.record,item.case,item.reason].map(value=>element('td',value)));
    }
    if (!stats.isolation.length) body.insertRow().insertCell().textContent = '当前文件没有隔离行';
  } else {
    head.append(...headers.map(title => element('th', title, {scope:'col'})));
    for (const row of report.cases || []) {
      const tr = body.insertRow();
      const button = element('button',row.case,{type:'button','data-case':row.case,'aria-pressed':String(row.case===selected)});
      tr.insertCell().append(button);
      [row.records.length, row.measure?.value ?? '—', row.measure?.expected ?? '—'].forEach(value=>tr.insertCell().textContent=value);
      tr.insertCell().append(badge(row.status));
    }
  }
  table.createTHead().append(head);
  const picked = report.cases?.find(row=>row.case===selected);
  document.querySelector('#detail-title').textContent = picked ? `分组 ${picked.case}` : '采信摘要';
  const shown = picked ? picked.measure?.evidence ?? picked.prep?.details ?? {原因:picked.status} : stats.reasons;
  document.querySelector('#detail').textContent = pretty(shown);
  document.querySelector('#counts').textContent = report.balance ? `行数 ${report.balance.accounted}/${report.balance.input} · ${report.balance.ready} 组通过` : `采信 ${stats.accepted} 行 · 隔离 ${stats.rejected} 行`;
}

export function history(items, active) {
  const target = document.querySelector('#history');
  target.replaceChildren();
  for (const run of items) {
    const button = element('button', run.id.slice(0,10), {'data-run':run.id,'aria-pressed':String(run.id===active),type:'button'});
    const item = element('li');
    item.append(button, badge(run.status));
    if (run.blocked) item.append(badge('BLOCKED'));
    target.append(item);
  }
  if (!items.length) target.append(element('li','尚无执行批次'));
}

export function handover(report) {
  const panel = document.querySelector('#closure');
  const doc = report.closure;
  if (!doc) { panel.hidden = true; return; }
  panel.hidden = false;
  document.querySelector('#closure-basis').textContent = doc.basis ? `依据批次 ${doc.basis.slice(0,10)}` : '无签发依据';
  const s = doc.summary;
  document.querySelector('#closure-summary').textContent =
    `沿用 ${s.carried} · 新裁 ${s.adjudicated} · 保留 ${s.retained} · 隔离 ${s.quarantined}${doc.blocked ? ' · 阻断批次' : ''}`;
  const table = document.querySelector('#closure-rows');
  table.replaceChildren();
  const head = element('tr');
  head.append(...['对象', '动作', '结论', '说明'].map(title => element('th', title, {scope:'col'})));
  table.createTHead().append(head);
  const body = table.createTBody();
  for (const [key, item] of Object.entries(doc.objects)) {
    const tr = body.insertRow();
    tr.insertCell().textContent = key;
    tr.insertCell().append(badge(item.action));
    tr.insertCell().textContent = verdicts[item.conclusion] || item.conclusion || '—';
    tr.insertCell().textContent = reasons[item.reason] || (item.action==='RETAINED' ? '保留上一版' : '');
  }
  const diff = doc.reconciliation;
  document.querySelector('#closure-diff').textContent = diff.balanced
    ? '源对象、快照定义与隔离项全部对上'
    : pretty({源对象缺失:diff.source_missing, 快照定义缺失:diff.definition_missing, 无主引用:diff.orphan_refs, 隔离项:diff.quarantined});
}
