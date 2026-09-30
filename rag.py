from pathlib import Path


def load_document(file_path: str) -> str:
    path = Path(file_path)

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


if __name__ == "__main__":
    document = load_document("data/employee_policy.md")

    print(document)