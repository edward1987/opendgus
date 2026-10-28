# PyInstaller entry point for opendgus-server (generated wrapper; keep in sync with [project.scripts]).
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from opendgus.server import main

    sys.exit(main())
