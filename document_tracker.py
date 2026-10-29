import hashlib
import json

from pathlib import Path

from knowledge_config import STATE_FILE, selected_paths


def calculate_file_hash(path: Path) -> str:
    """
    计算文件的 SHA-256。
    文件内容发生变化，Hash 就会变化。
    """

    sha256 = hashlib.sha256()

    with open(path, "rb") as file:

        while True:
            chunk = file.read(8192)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def scan_documents() -> dict[str, str]:
    return {
        relative_path: calculate_file_hash(path)
        for relative_path, path in selected_paths(require_existing=False).items()
    }


def load_previous_state() -> dict[str, str]:

    if not STATE_FILE.exists():
        return {}

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_state(state: dict[str, str]) -> None:

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2
        )


def detect_changes():

    previous = load_previous_state()
    current = scan_documents()

    previous_files = set(previous.keys())
    current_files = set(current.keys())

    added = current_files - previous_files
    deleted = previous_files - current_files

    modified = {
        filename
        for filename in previous_files & current_files
        if previous[filename] != current[filename]
    }

    unchanged = (
        previous_files
        & current_files
        - modified
    )

    return {
        "added": sorted(added),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
        "unchanged": sorted(unchanged),
        "current_state": current
    }


if __name__ == "__main__":

    changes = detect_changes()

    print("新增文件：", changes["added"])
    print("修改文件：", changes["modified"])
    print("删除文件：", changes["deleted"])
    print("未变化文件：", changes["unchanged"])

    # 目前只是测试文件检测
    # 下一步接入 Chroma 成功后才保存状态
