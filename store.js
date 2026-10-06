(function (root) {
  'use strict';
  const KEY = 'taskflow.workspace.v1';
  const EMOJIS = ['📋', '💼', '🌿', '🏠', '🎯', '📚', '💡', '💻', '🎨', '💪', '✈️', '🛒', '🎵', '❤️', '⭐', '☕'];
  const uid = () => root.crypto.randomUUID();
  function initialState() {
    return { version: 1, topics: [
      { id: uid(), name: '이번 주 업무', open: true, todos: [
        { id: uid(), title: '이번 주 우선순위 정리하기', done: false, due: '' },
        { id: uid(), title: '프로젝트 아이디어 메모하기', done: false, due: '' },
        { id: uid(), title: '메일함 가볍게 정리하기', done: true, due: '' }
      ] },
      { id: uid(), name: '나를 위한 시간', open: true, todos: [
        { id: uid(), title: '좋아하는 책 10페이지 읽기', done: false, due: '' },
        { id: uid(), title: '산책하며 잠깐 쉬어가기', done: false, due: '' }
      ] },
      { id: uid(), name: '일상의 작은 일들', open: false, todos: [] }
    ] };
  }
  function validate(state) {
    const ids = new Set();
    const unique = id => typeof id === 'string' && id.length > 0 && !ids.has(id) && !!ids.add(id);
    return state && state.version === 1 && Array.isArray(state.topics) && state.topics.every(topic =>
      unique(topic.id) && typeof topic.name === 'string' && topic.name.trim().length > 0 && topic.name.length <= 60 &&
      (topic.emoji === undefined || EMOJIS.includes(topic.emoji)) &&
      typeof topic.open === 'boolean' && Array.isArray(topic.todos) && topic.todos.every(todo =>
        unique(todo.id) && typeof todo.title === 'string' && todo.title.trim().length > 0 && todo.title.length <= 200 &&
        typeof todo.done === 'boolean' && typeof todo.due === 'string' && (!todo.due || /^\d{4}-\d{2}-\d{2}$/.test(todo.due))));
  }
  function load(storage) {
    const value = storage.getItem(KEY);
    if (value === null) return initialState();
    const state = JSON.parse(value);
    if (!validate(state)) throw new Error('저장된 데이터 형식을 확인할 수 없습니다.');
    return state;
  }
  function save(storage, state) {
    if (!validate(state)) throw new Error('저장할 데이터가 올바르지 않습니다.');
    storage.setItem(KEY, JSON.stringify(state));
  }
  function addTopic(state, name, emoji = '📋') {
    const trimmed = name.trim();
    if (!trimmed || trimmed.length > 60) throw new Error('주제 이름은 1–60자로 입력해주세요.');
    if (!EMOJIS.includes(emoji)) throw new Error('이모티콘을 선택해주세요.');
    const topic = { id: uid(), name: trimmed, emoji, open: true, todos: [] };
    state.topics.push(topic);
    return topic;
  }
  function addTodo(topic, title, due = '') {
    const trimmed = title.trim();
    if (!trimmed || trimmed.length > 200) throw new Error('할 일은 1–200자로 입력해주세요.');
    if (due && !/^\d{4}-\d{2}-\d{2}$/.test(due)) throw new Error('기한을 확인해주세요.');
    topic.todos.push({ id: uid(), title: trimmed, done: false, due });
    topic.open = true;
  }
  function visibleTodos(topic, filter, query) {
    const search = query.trim().toLocaleLowerCase();
    return topic.todos.filter(todo => (filter === 'all' || (filter === 'done' ? todo.done : !todo.done)) &&
      (!search || todo.title.toLocaleLowerCase().includes(search) || topic.name.toLocaleLowerCase().includes(search)));
  }
  function deleteTopic(state, topicId) {
    const index = state.topics.findIndex(topic => topic.id === topicId);
    if (index === -1) throw new Error('주제를 찾을 수 없습니다.');
    state.topics.splice(index, 1);
  }
  function deleteTodo(topic, todoId) {
    const index = topic.todos.findIndex(todo => todo.id === todoId);
    if (index === -1) throw new Error('할 일을 찾을 수 없습니다.');
    topic.todos.splice(index, 1);
  }
  root.TaskStore = { KEY, EMOJIS, initialState, validate, load, save, addTopic, addTodo, visibleTodos, deleteTopic, deleteTodo };
})(globalThis);
