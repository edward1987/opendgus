# PyInstaller entry point for opendgus-load (generated wrapper; keep in sync with [project.scripts]).
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from opendgus.device.dwinload import main

    sys.exit(main())
