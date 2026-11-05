"""전체 자료 백업 · 복구 — 모든 화면의 자료(app\\_data · 의견 보내기 voc\\)를 한 폴더로 떠 두고 되돌린다.

hotfix132 — 서버가 하루 한 번 떠 두는 것은 app.db 뿐이다 (db.backup_daily).  올린 도면 · LOGIC ·
판넬 · DCS · 도서검토 설정 같은 나머지 자료를 함께 지키는 도구.  표준 라이브러리만 쓴다.

    python spike\\backup_data.py                       백업 (목적지: PID_BACKUP_DIR, 없으면 app\\_data\\backups)
    python spike\\backup_data.py D:\\pid_backup          백업 (목적지 지정 — 다른 드라이브를 권합니다)
    python spike\\backup_data.py D:\\pid_backup --keep 14
    python spike\\backup_data.py --list [목적지]          있는 백업 목록
    python spike\\backup_data.py --restore D:\\pid_backup\\pid_backup_20261105_0930
    python spike\\backup_data.py --restore <폴더> --dry-run   (무엇이 바뀌는지만)

백업 한 판 = `<목적지>/pid_backup_<YYYYMMDD_HHMM>/`
  * SQLite 파일(app.db 등)은 sqlite backup API 로 뜬다 — 서버가 쓰는 중에도 일관된 판.  -wal/-shm 은 담지 않는다.
  * 빼는 것 (다시 만들어지거나 백업 자체): page_cache/ · outputs/ · work/ · logs/ · backups/ · 모든 pages/ 폴더.
  * 도서검토의 API 키는 담지 않는다: books/secret.json 은 빼고, books/config.json 의 apiKey 는 지운 사본을 담는다.
  * 끝에 manifest.json — 파일 수 · 바이트 · 뺀 목록 · app.db 의 integrity_check 결과("ok" 면 정상 백업).
  * --keep N (기본 7) 보다 오래된 pid_backup_* 판은 지운다.

복구:
  * 서버(포트 8000, --port 로 바꿈)가 대답하면 거부한다 — 서버를 먼저 끈다 (stop_pid_server.bat).
  * 지금 자료는 지우지 않고 `<자료 폴더>_before_restore_<시각>` 으로 옮겨 둔다 (backups/ 는 제자리).
  * 옛 app.db-wal/-shm 이 새 DB 위에 재생되지 않게 지운다.
  * 지금 쓰는 도서검토 API 키(secret.json · config.json 의 apiKey)는 복구한 자료로 옮겨 준다.
"""
from __future__ import annotations

import fnmatch
import json
import os
import shutil
import socket
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PREFIX = "pid_backup_"
KEEP = 7
PORT = 8000
SKIP_TOP = ("page_cache", "outputs", "work", "logs", "backups")    # 자료 폴더 바로 아래에서 뺄 폴더
SKIP_DIR_ANY = ("pages",)                                          # 어느 깊이든 뺄 폴더 (LOGIC 장 그림 — source.pdf 로 다시 그린다)
SKIP_FILE = ("*.db-wal", "*.db-shm", "*.db-journal", "*-wal", "*-shm")
SECRET_FILES = ("books/secret.json", "books/secret.json.*")
STRIP_KEY_FILES = ("books/config.json", "books/config.json.*")
SECRET_KEYS = ("apikey", "api_key")
VOC_DIR = "_voc"                                                   # 백업 안에서 voc 자리
SQLITE_MAGIC = b"SQLite format 3\x00"


def _say(*a) -> None:
    print(*a, flush=True)


def data_dir() -> Path:
    from app import paths
    return paths.data_dir()


def voc_dir() -> Path | None:
    """의견 보내기 자료.  자료 폴더 안(voc/)이면 따로 담지 않는다."""
    try:
        from app import voc
        v = voc.voc_root()
    except Exception:                                    # noqa: BLE001
        return None
    try:
        v.resolve().relative_to(data_dir().resolve())
        return None
    except ValueError:
        return v


def default_dest() -> Path:
    env = (os.environ.get("PID_BACKUP_DIR") or "").strip()
    return Path(env).expanduser() if env else data_dir() / "backups"


