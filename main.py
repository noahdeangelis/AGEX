import argparse

def main():
    parser = argparse.ArgumentParser(description="AGEX AI Agent")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Launch the terminal interface",
    )

    args = parser.parse_args()

    if args.cli:
        from interfaces.cli.cli import run_cli
        run_cli()
    else:
        from interfaces.gui.gui import run_gui
        run_gui()


if __name__ == "__main__":
    main()