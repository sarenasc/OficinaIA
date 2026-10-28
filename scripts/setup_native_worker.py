"""Provision a project-local stdlib worker; no downloads or global installations."""
import argparse
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    root = args.data_dir.resolve() / "runtime" / "native-venv"
    venv.EnvBuilder(with_pip=False).create(root)
    print(f"Worker preparado en {root}. Paquetes externos: ninguno. No es un sandbox.")


if __name__ == "__main__":
    main()
