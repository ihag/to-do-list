'use strict';
const $ = selector => document.querySelector(selector);
let state, storageReady = true, filter = 'all', query = '', selectedTopic = null, editingTopic = null, selectedEmoji = '📋', toastTimer;
let sync, signupMode = false, selectedWorkspace = 'default', editingWorkspace = null, workspaceEmoji = '📋', selectionAccount = null;
function currentWorkspace() {
  const key = 'taskflow.selection.' + (sync?.user?.id || 'guest');
  if (selectionAccount !== key) {
    selectionAccount = key;
    try { selectedWorkspace = localStorage.getItem(key) || 'default'; } catch { selectedWorkspace = 'default'; }
  }
  const rows = TaskStore.workspaces(state);
  const workspace = rows.find(item => item.id === selectedWorkspace) || rows[0];
  selectedWorkspace = workspace?.id || null;
  try { localStorage.setItem(key, selectedWorkspace || ''); } catch { /* 목록 저장과 선택 메뉴는 계속 사용한다. */ }
  return workspace;
}
function workspaceTopics() { return currentWorkspace()?.topics || []; }
function notify(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 3500);
}
try { state = TaskStore.load(localStorage); }
catch (error) {
  state = { version: 1, topics: [] };
  storageReady = false;
  $('#save-status').textContent = '저장 기능을 확인해주세요';
  notify('저장 데이터를 읽을 수 없습니다. 기존 데이터는 유지되며 변경 사항은 저장되지 않습니다.');
}
function persist() {
  if (sync?.user) { sync.change(state); return; }
  if (!storageReady) { notify('저장할 수 없는 상태입니다. 브라우저 저장 설정을 확인해주세요.'); return; }
  try { TaskStore.save(localStorage, state); $('#save-status').textContent = '이 브라우저에 저장됨'; }
  catch (error) { $('#save-status').textContent = '저장 실패 · 변경 사항 미저장'; notify('저장하지 못했습니다. 브라우저 저장 공간과 설정을 확인해주세요.'); }
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function emojiGraphic(emoji) {
  const glyph = element('span', 'emoji-glyph');
  glyph.setAttribute('aria-hidden', 'true');
  const image = element('img', 'emoji-image');
  const code = Array.from(emoji).filter(character => character.codePointAt(0) !== 0xfe0f).map(character => character.codePointAt(0).toString(16)).join('-');
  image.src = `emojis/${code}.png`;
  image.alt = '';
  image.width = 20;
  image.height = 20;
  image.draggable = false;
  glyph.append(image, element('span', 'emoji-text', emoji));
  return glyph;
}
function openTopicDialog(topic = null) {
  if (!currentWorkspace()) { notify('워크스페이스를 먼저 만들어주세요.'); openWorkspaceDialog(); return; }
  editingTopic = topic;
  $('#dialog-title').textContent = topic ? '주제 이름 수정' : '새로운 주제';
  $('#topic-name').value = topic ? topic.name : '';
  selectedEmoji = topic?.emoji || '📋';
  renderEmojiPicker();
  $('#topic-dialog').showModal();
  $('#topic-name').focus();
}
function renderEmojiPicker() {
  $('#emoji-picker').replaceChildren();
  TaskStore.EMOJIS.forEach(emoji => {
    const button = element('button', 'emoji-choice');
    button.append(emojiGraphic(emoji));
    button.type = 'button';
    button.setAttribute('aria-label', emoji + ' 이모티콘');
    button.setAttribute('aria-pressed', String(emoji === selectedEmoji));
    button.onclick = () => { selectedEmoji = emoji; renderEmojiPicker(); $('#emoji-picker').querySelectorAll('button')[TaskStore.EMOJIS.indexOf(emoji)].focus(); };
    $('#emoji-picker').append(button);
  });
}
function confirmDelete(description, action) {
  const dialog = $('#delete-dialog');
  $('#delete-description').textContent = description;
  dialog.returnValue = '';
  dialog.onclose = () => {
    if (dialog.returnValue !== 'confirm') return;
    try { action(); persist(); render(); notify('삭제했어요.'); }
    catch (error) { notify(error.message); }
  };
  dialog.showModal();
}
function render() {
  renderWorkspaces();
  const todos = workspaceTopics().flatMap(topic => topic.todos);
  const done = todos.filter(todo => todo.done).length;
  const percent = todos.length ? Math.round(done / todos.length * 100) : 0;
  $('#total').replaceChildren(document.createTextNode(todos.length), element('small', '', '개'));
  $('#pending').replaceChildren(document.createTextNode(todos.length - done), element('small', '', '개'));
  $('#completed').replaceChildren(document.createTextNode(done), element('small', '', '개'));
  $('#percent').textContent = percent + '%';
  $('#overall-progress').style.width = percent + '%';
  $('.progress-track').setAttribute('aria-valuenow', String(percent));
  $('#progress-caption').textContent = percent === 100 ? '오늘의 할 일, 모두 해냈어요!' : done ? `${done}개의 작은 완료가 쌓였어요.` : '첫 번째 할 일을 시작해보세요.';
  $('#filter-count').textContent = todos.length;
  $('#topic-nav').replaceChildren();
  workspaceTopics().forEach(topic => {
    const button = element('button', 'topic-nav-item' + (selectedTopic === topic.id ? ' selected' : ''));
    const navEmoji = element('span', 'nav-emoji');
    navEmoji.append(emojiGraphic(topic.emoji || '📋'));
    button.append(navEmoji, element('span', '', topic.name));
    button.setAttribute('aria-pressed', String(selectedTopic === topic.id));
    button.onclick = () => { selectedTopic = selectedTopic === topic.id ? null : topic.id; render(); };
    $('#topic-nav').append(button);
  });
  const container = $('#topics');
  container.replaceChildren();
  workspaceTopics().filter(topic => !selectedTopic || topic.id === selectedTopic).forEach(topic => {
    const visible = TaskStore.visibleTodos(topic, filter, query);
    if ((query || filter !== 'all') && !visible.length) return;
    const details = element('details', 'topic');
    details.open = query || filter !== 'all' ? true : topic.open;
    const summary = element('summary');
    const emojiButton = element('button', 'topic-icon');
    emojiButton.append(emojiGraphic(topic.emoji || '📋'));
    emojiButton.type = 'button';
    emojiButton.setAttribute('aria-label', topic.name + ' 이모티콘 변경');
    emojiButton.onclick = event => { event.preventDefault(); openTopicDialog(topic); $('#emoji-picker').querySelector('[aria-pressed=true]').focus(); };
    summary.append(element('span', 'chevron', '›'), emojiButton, element('span', 'topic-title', topic.name), element('span', 'topic-count', topic.todos.length));
    const actions = element('span', 'topic-actions');
    const edit = element('button', 'edit-topic', '수정');
    edit.type = 'button';
    edit.setAttribute('aria-label', topic.name + ' 주제 이름 수정');
    edit.onclick = event => { event.preventDefault(); openTopicDialog(topic); };
    const deleteTopic = element('button', 'delete-topic delete-action', '삭제');
    deleteTopic.type = 'button';
    deleteTopic.setAttribute('aria-label', topic.name + ' 주제 삭제');
    deleteTopic.onclick = event => {
      event.preventDefault();
      confirmDelete(`“${topic.name}” 주제와 그 안의 할 일 ${topic.todos.length}개를 삭제합니다. 삭제 후 되돌릴 수 없습니다.`, () => {
        TaskStore.deleteTopic(currentWorkspace(), topic.id);
        if (selectedTopic === topic.id) selectedTopic = null;
      });
    };
    actions.append(edit, deleteTopic);
    summary.append(actions);
    const list = element('div', 'todo-list');
    visible.forEach(todo => {
      const row = element('div', 'todo-row' + (todo.done ? ' done' : ''));
      const checkbox = element('input'); checkbox.type = 'checkbox'; checkbox.checked = todo.done; checkbox.id = 'todo-' + todo.id;
      checkbox.onchange = () => { todo.done = checkbox.checked; persist(); render(); };
      const label = element('label', 'todo-label', todo.title); label.htmlFor = checkbox.id;
      row.append(checkbox, label);
      if (todo.due) {
        const today = localDate();
        const badge = element('span', 'due-badge' + (!todo.done && todo.due < today ? ' overdue' : ''), todo.due === today ? '오늘' : todo.due.slice(5).replace('-', '.'));
        badge.title = todo.due; row.append(badge);
      }
      const editTodo = element('button', 'todo-edit', '수정');
      editTodo.setAttribute('aria-label', todo.title + ' 수정');
      editTodo.onclick = () => {
        const input = element('input'); input.type = 'text'; input.value = todo.title; input.maxLength = 200; input.className = 'todo-label'; input.setAttribute('aria-label', '할 일 이름 수정');
        label.replaceWith(input); editTodo.textContent = '저장'; input.focus();
        const finish = () => {
          const title = input.value.trim();
          if (!title) { notify('할 일 이름을 입력해주세요.'); input.focus(); return; }
          todo.title = title; persist(); render();
        };
        editTodo.onclick = finish;
        input.onkeydown = event => { if (event.isComposing) return; if (event.key === 'Enter') finish(); if (event.key === 'Escape') render(); };
      };
      const deleteTodo = element('button', 'delete-todo delete-action', '삭제');
      deleteTodo.setAttribute('aria-label', todo.title + ' 삭제');
      deleteTodo.onclick = () => confirmDelete(`“${todo.title}” 할 일을 삭제합니다. 삭제 후 되돌릴 수 없습니다.`, () => {
        const currentTopic = workspaceTopics().find(item => item.id === topic.id);
        if (!currentTopic) throw new Error('주제를 찾을 수 없습니다.');
        TaskStore.deleteTodo(currentTopic, todo.id);
      });
      row.append(editTodo, deleteTodo); list.append(row);
    });
    if (!visible.length) list.append(element('div', 'topic-empty', '아직 할 일이 없어요. 첫 번째 할 일을 적어보세요.'));
    const form = element('form', 'task-form');
    const input = element('input'); input.type = 'text'; input.placeholder = '새로운 할 일 추가하기'; input.required = true; input.maxLength = 200; input.setAttribute('aria-label', topic.name + '에 할 일 추가');
    const due = element('input'); due.type = 'date'; due.setAttribute('aria-label', '할 일 기한');
    const calendar = element('label', 'calendar-control');
    calendar.title = '기한 선택';
    calendar.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4M16 3v4M4 11h16"/></svg>';
    due.title = '기한 선택'; calendar.append(due);
    due.onchange = () => {
      calendar.classList.toggle('has-date', !!due.value);
      calendar.title = due.value ? '선택한 기한: ' + due.value : '기한 선택';
      due.setAttribute('aria-label', due.value ? '할 일 기한 ' + due.value : '할 일 기한');
    };
    const button = element('button', '', '추가'); button.type = 'submit';
    const addIcon = element('span', 'task-add-icon');
    addIcon.setAttribute('aria-hidden', 'true');
    addIcon.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 4v16M4 12h16"/></svg>';
    form.append(addIcon, input, calendar, button);
    form.onsubmit = event => {
      event.preventDefault();
      try {
        TaskStore.addTodo(topic, input.value, due.value); filter = 'all'; query = ''; $('#search').value = ''; updateFilters(); persist(); render();
        document.getElementById(details.id)?.querySelector('input[type=text]')?.focus();
        notify('할 일을 추가했어요.');
      } catch (error) { notify(error.message); }
    };
    details.id = 'topic-' + topic.id;
    list.append(form); details.append(summary, list); container.append(details);
    details.addEventListener('toggle', () => {
      if (!details.isConnected || query || filter !== 'all' || topic.open === details.open) return;
      topic.open = details.open; persist();
    });
  });
  if (!container.childElementCount) container.append(element('div', 'empty', query || filter !== 'all' ? '조건에 맞는 할 일이 없어요.' : '새로운 주제를 만들고 나의 할 일을 시작해보세요.'));
}
function localDate() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
function updateFilters() {
  document.querySelectorAll('[data-filter]').forEach(button => {
    button.classList.toggle('selected', button.dataset.filter === filter);
    button.setAttribute('aria-pressed', String(button.dataset.filter === filter));
  });
}
function resetWorkspaceView() {
  selectedTopic = null; filter = 'all'; query = ''; $('#search').value = ''; updateFilters();
}
function renderWorkspaces() {
  const current = currentWorkspace(), select = $('#workspace-select');
  select.replaceChildren();
  for (const workspace of TaskStore.workspaces(state)) {
    const option = element('option', '', workspace.name); option.value = workspace.id; select.append(option);
  }
  if (!current) { const option = element('option', '', '워크스페이스를 만들어주세요'); option.value = ''; select.append(option); }
  select.value = current?.id || ''; select.disabled = !current;
  $('#workspace-edit').disabled = !current;
  $('#workspace-emoji').replaceChildren();
  if (current) $('#workspace-emoji').append(emojiGraphic(current.emoji));
}
function renderWorkspaceEmojis() {
  const picker = $('#workspace-emoji-picker'); picker.replaceChildren();
  for (const emoji of TaskStore.EMOJIS) {
    const button = element('button', 'emoji-choice'); button.type = 'button'; button.append(emojiGraphic(emoji));
    button.setAttribute('aria-label', emoji + ' 워크스페이스 이모티콘');
    button.setAttribute('aria-pressed', String(emoji === workspaceEmoji));
    button.onclick = () => { workspaceEmoji = emoji; renderWorkspaceEmojis(); picker.querySelector('[aria-pressed=true]').focus(); };
    picker.append(button);
  }
}
function openWorkspaceDialog(workspace = null) {
  editingWorkspace = workspace?.id || null; workspaceEmoji = workspace?.emoji || '📋';
  $('#workspace-dialog-title').textContent = workspace ? '워크스페이스 수정' : '새 워크스페이스';
  $('#workspace-name').value = workspace?.name || ''; $('#workspace-delete').hidden = !workspace;
  renderWorkspaceEmojis(); $('#workspace-dialog').showModal(); $('#workspace-name').focus();
}
$('#workspace-add').onclick = () => openWorkspaceDialog();
$('#workspace-edit').onclick = () => openWorkspaceDialog(currentWorkspace());
$('#workspace-select').onchange = event => { selectedWorkspace = event.target.value; resetWorkspaceView(); render(); };
['#workspace-close', '#workspace-cancel'].forEach(selector => { $(selector).onclick = () => $('#workspace-dialog').close(); });
$('#workspace-form').onsubmit = event => {
  event.preventDefault();
  try {
    const workspace = editingWorkspace ? TaskStore.editWorkspace(state, editingWorkspace, $('#workspace-name').value, workspaceEmoji) : TaskStore.addWorkspace(state, $('#workspace-name').value, workspaceEmoji);
    selectedWorkspace = workspace.id; resetWorkspaceView(); persist(); render(); $('#workspace-dialog').close(); notify('워크스페이스를 저장했어요.');
  } catch (error) { notify(error.message); }
};
$('#workspace-delete').onclick = () => {
  const workspace = TaskStore.workspaces(state).find(item => item.id === editingWorkspace);
  if (!workspace) { notify('워크스페이스를 찾을 수 없습니다.'); return; }
  const id = workspace.id, count = workspace.topics.flatMap(topic => topic.todos).length;
  $('#workspace-dialog').close();
  confirmDelete(`“${workspace.name}” 워크스페이스와 주제 ${workspace.topics.length}개, 할 일 ${count}개를 삭제합니다. 삭제 후 되돌릴 수 없습니다.`, () => {
    TaskStore.deleteWorkspace(state, id); resetWorkspaceView();
  });
};
$('#today').textContent = new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }).format(new Date());
['#sidebar-add', '#bottom-add'].forEach(selector => { $(selector).onclick = () => openTopicDialog(); });
['#close-dialog', '#cancel-dialog'].forEach(selector => { $(selector).onclick = () => $('#topic-dialog').close(); });
$('#topic-form').onsubmit = event => {
  event.preventDefault();
  const name = $('#topic-name').value.trim();
  try {
    if (!name || name.length > 60) throw new Error('주제 이름을 입력해주세요.');
    if (editingTopic) {
      const topic = workspaceTopics().find(item => item.id === editingTopic.id);
      if (!topic) throw new Error('주제를 찾을 수 없습니다.');
      topic.name = name; topic.emoji = selectedEmoji;
    }
    else { const topic = TaskStore.addTopic(currentWorkspace(), name, selectedEmoji); selectedTopic = null; topic.open = true; }
    query = ''; filter = 'all'; $('#search').value = ''; updateFilters(); persist(); render(); $('#topic-dialog').close(); notify('주제를 저장했어요.');
  } catch (error) { notify(error.message); }
};
document.querySelectorAll('[data-filter]').forEach(button => { button.onclick = () => { filter = button.dataset.filter; updateFilters(); render(); }; });
$('#search').oninput = event => { query = event.target.value; render(); };
document.addEventListener('keydown', event => {
  if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName) && !document.querySelector('dialog[open]')) { event.preventDefault(); $('#search').focus(); }
});
window.addEventListener('storage', event => {
  if (sync?.user) return;
  if (event.key !== TaskStore.KEY) return;
  try { state = TaskStore.load(localStorage); selectedTopic = null; render(); notify('다른 탭의 변경 사항을 반영했어요.'); }
  catch (error) { storageReady = false; $('#save-status').textContent = '저장 데이터를 확인해주세요'; notify('다른 탭의 저장 데이터를 읽을 수 없습니다.'); }
});
render();
if (storageReady) persist();

