from h5textual.h5textual import HDFApp
import argparse

def hdf_app():
    parser = argparse.ArgumentParser(description="h5textual")
    parser.add_argument("filePath", help="the path to the hdf file you want to inspect")
    args = parser.parse_args()

    app = HDFApp(args.filePath)
    app.run()
