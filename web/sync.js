(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  // 서로 다른 항목의 변경은 유지하고, 같은 항목의 충돌은 사용자 선택 후 반영한다.
  function mergeWorkspace(base, local, remote) {
    function mergeRows(before, mine, theirs, level) {
      const a = new Map(before.map(row => [row.id, row]));
      const b = new Map(mine.map(row => [row.id, row]));
      const c = new Map(theirs.map(row => [row.id, row]));
      const rows = [];
      for (const id of new Set([...c.keys(), ...b.keys()])) {
        const old = a.get(id), own = b.get(id), other = c.get(id);
        if (old && !own) continue;
        if (!own) { rows.push(clone(other)); continue; }
        if (!other) { if (!old || !equal(own, old)) rows.push(clone(own)); continue; }
        const result = clone(other);
        for (const key of Object.keys(own)) {
          if (key === (level === 2 ? 'topics' : 'todos') && level) continue;
          if (!old || !equal(own[key], old[key])) result[key] = clone(own[key]);
        }
        if (level) { const key = level === 2 ? 'topics' : 'todos'; result[key] = mergeRows(old?.[key] || [], own[key], other[key], level - 1); }
        rows.push(result);
      }
      return rows;
    }
    if (base.workspaces || local.workspaces || remote.workspaces) {
      return {version: 1, topics: [], workspaces: mergeRows(root.TaskStore.workspaces(base), root.TaskStore.workspaces(local), root.TaskStore.workspaces(remote), 2)};
    }
    return {version: 1, topics: mergeRows(base.topics, local.topics, remote.topics, 1)};
  }
  class SyncClient {
    constructor(options) {
      this.base = options.base.replace(/\/$/, '');
      this.fetch = options.fetch || root.fetch.bind(root);
      this.storage = options.storage;
      this.session = options.session;
      this.onState = options.onState;
      this.onStatus = options.onStatus;
      this.onAccount = options.onAccount;
      this.onConflict = options.onConflict;
      this.user = null; this.token = null; this.dirty = false;
      this.busy = false; this.conflict = null; this.expired = false;
      this.epoch = 0; this.generation = 0; this.cached = false;
    }
    async request(path, method = 'GET', body, token = this.token) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 20000);
      try {
        const response = await this.fetch(this.base + path, {
          method, cache: 'no-store', signal: controller.signal,
          headers: {...(token ? {Authorization: 'Bearer ' + token} : {}), ...(body ? {'Content-Type': 'application/json'} : {})},
          ...(body ? {body: JSON.stringify(body)} : {})
        });
        if (!response.ok) {
          const error = new Error(response.status === 401 ? '아이디와 비밀번호 또는 로그인 상태를 확인해주세요.' : response.status === 400 ? '이미 사용 중인 아이디입니다.' : response.status === 422 ? '입력 형식이나 목록 크기를 확인해주세요.' : '서버에 연결하지 못했어요. 잠시 후 다시 시도해주세요.');
          error.status = response.status; throw error;
        }
        return await response.json();
      } finally { clearTimeout(timer); }
    }
    key() { return 'taskflow.cloud.' + this.user.id; }
    backup() {
      try {
        this.storage.setItem(this.key(), JSON.stringify({state: this.state, base: this.baseState, revision: this.revision, dirty: this.dirty}));
        this.cached = true;
        return true;
      } catch { this.cached = false; this.onStatus('기기 백업 실패 · 서버 저장 상태를 확인해주세요'); return false; }
    }
    async authenticate(username, password, signup) {
      if (signup) await this.request('/signup', 'POST', {username, password}, null);
      const result = await this.request('/login', 'POST', {username, password}, null);
      await this.connect(result.access_token);
    }
    async connect(token) {
      const user = await this.request('/users/me', 'GET', undefined, token);
      const workspace = await this.request('/workspaces/current', 'GET', undefined, token);
      if (!root.TaskStore.validate(workspace.state)) throw new Error('서버 목록 형식을 확인할 수 없습니다.');
      let pending;
      try { pending = JSON.parse(this.storage.getItem('taskflow.cloud.' + user.id)); } catch { /* 손상된 캐시는 서버 데이터를 사용한다. */ }
      if (this.user && this.dirty) {
        if (this.user.id === user.id) pending = {state: clone(this.state), base: clone(this.baseState), revision: this.revision, dirty: true};
        else if (!this.cached) throw new Error('현재 변경을 기기에 보관하지 못했어요. 서버에 저장한 후 계정을 바꿔주세요.');
      }
      this.epoch++; clearTimeout(this.timer);
      this.user = user; this.token = token; this.expired = false;
      this.revision = workspace.revision; this.baseState = clone(workspace.state);
      this.state = clone(workspace.state); this.dirty = false; this.conflict = null;
      if (pending?.dirty && Number.isSafeInteger(pending.revision) && pending.revision >= 0 && root.TaskStore.validate(pending.state) && root.TaskStore.validate(pending.base)) {
        this.state = pending.state; this.baseState = pending.base; this.dirty = true;
        this.revision = pending.revision;
        if (pending.revision !== workspace.revision) this.conflict = workspace;
      }
      try { this.session.setItem('taskflow.session', token); } catch { /* 현재 탭에서는 로그인을 유지한다. */ }
      this.generation++;
      this.onAccount(user); this.onState(clone(this.state)); this.backup();
      this.onConflict(this.conflict);
      this.onStatus(this.conflict ? '다른 기기의 변경 확인 필요' : this.dirty ? '저장 대기 중' : '모든 기기에 동기화됨');
      if (this.dirty && !this.conflict) this.schedule();
    }
    async restore() {
      let token;
      try { token = this.session.getItem('taskflow.session'); } catch { return; }
      if (!token) return;
      await this.connect(token);
    }
    change(state) {
      this.state = clone(state); this.generation++; this.dirty = true; this.backup();
      const location = this.cached ? '이 기기에 보관됨' : '탭을 닫지 마세요';
      this.onStatus(this.conflict ? '충돌 확인 필요 · ' + location : this.expired ? '다시 로그인 필요 · ' + location : '저장 중…');
      this.schedule();
    }
    schedule() { clearTimeout(this.timer); this.timer = setTimeout(() => this.flush(), 350); }
    fail(error) {
      if (error.status === 401) { this.expired = true; this.onAccount(this.user); }
      this.onStatus(this.expired ? '로그인 만료 · 다시 로그인해주세요' : this.dirty ? '서버 미저장 · ' + (this.cached ? '이 기기에 보관됨' : '탭을 닫지 마세요') : '연결 끊김 · 다시 동기화해주세요');
    }
    async flush() {
      if (!this.user || !this.dirty || this.busy || this.conflict || this.expired) return;
      this.busy = true;
      const epoch = this.epoch;
      try {
        while (this.dirty && !this.conflict && epoch === this.epoch) {
          const generation = this.generation, snapshot = clone(this.state);
          let saved;
          try { saved = await this.request('/workspaces/current', 'PUT', {revision: this.revision, state: snapshot}); }
          catch (error) {
            if (error.status !== 409) throw error;
            const remote = await this.request('/workspaces/current');
            if (epoch !== this.epoch) return;
            this.conflict = remote; this.onConflict(remote); this.onStatus('다른 기기의 변경 확인 필요'); return;
          }
          if (epoch !== this.epoch) return;
          this.revision = saved.revision; this.baseState = snapshot;
          this.dirty = generation !== this.generation; this.backup();
          this.onStatus(this.dirty ? '저장 중…' : '모든 기기에 동기화됨');
        }
      } catch (error) { if (epoch === this.epoch) this.fail(error); }
      finally { this.busy = false; if (epoch !== this.epoch && this.dirty && !this.conflict && !this.expired) this.schedule(); }
    }
    async refresh() {
      if (!this.user || this.busy || this.conflict || this.expired) return;
      if (this.dirty) { await this.flush(); return; }
      this.busy = true; const epoch = this.epoch, generation = this.generation;
      try {
        const workspace = await this.request('/workspaces/current');
        if (epoch !== this.epoch || generation !== this.generation) return;
        if (!root.TaskStore.validate(workspace.state)) throw new Error('Invalid workspace');
        if (workspace.revision !== this.revision) {
          this.revision = workspace.revision; this.baseState = clone(workspace.state);
          this.state = clone(workspace.state); this.backup(); this.onState(clone(this.state));
        }
        this.onStatus('모든 기기에 동기화됨');
      } catch (error) { if (epoch === this.epoch) this.fail(error); }
      finally { this.busy = false; if (this.dirty && !this.conflict && !this.expired) this.schedule(); }
    }
    resolve(useLocal) {
      if (!this.conflict) return;
      this.state = useLocal ? mergeWorkspace(this.baseState, this.state, this.conflict.state) : clone(this.conflict.state);
      this.revision = this.conflict.revision; this.baseState = clone(this.conflict.state);
      this.dirty = useLocal; this.conflict = null; this.generation++;
      this.backup(); this.onConflict(null); this.onState(clone(this.state));
      this.onStatus(useLocal ? '저장 중…' : '모든 기기에 동기화됨');
      if (useLocal) this.schedule();
    }
    logout() {
      this.epoch++; clearTimeout(this.timer);
      try { this.session.removeItem('taskflow.session'); } catch { /* 현재 탭 로그아웃은 계속한다. */ }
      this.user = null; this.token = null; this.dirty = false; this.conflict = null; this.expired = false;
      this.onAccount(null); this.onConflict(null);
    }
  }
  root.TaskSync = {SyncClient, mergeWorkspace};
})(globalThis);
