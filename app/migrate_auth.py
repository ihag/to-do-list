import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from app.db import DB_PATH, migrate_auth


def main() -> None:
    parser = argparse.ArgumentParser(description="승인된 인증 DB 마이그레이션 실행")
    parser.add_argument("--database", type=Path, default=DB_PATH)
    parser.add_argument("--confirm", action="store_true", help="사람의 실행 승인을 확인")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("마이그레이션은 사람 확인 후 --confirm 옵션으로 실행하세요.")
    if args.database.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = args.database.with_name(args.database.name + ".backup-" + timestamp)
        with closing(sqlite3.connect(args.database)) as source:
            with closing(sqlite3.connect(backup_path)) as backup:
                source.backup(backup)
        print(f"Database backup: {backup_path}")
    migrate_auth(args.database)
    print("Auth migration complete; existing todos preserved.")


if __name__ == "__main__":
    main()