# ---------------------------------------------------------------- 고르기
def skipped(rel: str) -> str | None:
    """빼는 이유(짧은 이름) 또는 None.  rel 은 자료 폴더 기준 '/' 경로."""
    parts = rel.split("/")
    if parts[0] in SKIP_TOP:
        return parts[0] + "/"
    if parts[0].startswith(Path(PREFIX).name) or "_before_restore_" in parts[0]:
        return parts[0] + "/"
    if any(p in SKIP_DIR_ANY for p in parts[:-1]):
        return "**/pages/"
    if any(fnmatch.fnmatch(rel, g) for g in SECRET_FILES):
        return "books/secret.json (API 키)"
    if any(fnmatch.fnmatch(parts[-1], g) for g in SKIP_FILE):
        return "-wal/-shm"
    return None


def _is_sqlite(p: Path) -> bool:
    try:
        with open(p, "rb") as f:
            return f.read(16) == SQLITE_MAGIC
    except OSError:
        return False


def _sqlite_copy(src: Path, dst: Path) -> None:
    """sqlite backup API — 쓰는 중이어도 한 파일의 일관된 판 (-wal 내용까지 담긴다)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    s = sqlite3.connect(src.resolve().as_uri() + "?mode=ro", uri=True, timeout=30.0)
    try:
        o = sqlite3.connect(tmp)
        try:
            s.backup(o)
            o.execute("PRAGMA journal_mode=DELETE")       # 사본은 한 파일로 — 열어 봐도 -wal/-shm 이 안 생긴다 (서버가 다시 WAL 로 연다)
        finally:
            o.close()
    finally:
        s.close()
    os.replace(tmp, dst)


def _integrity(db: Path) -> str:
    try:
        c = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            return str(c.execute("PRAGMA integrity_check").fetchone()[0])
        finally:
            c.close()
    except sqlite3.Error as e:
        return f"error: {e}"


def _strip_keys(obj):
    if isinstance(obj, dict):
        return {k: _strip_keys(v) for k, v in obj.items() if str(k).lower() not in SECRET_KEYS}
    if isinstance(obj, list):
        return [_strip_keys(v) for v in obj]
    return obj


def _copy_tree(src_root: Path, dst_root: Path, stats: dict, prefix: str = "", skip_top: tuple = ()) -> None:
    for p in sorted(src_root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src_root).as_posix()
        if rel.split("/")[0] in skip_top:
            continue
        why = skipped(rel) if not prefix else (None if not any(fnmatch.fnmatch(p.name, g) for g in SKIP_FILE) else "-wal/-shm")
        if why:
            stats["excluded"][why] = stats["excluded"].get(why, 0) + 1
            continue
        out = dst_root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if not prefix and any(fnmatch.fnmatch(rel, g) for g in STRIP_KEY_FILES):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                clean = _strip_keys(d)
                if clean != d:
                    stats["keys_removed"].append(rel)
                out.write_text(json.dumps(clean, ensure_ascii=False, indent=1), encoding="utf-8")
            except (OSError, ValueError):
                stats["excluded"]["books/config (읽지 못함)"] = stats["excluded"].get("books/config (읽지 못함)", 0) + 1
                continue
        elif _is_sqlite(p):
            _sqlite_copy(p, out)
            stats["sqlite"].append(prefix + rel)
        else:
            shutil.copy2(p, out)
        stats["files"] += 1
        stats["bytes"] += out.stat().st_size


# ---------------------------------------------------------------- 백업
def backup(dest: Path, keep: int = KEEP, src: Path | None = None, voc: Path | None = None,
           stamp: str | None = None) -> Path:
    src = src or data_dir()
    if voc is None:
        voc = voc_dir()
    if not src.is_dir():
        raise FileNotFoundError(f"자료 폴더가 없습니다: {src}")
    dest.mkdir(parents=True, exist_ok=True)
    stamp = stamp or time.strftime("%Y%m%d_%H%M")
    out = dest / f"{PREFIX}{stamp}"
    n = 1
    while out.exists():
        n += 1
        out = dest / f"{PREFIX}{stamp}_{n}"
    work = out.with_name(out.name + ".partial")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    stats = {"files": 0, "bytes": 0, "excluded": {}, "sqlite": [], "keys_removed": []}
    try:
        # 목적지가 자료 폴더 안이면 (기본: app\_data\backups) 그 폴더는 담지 않는다
        try:
            inside = (dest.resolve().relative_to(src.resolve()).parts or ("",))[0]
        except ValueError:
            inside = ""
        _copy_tree(src, work, stats, skip_top=(inside,) if inside else ())
        if voc and voc.is_dir():
            _copy_tree(voc, work / VOC_DIR, stats, prefix=VOC_DIR + "/")
        db = work / "app.db"
        man = {
            "made_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": str(src),
            "voc_source": str(voc) if voc and voc.is_dir() else None,
            "files": stats["files"],
            "bytes": stats["bytes"],
            "excluded": stats["excluded"],
            "sqlite": stats["sqlite"],
            "api_key_removed_from": stats["keys_removed"],
            "integrity": _integrity(db) if db.exists() else "no app.db",
        }
        (work / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
        work.rename(out)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    _say(f"백업했습니다: {out}")
    _say(f"  파일 {stats['files']}개 · {stats['bytes'] / 1e6:.1f} MB · app.db 점검: {man['integrity']}")
    if stats["excluded"]:
        _say("  뺀 것 (다시 만들어지는 자료): " + ", ".join(f"{k} {v}개" for k, v in sorted(stats["excluded"].items())))
    if stats["keys_removed"]:
        _say("  도서검토 API 키는 백업하지 않았습니다 (복구 뒤 화면에서 다시 넣거나, 복구 때 지금 키를 옮겨 줍니다).")
    if man["integrity"] not in ("ok", "no app.db"):
        _say("  [주의] app.db 점검이 'ok' 가 아닙니다 — 이 판으로 복구하지 말고 관리자에게 알려 주세요.")
    prune(dest, keep)
    return out


def listing(dest: Path) -> list[Path]:
    if not dest.is_dir():
        return []
    return sorted((p for p in dest.iterdir() if p.is_dir() and p.name.startswith(PREFIX)
                   and not p.name.endswith(".partial")), key=lambda p: p.name)


def prune(dest: Path, keep: int) -> list[Path]:
    old = listing(dest)[:-keep] if keep > 0 else []
    for p in old:
        shutil.rmtree(p, ignore_errors=True)
        _say(f"  오래된 백업을 지웠습니다 (보관 {keep}판): {p.name}")
    return old


# ---------------------------------------------------------------- 복구
def server_answers(port: int = PORT, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def _move_aside(folder: Path, keep_names: tuple, stamp: str) -> Path | None:
    """folder 안의 것을 `<folder>_before_restore_<시각>` 으로 옮긴다 (keep_names 는 제자리)."""
    if not folder.is_dir():
        return None
    aside = folder.with_name(f"{folder.name}_before_restore_{stamp}")
    aside.mkdir(parents=True, exist_ok=False)
    for p in list(folder.iterdir()):
        if p.name in keep_names:
            continue
        shutil.move(str(p), str(aside / p.name))
    return aside


def _carry_secrets(aside: Path | None, dst: Path) -> list[str]:
    """지금 쓰던 도서검토 API 키를 복구한 자료로 옮긴다 (백업에는 키가 없다)."""
    moved: list[str] = []
    if not aside:
        return moved
    old_secret = aside / "books" / "secret.json"
    if old_secret.is_file() and not (dst / "books" / "secret.json").exists():
        (dst / "books").mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_secret, dst / "books" / "secret.json")
        moved.append("books/secret.json")
    old_cfg, new_cfg = aside / "books" / "config.json", dst / "books" / "config.json"
    if old_cfg.is_file() and new_cfg.is_file():
        try:
            o = json.loads(old_cfg.read_text(encoding="utf-8"))
            n = json.loads(new_cfg.read_text(encoding="utf-8"))
            key = ((o.get("translate") or {}).get("apiKey") if isinstance(o, dict) else None)
            if key and isinstance(n, dict) and not (n.get("translate") or {}).get("apiKey"):
                n.setdefault("translate", {})["apiKey"] = key
                new_cfg.write_text(json.dumps(n, ensure_ascii=False, indent=1), encoding="utf-8")
                moved.append("books/config.json apiKey")
        except (OSError, ValueError, AttributeError):
            pass
    return moved


def restore(folder: Path, port: int = PORT, dry: bool = False, dst: Path | None = None,
            voc: Path | None = None) -> int:
    folder = folder.resolve()
    man_p = folder / "manifest.json"
    if not man_p.is_file():
        _say(f"[중단] {folder} 는 백업 폴더가 아닙니다 (manifest.json 이 없습니다).")
        return 1
    man = json.loads(man_p.read_text(encoding="utf-8"))
    if str(man.get("integrity", "ok")) not in ("ok", "no app.db"):
        _say(f"[중단] 이 백업의 app.db 점검 결과가 '{man.get('integrity')}' 입니다 — 다른 판을 고르세요.")
        return 1
    if server_answers(port):
        _say(f"[중단] 서버가 켜져 있습니다 (포트 {port}).  서버를 먼저 끄세요 — stop_pid_server.bat,\n"
             "       서비스 창(run_lan_service.bat)도 닫은 뒤 다시 실행하세요.")
        return 2
    dst = dst or data_dir()
    if voc is None:
        voc = voc_dir()
    files = [p for p in folder.rglob("*") if p.is_file() and p.name != "manifest.json"]
    n_voc = sum(1 for p in files if p.relative_to(folder).parts[0] == VOC_DIR)
    _say(f"복구할 백업: {folder.name}  (만든 때 {man.get('made_at')})")
    _say(f"  자료 폴더: {dst}  ← 파일 {len(files) - n_voc}개" + (f"\n  의견 보내기: {voc}  ← 파일 {n_voc}개" if n_voc and voc else ""))
    if dry:
        _say("  [미리보기 - 아무것도 바꾸지 않았습니다]")
        return 0
    stamp = time.strftime("%Y%m%d_%H%M%S")
    try:
        folder.relative_to(dst.resolve())
        inside = folder.relative_to(dst.resolve()).parts[0]     # 백업이 자료 폴더 안(backups/)이면 그 폴더는 제자리
    except ValueError:
        inside = None
    keep = tuple(x for x in ("backups", inside) if x)
    dst.mkdir(parents=True, exist_ok=True)
    aside = _move_aside(dst, keep, stamp)
    for p in files:
        rel = p.relative_to(folder)
        if rel.parts[0] == VOC_DIR:
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
    for side in ("app.db-wal", "app.db-shm"):              # 옛 WAL 이 새 DB 위에 재생되지 않게
        q = dst / side
        if q.exists():
            q.unlink()
    voc_aside = None
    if n_voc and voc:
        voc_aside = _move_aside(voc, (), stamp)
        voc.mkdir(parents=True, exist_ok=True)
        for p in files:
            rel = p.relative_to(folder)
            if rel.parts[0] == VOC_DIR:
                out = voc / Path(*rel.parts[1:])
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, out)
    carried = _carry_secrets(aside, dst)
    db = dst / "app.db"
    check = _integrity(db) if db.exists() else "no app.db"
    _say(f"복구했습니다.  app.db 점검: {check}")
    if aside:
        _say(f"  복구 전 자료는 지우지 않고 옮겨 두었습니다: {aside}")
    if voc_aside:
        _say(f"  복구 전 의견 보내기 자료: {voc_aside}")
    if carried:
        _say("  지금 쓰던 도서검토 API 키를 옮겨 놓았습니다.")
    _say("  이제 서버를 켜세요 (run_lan_service.bat).  화면이 정상이면 옮겨 둔 폴더는 지워도 됩니다.")
    return 0 if check in ("ok", "no app.db") else 3


# ---------------------------------------------------------------- 실행
def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                    # noqa: BLE001
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        _say(__doc__)
        return 0

    def opt(name: str, default=None):
        if name in argv:
            i = argv.index(name)
            if i + 1 < len(argv):
                v = argv[i + 1]
                del argv[i:i + 2]
                return v
            del argv[i]
        return default

    keep = int(opt("--keep", KEEP))
    port = int(opt("--port", PORT))
    rest_from = opt("--restore")
    dry = "--dry-run" in argv
    do_list = "--list" in argv
    pos = [a for a in argv if a and not a.startswith("--")]
    if rest_from:
        return restore(Path(rest_from), port=port, dry=dry)
    dest = Path(pos[0]).expanduser() if pos else default_dest()
    if do_list:
        have = listing(dest)
        _say(f"{dest} 의 백업 {len(have)}판" + (":" if have else ""))
        for p in have:
            try:
                m = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
                _say(f"  {p.name}  파일 {m.get('files')}개 · {int(m.get('bytes') or 0) / 1e6:.1f} MB · 점검 {m.get('integrity')}")
            except (OSError, ValueError):
                _say(f"  {p.name}  (manifest.json 을 읽지 못함 — 온전하지 않은 판)")
        return 0
    try:
        backup(dest, keep=keep)
    except OSError as e:
        _say(f"[실패] 백업하지 못했습니다: {e}\n       목적지 폴더에 쓸 수 있는지, 디스크가 남았는지 확인하세요.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
