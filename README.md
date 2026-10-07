# TaskFlow · 주제별 투두리스트

흰색 바탕과 하늘색·파란색 포인트의 반응형 개인 할 일 웹 앱입니다.

- 주제 만들기·이름 수정·이모티콘 선택·접기 및 펼치기
- 주제 아래 할 일 추가·이름 수정·기한 지정
- 주제·할 일 삭제 확인 및 취소 (주제 삭제 시 내부 할 일도 함께 삭제)
- 2열 주제 카드와 한 줄로 배치한 현황 카드 4개, 모바일에서는 주제 1열
- 완료 체크 시 회색 글자와 취소선, 진행률 자동 계산
- 큰 날짜 제목, 달성률 진행 막대, 검색, 전체·진행 중·완료 필터, `/` 검색 단축키
- 새로고침 후 데이터와 접힘 상태 유지, 다른 탭의 변경 반영
- 회원가입·로그인, 같은 계정의 PC·휴대폰 목록 자동 동기화
- 기존 브라우저 목록 가져오기, 오프라인 변경 보관·재전송, 동시 수정 충돌 확인·병합

웹 화면은 `web/`에 있으며 다음 명령으로 바로 실행할 수 있습니다.

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory web
```

주소: http://127.0.0.1:8080

로그인 전에는 현재 브라우저의 localStorage에 저장하며 첫 방문에 예시 목록을 제공합니다.
로그인 후에는 개인 계정의 목록을 Vercel API와 Neon PostgreSQL에 저장합니다.
PC와 휴대폰에서 같은 계정으로 로그인하면 목록이 동기화됩니다. 화면을 다시 열 때와
활성 화면에서 30초마다 다른 기기의 변경을 확인하며, 동기화 버튼으로 바로 확인할 수 있습니다.
기존 브라우저 목록은 유지됩니다. **나의 계정 → 이 브라우저 목록 가져오기**를 선택하면
계정 목록에 복사해서 추가합니다. 반복하면 중복으로 추가되므로 확인 창을 표시합니다.

로그인은 탭의 sessionStorage에 저장하며 운영 토큰은 7일 후 만료됩니다. 만료 시 다시
로그인해야 합니다. 로그인되지 않은 다른 사람은 계정 목록을 볼 수 없습니다.
서버 저장에 실패한 변경은 사용자 ID별 로컬 캐시에 보관하고 재연결 시 재전송합니다.
동시에 변경한 기기에는 충돌 안내를 표시합니다. **내 변경 합쳐 저장**은 서로 다른 항목의
변경을 합치며 같은 항목은 이 기기의 변경을 우선합니다. **다른 기기 목록 사용**은 확인 후
이 기기의 저장 대기 중 변경을 취소합니다. 서버 저장 완료 표시를 확인하세요.
브라우저 데이터 삭제 시 게스트 목록과 아직 서버에 저장되지 않은 변경은 사라집니다.

정적 파일만 실행하면 게스트 기능을 사용합니다. 로컬에서 로그인·동기화를 테스트하려면
아래 FastAPI 서버를 실행하세요. `web/config.js`는 GitHub Pages에서 운영 API를,
그 외에는 현재 사이트의 API를 사용합니다.

## 무료 동기화 서버

운영 서버: https://taskflow-sync-rla2fma-2683.vercel.app/

- Vercel 프로젝트: `taskflow-sync` (Hobby)
- 저장소: 연결된 Neon Free PostgreSQL
- 필수 환경 변수: `DATABASE_URL`, `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- DB 연결 문자열·JWT 비밀키는 Vercel 비밀 환경 변수에만 저장합니다.
- 인증은 기존 Argon2 비밀번호 해시와 JWT를 사용합니다. 워크스페이스 접근은 토큰의 사용자 ID로 제한합니다.
- `DATABASE_URL`이 없으면 개발 SQLite를 사용합니다. Vercel 운영에서는 없는 경우 시작을 거부합니다.
- 승인한 새 DB에 `users`, `todos`, `workspaces` 테이블을 생성하며 기존 SQLite·브라우저 데이터를 자동으로 옮기지 않습니다.

`vercel.json`의 FastAPI 설정과 `requirements.txt`를 사용해 백엔드를 별도로 배포합니다.
소스 파일 배포에는 `app/`, `web/`, `requirements.txt`, `vercel.json`만 포함하고 `.env`, DB,
테스트 브라우저 프로필, 인증 정보는 포함하지 않습니다. GitHub Pages와 서버는 별도 배포이므로
API가 바뀌면 서버 배포도 갱신해야 합니다. Vercel Git 연결은 별도로 구성할 수 있습니다.