function applyCloudState(next) {
  state = next; selectedTopic = null;
  // 열린 편집창의 입력은 유지하고 현재 목록만 갱신한다.
  render();
}
function updateAccount(user) {
  $('#account-button').textContent = user ? (sync.expired ? '다시 로그인' : '나의 계정') : '로그인';
  $('#sync-now').hidden = !user;
  $('#profile-name').textContent = user ? user.username : '나의 워크스페이스';
  $('#profile-detail').textContent = user ? '개인 공간 · 기기 간 동기화' : '개인 공간 · 브라우저 저장';
}
sync = new TaskSync.SyncClient({
  base: TaskFlowConfig.apiBase,
  storage: localStorage, session: sessionStorage,
  onState: applyCloudState,
  onStatus: message => { $('#save-status').textContent = message; },
  onAccount: updateAccount,
  onConflict: conflict => { $('#sync-conflict').hidden = !conflict; }
});
function openAuth() {
  signupMode = false; updateAuthMode(); $('#auth-dialog').showModal(); $('#auth-username').focus();
}
function updateAuthMode() {
  $('#auth-title').textContent = signupMode ? '회원가입' : '로그인';
  $('#auth-submit').textContent = signupMode ? '가입하고 시작하기' : '로그인';
  $('#auth-switch').textContent = signupMode ? '로그인으로 돌아가기' : '회원가입';
  $('#auth-password').autocomplete = signupMode ? 'new-password' : 'current-password';
  $('#auth-error').hidden = true;
}
$('#account-button').onclick = () => {
  if (!sync.user || sync.expired) { openAuth(); return; }
  $('#account-name').textContent = sync.user.username + '님으로 로그인됨';
  $('#account-dialog').showModal();
};
$('#close-auth').onclick = () => $('#auth-dialog').close();
$('#auth-switch').onclick = () => { signupMode = !signupMode; updateAuthMode(); };
$('#auth-form').onsubmit = async event => {
  event.preventDefault();
  $('#auth-error').hidden = true;
  const buttons = $('#auth-form').querySelectorAll('button'); buttons.forEach(button => { button.disabled = true; });
  const fields = $('#auth-form').querySelectorAll('input'); fields.forEach(input => { input.readOnly = true; });
  try {
    await sync.authenticate($('#auth-username').value.trim().toLowerCase(), $('#auth-password').value, signupMode);
    $('#auth-password').value = ''; $('#auth-dialog').close(); notify('로그인했어요. 같은 계정으로 다른 기기에서도 이어서 사용하세요.');
  } catch (error) { $('#auth-error').textContent = error.message || '연결을 확인하고 다시 시도해주세요.'; $('#auth-error').hidden = false; }
  finally { buttons.forEach(button => { button.disabled = false; }); fields.forEach(input => { input.readOnly = false; }); }
};
['#close-account', '#account-done'].forEach(selector => { $(selector).onclick = () => $('#account-dialog').close(); });
$('#logout-button').onclick = async () => {
  if (sync.dirty) await sync.flush();
  if (sync.dirty && !sync.cached) { notify('변경을 기기에 보관하지 못했어요. 서버에 저장한 후 로그아웃해주세요.'); return; }
  if (sync.dirty && !window.confirm('아직 서버에 저장되지 않은 변경이 있어요. 이 기기에 보관하고 로그아웃할까요? 같은 계정으로 다시 로그인하면 복구할 수 있습니다.')) return;
  sync.logout(); $('#account-dialog').close();
  try { state = TaskStore.load(localStorage); storageReady = true; }
  catch { state = {version: 1, topics: []}; storageReady = false; }
  selectedTopic = null; render(); $('#save-status').textContent = storageReady ? '이 브라우저에 저장됨' : '브라우저 저장 확인 필요';
  notify('로그아웃했어요. 브라우저 목록으로 돌아왔습니다.');
};
$('#import-local').onclick = () => {
  let local;
  try { local = TaskStore.load(localStorage); }
  catch { notify('기존 브라우저 목록을 읽을 수 없습니다.'); return; }
  const importedTopics = TaskStore.workspaces(local).flatMap(workspace => workspace.topics);
  if (!currentWorkspace()) { notify('가져올 워크스페이스를 먼저 만들어주세요.'); return; }
  if (!importedTopics.length) { notify('가져올 주제가 없습니다.'); return; }
  if (!window.confirm(`이 브라우저의 주제 ${importedTopics.length}개를 계정 목록에 추가할까요? 기존 목록은 유지되며, 다시 가져오면 중복으로 추가됩니다.`)) return;
  for (const topic of importedTopics) {
    workspaceTopics().push({...topic, id: crypto.randomUUID(), todos: topic.todos.map(todo => ({...todo, id: crypto.randomUUID()}))});
  }
  persist(); selectedTopic = null; render(); $('#account-dialog').close(); notify('목록을 추가했어요. 저장 상태를 확인해주세요.');
};
$('#sync-now').onclick = async () => {
  if (document.querySelector('.todo-row input[type=text]')) { notify('편집 중인 할 일을 먼저 저장해주세요.'); return; }
  $('#sync-now').disabled = true; await sync.refresh(); $('#sync-now').disabled = false;
};
$('#merge-changes').onclick = () => sync.resolve(true);
$('#use-remote').onclick = () => {
  if (window.confirm('이 기기의 저장 대기 중 변경을 취소하고 다른 기기 목록을 사용할까요?')) sync.resolve(false);
};
const canRefresh = () => !document.hidden && !document.querySelector('dialog[open], .todo-row input[type=text]');
setInterval(() => { if (canRefresh()) sync.refresh(); }, 30000);
window.addEventListener('focus', () => { if (canRefresh()) sync.refresh(); });
window.addEventListener('online', () => { if (sync.dirty) sync.flush(); else if (canRefresh()) sync.refresh(); });
document.addEventListener('visibilitychange', () => { if (canRefresh()) sync.refresh(); });
window.addEventListener('beforeunload', event => { if (sync.dirty) { event.preventDefault(); event.returnValue = ''; } });
// 복원 중에는 브라우저 목록을 편집해 계정 목록과 섞이지 않도록 한다.
let savedSession;
try { savedSession = sessionStorage.getItem('taskflow.session'); } catch { /* 로그인 없이 계속 사용한다. */ }
if (savedSession) {
  $('.content').inert = true; $('.sidebar').inert = true; $('#account-button').disabled = true;
  $('#save-status').textContent = '로그인 복원 중…';
  sync.restore().catch(() => { $('#save-status').textContent = '로그인 복원 실패 · 다시 로그인해주세요'; notify('서버 목록을 불러오지 못했어요. 현재는 브라우저 목록입니다. 다시 로그인해주세요.'); })
    .finally(() => { $('.content').inert = false; $('.sidebar').inert = false; $('#account-button').disabled = false; });
}
