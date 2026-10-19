"""Editable pixels and bounded patch history, independent of the UI toolkit."""
from pathlib import Path
from PIL import Image
from processor import read_image, render_image, heal_region

class EditorDocument:
    def __init__(self, source):
        self.source = Path(source)
        self.original = read_image(source)
        self.image = self.original.copy()
        self.undo_stack = []
        self.redo_stack = []
        self.output = None
        self.revision = 0
        self.saved_revision = -1

    @property
    def dirty(self):
        return self.revision != self.saved_revision

    def commit_heal(self, mask, result):
        box = Image.fromarray(mask).getbbox()
        if box is None:
            return
        self.undo_stack.append((box,self.image.crop(box),result.crop(box)))
        self.undo_stack = self.undo_stack[-20:]
        self.redo_stack.clear()
        self.image.paste(result.crop(box),box)
        self.revision += 1

    def undo(self):
        if self.undo_stack:
            entry = self.undo_stack.pop()
            self.image.paste(entry[1],entry[0])
            self.redo_stack.append(entry)
            self.revision += 1

    def redo(self):
        if self.redo_stack:
            entry = self.redo_stack.pop()
            self.image.paste(entry[2],entry[0])
            self.undo_stack.append(entry)
            self.revision += 1

    def reset(self):
        self.image = self.original.copy()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.revision += 1

    def render(self, settings):
        return render_image(self.image,settings)
