import argparse

from culturechamp_ml import __version__


def main() -> None:
    parser = argparse.ArgumentParser(description="Лад ML workspace")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()
    print("No ML experiment is configured.")
