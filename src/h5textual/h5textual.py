# A simple python library to inspect the content of h5 files
#
# Author: Urs Hofmann
# Mail: mail@hofmannu.org
# Date: 11 June 2025

import numpy as np
import os
import datetime
import h5py
import logging
from textual.widgets import Header, Footer, Tree, Markdown
from textual.containers import Vertical, Horizontal, Container
from textual.app import App, ComposeResult
from textual.logging import TextualHandler
from textual.binding import Binding
from textual import events

def HumanReadableSizeString(sizeInBytes : float):
    """
    A helper function returning the file size in bytes as a human readable string
    """
    counter = 0
    while (sizeInBytes > 1024.0):
        sizeInBytes /= 1024.0
        counter += 1
    counterStr = ["Byte", "kB", "Mb", "Gb", "Tb"]
    return "{} {}".format(round(sizeInBytes), counterStr[counter])

logging.basicConfig(
    level="NOTSET",
    handlers=[TextualHandler()],
)

class HDFTree(Tree[str]):
    def __init__(self, file: h5py.File):
        super().__init__("(root)", data="/")
        self.file = file

        self.info_panel = Markdown(id="attr_viewer") # displays size, type, and attributes
        self.data_viewer = Markdown(id="data_viewer") # displays numbers / content

        self.build_tree(self.root, self.file)

    def build_tree(self, node, h5node):

        for key in h5node:
            item = h5node[key]

            if isinstance(item, h5py.Group):
                label = f"{key}/ (Group)"
                group_node = node.add(label, data=item.name)
                group_node.allow_expand = True
                self.build_tree(group_node, item)

            elif isinstance(item, h5py.Dataset):
                try:
                    shape = item.shape
                    dtype = item.dtype
                except Exception as e:
                    shape = "?"
                    dtype = "?"
                label = f"{key} (Dataset) [{dtype}, shape={shape}]"

                dset_node = node.add(label, data=item.name)
                dset_node.allow_expand = False

    def on_tree_node_highlighted(self, event: Tree.NodeSelected) -> None:
        node = event.node
        objPath = node.data  # the path to the hdf5 object

        if objPath is None:
            return

        obj = self.file[objPath]
        
        if isinstance(obj, h5py.Dataset):
            shape = obj.shape
            dtype = obj.dtype
            kind = "Dataset"
        elif isinstance(obj, h5py.Group):
            shape = ""
            dtype = ""
            kind = "Group"
        else:
            shape = ""
            dtype = ""
            kind = "Unknown"

        def FormatAttribute(key, value):
            
            typeStr = type(value).__name__
            allowed = ["uint8", "int32", "int64", "float32", "float64", "bytes_", "str" ]
            if typeStr in allowed:
                return f"| {key} | {typeStr}  | {value} |\n"
            if typeStr == "ndarray":
                try:
                    arr_str = np.array2string(value, separator=", ", max_line_width=80).replace("\n", "")
                    return f"| {key} | array{value.shape} | `{arr_str}` |\n"
                except Exception:
                    return f"| {key} | array | <error formatting> |\n"
            else:
                return f"| {key} | {typeStr} | no display | \n"

        attrs = "| Key | Type | Value |\n"
        attrs +="| --- | ---- | ----- |\n"
        for k, v in obj.attrs.items():
            attrs += FormatAttribute(k, v)

        info_text = f"# {objPath}\n"
        info_text += f"- HDF: {kind}\n"
        if shape:
            info_text += f"- Shape: {shape}\n"
        if dtype:
            info_text += f"- Type: {dtype}\n"
        if attrs:
            info_text += f"## Attributes\n{attrs}"
        else:
            info_text += "\n(No attributes)"

        self.info_panel.update(info_text)
        self.data_viewer.update("Press i to look into data")

class HDFApp(App[None]):

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(key="i", action="inspect", description="Inspect dataset"),
        Binding(
            key="question_mark",
            action="help",
            description="Show help screen",
            key_display="?",
        ),
    ]

    CSS_PATH = "horizontal_layout.tcss"

    def __init__(self, filePath : str):
        super().__init__()
        self.filePath = filePath
        self.h5file = None

    def compose(self) -> ComposeResult:
        self.h5file = h5py.File(self.filePath, "r")

        self.hdfTree = HDFTree(self.h5file)
        with Horizontal():
            yield self.hdfTree
            with Vertical():
                yield self.hdfTree.info_panel
                yield self.hdfTree.data_viewer
        yield Footer()
        yield Header()

    def inspect_dataset(self, path: str) -> None:
        try:
            ds = self.h5file[path]
            if not isinstance(ds, h5py.Dataset):
                self.hdfTree.info_panel.update("_Not a dataset_")
                return

            data = ds[()]

            preview =  "# Data Preview\n"
            preview += "## Statistics\n"
            preview += " - min: {}\n".format(data.min())
            preview += " - max: {}\n".format(data.max())
            preview += " - mean: {} \n".format(data.mean())
            preview += "## Data\n"
            preview += f"{data}"

        except Exception as e:
            preview = f"⚠️ _Error reading dataset_: `{e}`"

        self.hdfTree.data_viewer.update(preview)

    def action_inspect(self) -> None:
        selected = self.hdfTree.cursor_node
        if selected and selected.data:
            path = selected.data  # your HDFTree stores HDF5 paths
            self.call_later(self.inspect_dataset, path)

    def on_mount(self) -> None:        
        # get some details about the file for the headline of the App
        stat = os.stat(self.filePath)

        fileSize = stat.st_size
        sizeStr = HumanReadableSizeString(fileSize)

        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
        mtimeStr = mtime.strftime("%Y-%m-%d %H:%M:%S")

        info_text = "File: {}, Last changed: {}, Size: {}".format(self.filePath, mtimeStr, sizeStr)

        self.title = "h5textual"
        self.sub_title = info_text

    def on_shutdown(self):
        if self.h5file:
            self.h5file.close()