현재 무료 플랜으로 운영합니다. 사용량·무료 한도·비상업적 이용 조건은
[Vercel Hobby](https://vercel.com/docs/plans/hobby)와 [Neon 요금](https://neon.com/pricing)을 확인하세요.
무료 한도를 넘으면 서비스 제한이 발생할 수 있으며 유료 플랜으로 자동 전환하지 않습니다.

## GitHub Pages 배포

배포 주소: https://ihag.github.io/to-do-list/

소스는 `feat/taskflow-pages`, 웹 배포 파일은 `gh-pages` 브랜치에 있습니다.
전체 pytest와 실제 Chrome 검증을 통과한 `web/` 파일만 배포했습니다.
`.env`, SQLite DB, 백엔드 소스는 웹 배포 파일에 포함되지 않습니다.

저장소 Settings → Pages에서 **Deploy from a branch**, `gh-pages`, `/ (root)`를
사용합니다. 현재 Git 인증에 workflow 권한이 없어 브랜치 배포 방식을 사용합니다.
main에는 직접 커밋하지 않았습니다.

후속 수정은 기능 브랜치에서 진행하고 전체 pytest를 실행한 후, 변경된 `web/`
파일을 `gh-pages` 루트에 반영합니다. gh-pages에 push하면 GitHub Pages가 다시 배포합니다.

`deployment/github-pages.yml`은 테스트 후 자동 배포를 위한 선택적 워크플로 템플릿입니다.
workflow 권한이 있는 인증을 사용하게 되면 이를 `.github/workflows/pages.yml`에 복사하고,
트리거의 기능 브랜치 이름을 조정한 뒤 Pages Source를 GitHub Actions로 변경할 수 있습니다.

프런트엔드 테스트도 `pytest`에 포함되어 있어 Node.js 22 이상이 필요합니다.
`node tests/web_store_test.cjs`로 저장·완료·검색·검증 실패 케이스를 따로 실행할 수 있습니다.
`node tests/web_sync_test.cjs`는 동시 수정, 저장 도중 추가 편집, 충돌 상태의 새로고침,
오프라인 복구, 로그인 만료, 게스트 목록 보존을 검사하며 pytest에도 포함됩니다.
`tests/browser_sync_qa.cjs`는 Chrome의 서로 격리된 두 브라우저 컨텍스트로 PC·휴대폰
로그인과 실제 API 저장, 병합, 오프라인 재전송, 새로고침, 가져오기·로그아웃을 검사합니다.
실제 운영 테스트는 별도 테스트 계정을 생성하며 실제 사용자 목록은 변경하지 않습니다.
`tests/browser_qa.cjs`는 별도로 실행 중인 로컬 Chrome(디버깅 포트 9227)과
웹 서버(8080)를 사용하여 실제 화면 동작 및 모바일 레이아웃을 검사합니다.

이모티콘은 기기의 글꼴에 영향을 받지 않는 자체 호스팅 256px 투명 PNG로 표시합니다.
Twemoji v17.0.3 그래픽(CC BY 4.0)의 SVG viewBox를 그림 영역 기준으로 조정하고,
기기별 SVG 렌더링 차이도 없도록 대칭 여백을 적용한 PNG를 생성했습니다.
출처·변경 내역과 라이선스는 `web/emojis/NOTICE.txt` 및 `LICENSE-GRAPHICS.txt`에 있습니다.

`node tests/mobile_emoji_qa.cjs`는 11가지 화면 크기에서 16개 이모티콘의 실제
그림 픽셀 중심과 버튼 중심의 차이가 0.6px 이하인지 검증합니다.
macOS의 `swift tests/webkit_emoji_qa.swift`는 시스템 WebKit에서도 같은 검사를 수행합니다.
테스트는 실물 휴대폰 검증을 대신하지 않습니다.

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
| `GET /users/me` | 로그인한 사용자 확인 | 200, User |
| `GET /workspaces/current` | 자신의 주제·할일·이모티콘·접힘 상태 | 200, Workspace |
| `PUT /workspaces/current` | `revision`, `state`로 전체 목록 저장 | 200, Workspace |

Workspace 형식은 `{"revision":0,"state":{"version":1,"topics":[]}}`입니다.
저장은 원자적으로 revision을 비교·증가시킵니다. 다른 기기에서 먼저 저장한 버전은
409로 거부합니다. 요청에 사용자 ID를 지정할 수 없습니다. 주제는 100개, 주제당 할 일은
1,000개, 목록은 1MB까지 저장할 수 있습니다. UI의 주제 목록과 기존 `/todos`는 별도 저장소입니다.

Todo 형식: `{"id":1,"title":"장보기","done":false,"due":null}`.
`due`는 `YYYY-MM-DD` 날짜 또는 null입니다. 제목 누락·빈 제목은 400입니다.
토큰 누락·유효하지 않음·만료는 401, 없는 할일 또는 다른 사용자의 할일은 404입니다.
클라이언트가 할일 소유자를 지정할 수 없습니다.

## 구조와 검증

`app/routers/`는 HTTP 처리, `app/models/`는 요청·응답 모델,
`app/services/`는 인증·할일·워크스페이스 처리, `app/db.py`는 SQLite/PostgreSQL 연결과 스키마를 담당합니다.
개발 DB 파일은 프로젝트 루트에 저장되며 운영 데이터는 Neon에 저장됩니다.
`repository.py`의 메모리 저장소는 현재 API에서 사용하지 않습니다.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m black --check app main.py todo_api.py conftest.py test_todo_api.py tests
```

테스트는 임시 DB를 사용하며 실제 `todos.sqlite3`를 변경하지 않습니다.
회원가입·로그인, JWT 검증, 사용자별 권한, 할일 CRUD, 재시작 영속성,
기존 데이터 보존 마이그레이션을 검증합니다.

별도 Codex 함수 요약 도구는 [function_summary/README.md](function_summary/README.md)를 참고하세요.
