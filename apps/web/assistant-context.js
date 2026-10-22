// Selected card data is transient: never localStorage or a confirmed profile fact.
let focus = null;
export function selectFocus(value) {
  focus = value ? { ...value, selected_at: new Date().toISOString() } : null;
  dispatchEvent(new CustomEvent('dubaiio:focus', { detail: focus }));
}
export function requestContext() {
  if (!focus || Date.now() - Date.parse(focus.selected_at) > 1800000) return {};
  if (focus.task_id) return { task_focus: { task_id: focus.task_id, revision: focus.revision, selected_at: focus.selected_at } };
  return { focus: { ...focus } };
}
export function selectTaskFocus(task) {
  selectFocus({ task_id: task.id, revision: task.revision, entity_name: task.outcome });
}
