// Selected card data is transient: never localStorage or a confirmed profile fact.
let focus = null;
let project = null;
let projectReady=Promise.resolve();
export function setProjectContextReady(work){projectReady=work;work.catch(()=>{});}
export function waitForProjectContext(){return projectReady;}
export function selectProjectFocus(value) {
  project = value ? {project_id:value.id,revision:value.revision,name:value.name} : null;
  dispatchEvent(new CustomEvent('dubaiio:project-focus', {detail:project}));
}
export function selectFocus(value) {
  focus = value ? { ...value, selected_at: new Date().toISOString() } : null;
  dispatchEvent(new CustomEvent('dubaiio:focus', { detail: focus }));
}
export function requestContext() {
  const context = project ? {project_focus:{project_id:project.project_id,revision:project.revision,selected_at:new Date().toISOString()}} : {};
  if (!focus || Date.now() - Date.parse(focus.selected_at) > 1800000) return context;
  if (focus.task_id) return {...context, task_focus: { task_id: focus.task_id, revision: focus.revision, selected_at: focus.selected_at } };
  return {...context, focus: { ...focus } };
}
export function selectTaskFocus(task) {
  selectFocus({ task_id: task.id, revision: task.revision, entity_name: task.outcome });
}
