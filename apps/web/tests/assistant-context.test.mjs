import test from 'node:test';
import assert from 'node:assert/strict';

async function context(){globalThis.dispatchEvent=()=>{};return import('../assistant-context.js?test='+Math.random());}
test('project membership reference can accompany selected task without sending shared text',async()=>{
  const c=await context();c.selectProjectFocus({id:'project',revision:3,name:'Moving home',context:'Private shared notes'});
  c.selectTaskFocus({id:'task',revision:2,outcome:'Arrange movers'});
  const body=c.requestContext();
  assert.equal(body.project_focus.project_id,'project');assert.equal(body.task_focus.task_id,'task');
  assert(!JSON.stringify(body).includes('Private shared notes'));assert(!JSON.stringify(body).includes('Moving home'));
  c.selectFocus(null);assert(body.project_focus);assert.equal(c.requestContext().task_focus,undefined);
  c.selectProjectFocus(null);assert.deepEqual(c.requestContext(),{});
});
test('model turns can wait for verified workspace context and fail closed when it is unavailable',async()=>{
  const c=await context();let release;
  c.setProjectContextReady(new Promise(resolve=>release=resolve));let ready=false;
  const wait=c.waitForProjectContext().then(()=>ready=true);await Promise.resolve();assert.equal(ready,false);
  release();await wait;assert.equal(ready,true);
  c.setProjectContextReady(Promise.reject(Error('unavailable')));
  await assert.rejects(c.waitForProjectContext(),/unavailable/);
});
