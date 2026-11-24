import {element} from './client.js';

function zone(target, className, text) {
  const box = element('div', undefined, {class:className});
  if (text) box.append(element('span',text));
  target.append(box);
  return box;
}

function fill(layer, value, max, label) {
  const mark = zone(layer, 'mark-piece', label);
  mark.style.setProperty('--part', `${Math.max(0,Math.min(100,100*value/Math.max(1,max)))}%`);
  return mark;
}

export function visualize(report, selected) {
  const target = document.querySelector('#visual');
  const row = report.cases?.find(item=>item.case===selected && item.measure);
  target.replaceChildren();
  if (!row) { target.append(element('p','该分组暂无计算值')); return; }
  const {evidence:e, value, expected, unit} = row.measure;
  render(target, e, value, expected, unit);
}

function render(target,e,value,expected,unit) {
  const labels={LIVE_SNAPSHOT:'快照引用',LEGAL_HOLD:'合法保全',RETENTION:'保留期',RECLAIM:'回收候选'};
  const rows=zone(target,'retention-list');
  for(const [id,reason] of Object.entries(e)) zone(rows,`retention-item ${reason==='RECLAIM'?'eligible':''}`,`对象 ${id} · ${labels[reason]}`);
  zone(target,'retention-total',`候选容量 ${value} 字节`);
}
