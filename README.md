# TaskFlow · 주제별 투두리스트

흰색 바탕과 하늘색·파란색 포인트의 반응형 개인 할 일 웹 앱입니다.

- 주제 만들기·이름 수정·접기 및 펼치기
- 주제 아래 할 일 추가·이름 수정·기한 지정
- 완료 체크 시 회색 글자와 취소선, 진행률 자동 계산
- 검색, 전체·진행 중·완료 필터, `/` 검색 단축키
- 새로고침 후 데이터와 접힘 상태 유지, 다른 탭의 변경 반영

웹 화면은 `web/`에 있으며 다음 명령으로 바로 실행할 수 있습니다.

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory web
```

주소: http://127.0.0.1:8080

이 버전의 웹 화면은 현재 브라우저의 localStorage에 저장합니다. 기존 인증 API와는
별도로 동작하며 기기 간 동기화와 서버 계정 저장은 제공하지 않습니다. 첫 방문에
수정 가능한 예시 주제와 할 일을 제공합니다. 브라우저 데이터를 지우면 저장 내용도
사라집니다. 기존 SQLite 데이터는 변경하거나 마이그레이션하지 않습니다.

## GitHub Pages 배포

`.github/workflows/pages.yml`은 전체 pytest가 성공한 뒤 `web/`만 배포합니다.
`.env`, SQLite DB, 백엔드 소스는 웹 배포 파일에 포함되지 않습니다.

1. GitHub 저장소에 `feat/taskflow-web` 브랜치를 push합니다.
2. 저장소 Settings → Pages → Source를 **GitHub Actions**로 설정합니다.
3. 배포 환경의 허용 브랜치에 `feat/taskflow-web`을 포함합니다.
4. Actions에서 **Test and deploy TaskFlow**를 실행합니다.

main에는 직접 커밋하지 않습니다. 리뷰 후 병합하면 main에서도 테스트 및 배포가 실행됩니다.

프런트엔드 테스트도 `pytest`에 포함되어 있어 Node.js 22 이상이 필요합니다.
`node tests/web_store_test.cjs`로 저장·완료·검색·검증 실패 케이스를 따로 실행할 수 있습니다.
`tests/browser_qa.cjs`는 별도로 실행 중인 로컬 Chrome(디버깅 포트 9227)과
웹 서버(8080)를 사용하여 실제 화면 동작 및 모바일 레이아웃을 검사합니다.

## 기존 FastAPI 백엔드

사용자 인증과 SQLite 저장을 제공하는 FastAPI 할일 API입니다. Python 3.9 이상을 사용합니다.

## 설치와 설정

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

`.env`에 `JWT_SECRET`을 설정하세요. 다음 명령으로 생성한 값을 넣습니다.

```sh
.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'
```

`ACCESS_TOKEN_EXPIRE_MINUTES`의 기본값은 30입니다. `.env`는 버전 관리에서 제외하며,
설정이 없거나 비밀키가 32바이트보다 짧으면 서버 시작을 거부합니다.
환경 변수로 설정한 값이 `.env`보다 우선합니다. 서버 재시작 시 같은 비밀키를 유지하면
만료되지 않은 토큰도 계속 사용할 수 있습니다.

## 기존 DB 마이그레이션

인증 이전의 `todos.sqlite3`에는 사용자 구분 컬럼이 없습니다.
사람의 실행 승인을 받은 후, 서버를 종료하고 아래 명령을 실행합니다.

```sh
.venv/bin/python -m app.migrate_auth --confirm
```

명령은 기존 DB를 `todos.sqlite3.backup-*`로 백업하고, `users` 테이블과
`todos.user_id`, 사용자별 인덱스를 추가합니다. 기존 데이터는 삭제하지 않습니다.
기존 소유자 없는 할일은 어떤 사용자에게도 노출하지 않으며 임의로 소유자를 배정하지 않습니다.
기존 스키마를 서버 시작 중 자동으로 마이그레이션하지 않습니다.
새 DB라면 최초 실행 시 최신 테이블을 생성합니다.

## 실행

```sh
.venv/bin/python -m uvicorn app.main:app --reload --workers 1
```

기존 실행 경로인 `todo_api:app`, `main:app`도 같은 인증 앱을 사용합니다.
문서와 테스트: http://127.0.0.1:8000/docs

## 인증과 API

회원가입과 로그인은 JSON을 받습니다.

```json
{"username": "alice", "password": "your-password"}
```

- `POST /signup`: 201, 사용자 `id`와 `username` 반환. 비밀번호는 최소 8자이며 Argon2로 해시 저장합니다. 중복 사용자명은 400입니다.
- `POST /login`: 200, `{"access_token":"...", "token_type":"bearer"}` 반환. 잘못된 사용자명·비밀번호는 401입니다.

사용자명은 앞뒤 공백 제거 후 소문자로 저장합니다. 3~64자의 영문 소문자, 숫자, `_`, `.`, `-`를 사용합니다.
비밀번호는 최대 128자이며 공백을 임의로 제거하지 않습니다. 잘못된 요청 형식은 422입니다.

`/docs`에서 로그인 후 **Authorize**에 JWT를 입력하세요. 모든 할일 요청에
`Authorization: Bearer <access_token>` 헤더가 필요합니다.

| 요청 | 동작 | 성공 응답 |
| --- | --- | --- |
| `POST /todos` | `title`, 선택적인 `due`로 추가 | 201, Todo |
| `GET /todos` | 로그인한 사용자의 할일 목록 | 200, 배열 |
| `PATCH /todos/{id}/toggle` | 자신의 할일 완료 상태 토글 | 200, Todo |
| `DELETE /todos/{id}` | 자신의 할일 삭제 | 204, 본문 없음 |

Todo 형식: `{"id":1,"title":"장보기","done":false,"due":null}`.
`due`는 `YYYY-MM-DD` 날짜 또는 null입니다. 제목 누락·빈 제목은 400입니다.
토큰 누락·유효하지 않음·만료는 401, 없는 할일 또는 다른 사용자의 할일은 404입니다.
클라이언트가 할일 소유자를 지정할 수 없습니다.

## 구조와 검증

`app/routers/`는 HTTP 처리, `app/models/`는 요청·응답 모델,
`app/services/`는 인증·할일 처리, `app/db.py`는 SQLite 연결과 스키마를 담당합니다.
DB 파일은 프로젝트 루트에 저장되며 재시작해도 유지됩니다.
`repository.py`의 메모리 저장소는 현재 API에서 사용하지 않습니다.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m black --check app main.py todo_api.py conftest.py test_todo_api.py tests
```

테스트는 임시 DB를 사용하며 실제 `todos.sqlite3`를 변경하지 않습니다.
회원가입·로그인, JWT 검증, 사용자별 권한, 할일 CRUD, 재시작 영속성,
기존 데이터 보존 마이그레이션을 검증합니다.

별도 Codex 함수 요약 도구는 [function_summary/README.md](function_summary/README.md)를 참고하세요.
