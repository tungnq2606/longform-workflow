"""Stage the files a render needs into <project>/public/ (Remotion copies its public dir into the bundle,
so it must never be the whole workspace). Paths are workspace-relative and keep their relative layout."""
import os
import shutil

from tools.longform import paths


def stage(project_dir, files):
    pub = os.path.join(project_dir, "public")
    os.makedirs(pub, exist_ok=True)
    root = os.path.realpath(paths.root())
    for rel in files:
        src = os.path.realpath(os.path.join(root, rel))
        if os.path.isabs(rel) or not src.startswith(root + os.sep):
            raise ValueError("stage: %s is not inside the workspace" % rel)
        dst = os.path.join(pub, os.path.relpath(src, root))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    return pub
