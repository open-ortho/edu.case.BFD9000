"""Tests for BoxStorageBackend using a fake in-memory Box client.

The fake client simulates the Box folder/file tree entirely in memory and
records every API call so tests can assert on the exact sequence of operations.
No real Box credentials or network access are required.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

import archive.storage as storage_module
from archive.storage import BoxStorageBackend
from box_sdk_gen import BoxAPIError as _RealBoxAPIError, FileBaseTypeField
from box_sdk_gen.schemas.folder_mini import FolderBaseTypeField

ROOT_FOLDER = "root-0"



class _Conflict(_RealBoxAPIError):
    """Minimal BoxAPIError carrying a 409 status and the conflicting file id."""

    def __init__(self, file_id: str) -> None:
        object.__init__(self)  # bypass SDK constructor; we only need response_info
        self.response_info = SimpleNamespace(
            status_code=409,
            context_info={"conflicts": {"id": file_id}},
        )

class _Item:
    def __init__(self, item_id: str, name: str, type_) -> None:
        self.id = item_id
        self.name = name
        self.type = type_


class FakeBoxClient:
    """Simulated Box client backed by an in-memory folder/file tree.

    Tree structure::

        _tree: {folder_id: [_Item, ...]}   # folder contents
        _content: {file_id: bytes}          # file bodies

    All operations are recorded in ``calls`` as
    ``(method_label, *positional_args)`` tuples.
    """

    def __init__(self, root_folder_id: str = ROOT_FOLDER) -> None:
        self._tree: dict[str, list[_Item]] = {root_folder_id: []}
        self._content: dict[str, bytes] = {}
        self._counter = 0
        self.calls: list[tuple] = []

    def _new_id(self, prefix: str = "item") -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"

    # test-setup helpers

    def seed_folder(self, parent_id: str, name: str) -> str:
        """Insert a folder into the tree without recording an API call."""
        fid = self._new_id("folder")
        self._tree[parent_id].append(_Item(fid, name, FolderBaseTypeField.FOLDER))
        self._tree[fid] = []
        return fid

    def seed_file(self, folder_id: str, name: str, content: bytes = b"data") -> str:
        """Insert a file into the tree without recording an API call."""
        fid = self._new_id("file")
        self._tree[folder_id].append(_Item(fid, name, FileBaseTypeField.FILE))
        self._content[fid] = content
        return fid

    # SDK surface (accessed as client.folders, client.uploads, …)

    @property
    def folders(self) -> _Folders:
        return _Folders(self)

    @property
    def uploads(self) -> _Uploads:
        return _Uploads(self)

    @property
    def files(self) -> _Files:
        return _Files(self)

    @property
    def downloads(self) -> _Downloads:
        return _Downloads(self)


class _Folders:
    def __init__(self, c: FakeBoxClient) -> None:
        self._c = c

    def get_folder_items(self, folder_id: str, **_kw):
        self._c.calls.append(("folders.get_folder_items", folder_id))
        entries = list(self._c._tree.get(folder_id, []))
        return SimpleNamespace(entries=entries, next_marker=None)

    def create_folder(self, name: str, parent):
        self._c.calls.append(("folders.create_folder", name, parent.id))
        fid = self._c._new_id("folder")
        item = _Item(fid, name, FolderBaseTypeField.FOLDER)
        self._c._tree[parent.id].append(item)
        self._c._tree[fid] = []
        return item


class _Uploads:
    def __init__(self, c: FakeBoxClient) -> None:
        self._c = c

    def preflight_file_upload_check(self, name: str, size: int, parent):
        self._c.calls.append(("uploads.preflight", name, parent.id))
        for item in self._c._tree.get(parent.id, []):
            if item.name == name:
                raise _Conflict(item.id)
        return SimpleNamespace(upload_url="https://upload.box.com/fake")

    def upload_file(self, attributes, file):
        folder_id = attributes.parent.id
        name = attributes.name
        self._c.calls.append(("uploads.upload_file", name, folder_id))
        fid = self._c._new_id("file")
        content = file.read() if hasattr(file, "read") else b""
        item = _Item(fid, name, FileBaseTypeField.FILE)
        self._c._tree[folder_id].append(item)
        self._c._content[fid] = content
        return SimpleNamespace(entries=[item])


class _Files:
    def __init__(self, c: FakeBoxClient) -> None:
        self._c = c

    def get_file_by_id(self, file_id: str):
        self._c.calls.append(("files.get_file_by_id", file_id))
        for items in self._c._tree.values():
            for item in items:
                if item.id == file_id and item.type == FileBaseTypeField.FILE:
                    return SimpleNamespace(name=item.name)
        raise RuntimeError(f"No file with id {file_id!r} in fake filesystem")

    def delete_file_by_id(self, file_id: str):
        self._c.calls.append(("files.delete_file_by_id", file_id))
        for items in self._c._tree.values():
            for item in list(items):
                if item.id == file_id:
                    items.remove(item)
                    self._c._content.pop(file_id, None)
                    return
        raise RuntimeError(f"No file with id {file_id!r} to delete")


class _Downloads:
    def __init__(self, c: FakeBoxClient) -> None:
        self._c = c

    def download_file(self, file_id: str):
        self._c.calls.append(("downloads.download_file", file_id))
        content = self._c._content.get(file_id)
        return io.BytesIO(content) if content is not None else None


# Test cases

class BoxStorageBackendTests(TestCase):
    """BoxStorageBackend behaviour verified against the fake client."""

    def setUp(self):
        storage_module._box_item_cache.clear()
        self.fs = FakeBoxClient(root_folder_id=ROOT_FOLDER)
        self._patches = [
            patch("archive.storage._get_box_client", return_value=self.fs),
            patch("BFD9000.settings.BOX_FOLDER_ID", ROOT_FOLDER),
        ]
        for p in self._patches:
            p.start()
        self.backend = BoxStorageBackend()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        storage_module._box_item_cache.clear()

    # helpers -----------------------------------------------------------------

    def _call_names(self) -> list[str]:
        return [c[0] for c in self.fs.calls]

    def test_upload_file_to_root_returns_box_link(self):
        """Uploading a file returns a box:// link and stores the content."""
        link = self.backend.upload(io.BytesIO(b"hello"), "scan.jpg")

        self.assertTrue(link.startswith("box://"), link)
        file_id = link[len("box://"):]
        self.assertEqual(self.fs._content[file_id], b"hello")

    def test_upload_issues_preflight_then_upload(self):
        """A successful upload always runs preflight before upload_file."""
        self.backend.upload(io.BytesIO(b"x"), "scan.jpg")

        names = self._call_names()
        self.assertIn("uploads.preflight", names)
        self.assertIn("uploads.upload_file", names)
        self.assertLess(
            names.index("uploads.preflight"),
            names.index("uploads.upload_file"),
        )

    def test_upload_creates_missing_intermediate_folders(self):
        """Uploading to a nested path creates every folder that is absent."""
        self.backend.upload(io.BytesIO(b"img"), "patient/scan/image.tif")

        create_calls = [c for c in self.fs.calls if c[0] == "folders.create_folder"]
        created_names = [c[1] for c in create_calls]
        self.assertEqual(created_names, ["patient", "scan"])

    def test_upload_reuses_existing_folders(self):
        """Uploading to a path whose folders already exist never calls create_folder."""
        patient_id = self.fs.seed_folder(ROOT_FOLDER, "patient")

        self.backend.upload(io.BytesIO(b"img"), "patient/scan.jpg")

        create_calls = [c for c in self.fs.calls if c[0] == "folders.create_folder"]
        self.assertEqual(create_calls, [])
        # File ended up in the pre-existing patient folder
        file_items = [
            i for i in self.fs._tree[patient_id] if i.type == FileBaseTypeField.FILE
        ]
        self.assertEqual(len(file_items), 1)

    def test_upload_conflict_deletes_old_file_then_reuploads(self):
        """A 409 conflict on preflight causes the old file to be deleted and re-uploaded."""
        old_id = self.fs.seed_file(ROOT_FOLDER, "scan.jpg", b"old content")

        link = self.backend.upload(io.BytesIO(b"new content"), "scan.jpg")

        # Old file removed
        self.assertNotIn(old_id, self.fs._content)
        # New file present with correct content
        new_id = link[len("box://"):]
        self.assertEqual(self.fs._content[new_id], b"new content")
        # delete_file_by_id was called exactly once with the old id
        deletes = [c for c in self.fs.calls if c[0] == "files.delete_file_by_id"]
        self.assertEqual(len(deletes), 1)
        self.assertEqual(deletes[0][1], old_id)

    def test_upload_large_file_logs_warning(self):
        """Files over 50 MB log a warning (chunked upload not yet implemented)."""
        big = io.BytesIO(b"\x00" * 50_000_001)
        with self.assertLogs("archive.storage", level="WARNING") as cm:
            self.backend.upload(big, "big.bin")
        self.assertTrue(any("50 MB" in line for line in cm.output))

    def test_list_empty_folder_returns_empty(self):
        self.fs.seed_folder(ROOT_FOLDER, "empty")
        self.assertCountEqual(self.backend.list("empty"), [])

    def test_list_returns_box_links_for_files(self):
        folder_id = self.fs.seed_folder(ROOT_FOLDER, "scans")
        fid1 = self.fs.seed_file(folder_id, "a.jpg")
        fid2 = self.fs.seed_file(folder_id, "b.jpg")

        links = self.backend.list("scans")

        self.assertCountEqual(links, [f"box://{fid1}", f"box://{fid2}"])

    def test_list_navigates_nested_path(self):
        patient_id = self.fs.seed_folder(ROOT_FOLDER, "patient")
        scan_id = self.fs.seed_folder(patient_id, "scan")
        fid = self.fs.seed_file(scan_id, "img.jpg")

        links = self.backend.list("patient/scan")

        self.assertCountEqual(links, [f"box://{fid}"])

    def test_list_missing_path_returns_empty(self):
        self.assertCountEqual(self.backend.list("does/not/exist"), [])

    def test_list_excludes_subfolders(self):
        """Only file entries are included; sub-folders are omitted."""
        folder_id = self.fs.seed_folder(ROOT_FOLDER, "parent")
        self.fs.seed_folder(folder_id, "child_dir")
        fid = self.fs.seed_file(folder_id, "file.jpg")

        links = self.backend.list("parent")

        self.assertCountEqual(links, [f"box://{fid}"])

    def test_download_returns_correct_stream_and_filename(self):
        fid = self.fs.seed_file(ROOT_FOLDER, "photo.jpg", b"pixels")

        stream, filename = self.backend.download(f"box://{fid}")

        self.assertEqual(filename, "photo.jpg")
        self.assertEqual(stream.read(), b"pixels")

    def test_download_issues_get_file_info_then_stream(self):
        """Download always fetches file metadata before streaming content."""
        fid = self.fs.seed_file(ROOT_FOLDER, "x.jpg", b"x")

        self.backend.download(f"box://{fid}")

        self.assertEqual(
            self._call_names(),
            ["files.get_file_by_id", "downloads.download_file"],
        )

    def test_download_raises_when_stream_is_none(self):
        """RuntimeError is raised when Box returns no byte stream."""
        fid = self.fs.seed_file(ROOT_FOLDER, "ghost.jpg", b"will be removed")
        del self.fs._content[fid]  # simulate Box returning None for the body

        with self.assertRaises(RuntimeError):
            self.backend.download(f"box://{fid}")
