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
