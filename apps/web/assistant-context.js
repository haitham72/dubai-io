// Selected card data is transient: never localStorage or a confirmed profile fact.
let focus = null;
export function selectFocus(value) {
  focus = value ? { ...value, selected_at: new Date().toISOString() } : null;
  dispatchEvent(new CustomEvent('dubaiio:focus', { detail: focus }));
}
export function requestContext() {
  if (!focus || Date.now() - Date.parse(focus.selected_at) > 1800000) return {};
  return { focus: { ...focus } };
}
