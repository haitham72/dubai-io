// One tiny external-store factory for the module stores.
//
// Every screen/service kept its own copy of the same plumbing (a `listeners`
// set, a `set(patch)` merge + notify, a `useSyncExternalStore` hook). Only
// that plumbing lives here; each module keeps its own State type, initial
// value and side effects (pass those via `onSet`).
import { useSyncExternalStore } from "react";

export interface Store<S> {
  get: () => S;
  set: (patch: Partial<S>) => void;
  update: (fn: (s: S) => S) => void;
  subscribe: (listener: () => void) => () => void;
  use: <T>(select: (s: S) => T) => T;
  useState: () => S;
}

export function createStore<S>(initial: S, onSet?: (state: S, patch: Partial<S>) => void): Store<S> {
  let state = initial;
  const listeners = new Set<() => void>();
  const set = (patch: Partial<S>) => {
    state = { ...state, ...patch };
    onSet?.(state, patch);
    listeners.forEach((l) => l());
  };
  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };
  const get = () => state;
  const use = <T>(select: (s: S) => T): T => useSyncExternalStore(subscribe, () => select(get()));
  const useState = (): S => useSyncExternalStore(subscribe, get);
  /** Replace the whole value (for array/record shapes where merge-patch makes no sense). */
  const update = (fn: (s: S) => S) => {
    state = fn(state);
    onSet?.(state, {});
    listeners.forEach((l) => l());
  };
  return { get, set, subscribe, use, useState, update };
}
