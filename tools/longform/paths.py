"""Workspace locations. LONGFORM_ROOT overrides the root (tests use a temp folder)."""
import os

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def root():
    return os.environ.get("LONGFORM_ROOT") or WS


def projects():
    return os.path.join(root(), "projects")


def library():
    return os.path.join(root(), "library")


def config():
    return os.path.join(root(), "config")


def state():
    """Studio runtime state (inbox, jobs, pause); gitignored."""
    d = os.path.join(root(), "studio", "state")
    os.makedirs(d, exist_ok=True)
    return d
