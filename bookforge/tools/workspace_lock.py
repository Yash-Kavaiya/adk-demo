"""Thread-safe workspace operations with locking for parallel execution.

This module provides a locking mechanism for manifest updates to prevent
race conditions when multiple videos are processed concurrently.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from bookforge.schemas import ChannelManifest
from bookforge.tools.workspace import Workspace

# Global lock per workspace (keyed by workspace root path)
_workspace_locks: dict[str, asyncio.Lock] = {}


def get_workspace_lock(workspace_root: Path) -> asyncio.Lock:
    """Get or create a lock for the given workspace.
    
    This ensures that manifest updates for the same workspace are serialized,
    preventing race conditions when multiple videos are processed in parallel.
    """
    key = str(workspace_root.resolve())
    if key not in _workspace_locks:
        _workspace_locks[key] = asyncio.Lock()
    return _workspace_locks[key]


async def safe_update_video(
    ws: Workspace, video_id: str, **changes: Any
) -> ChannelManifest:
    """Thread-safe video status update with automatic locking.
    
    This function wraps Workspace.update_video() with an asyncio lock to
    prevent concurrent modification of the manifest file.
    
    Args:
        ws: The Workspace instance
        video_id: Video ID to update
        **changes: Status fields to update (status, error, etc.)
    
    Returns:
        Updated manifest
    
    Example:
        await safe_update_video(ws, "abc123", status="verified", error="")
    """
    lock = get_workspace_lock(ws.root)
    async with lock:
        # Perform the update atomically
        return ws.update_video(video_id, **changes)


async def safe_load_manifest(ws: Workspace) -> ChannelManifest:
    """Thread-safe manifest loading.
    
    While loading is typically safe without a lock, this function is provided
    for consistency and can be used when you need to ensure no writes happen
    during a read operation.
    """
    lock = get_workspace_lock(ws.root)
    async with lock:
        return ws.load_manifest()


async def safe_save_manifest(ws: Workspace, manifest: ChannelManifest) -> None:
    """Thread-safe manifest saving.
    
    Use this when you need to save an entire manifest that was modified
    outside of update_video().
    """
    lock = get_workspace_lock(ws.root)
    async with lock:
        ws.save_manifest(manifest)
