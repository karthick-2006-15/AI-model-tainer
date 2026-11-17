"""
Mobile Integration & Pairing REST Endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import shutil
import tempfile
from modules.mobile.pairing import pairing_manager

router = APIRouter(prefix="/api/mobile", tags=["Mobile"])


class InitiatePairingRequest(BaseModel):
    device_name: Optional[str] = "Android Device"


class ConfirmPairingRequest(BaseModel):
    pairing_code: str
    device_name: str
    public_key: str


@router.post("/pairing/initiate")
def initiate_pairing(request: InitiatePairingRequest):
    """Generates an ephemeral pairing code and QR payload to display on HUD."""
    return pairing_manager.initiate_pairing(device_name=request.device_name or "Android Device")


@router.post("/pairing/confirm")
def confirm_pairing(request: ConfirmPairingRequest):
    """Validates pairing code, generates device token, and registers device in database."""
    success, error_msg, device_info = pairing_manager.confirm_pairing(
        pairing_code=request.pairing_code,
        device_name=request.device_name,
        client_public_key=request.public_key
    )
    if not success:
        raise HTTPException(status_code=400, detail=error_msg)
    return device_info


@router.get("/devices")
def list_devices():
    """Lists all paired devices and authorization states."""
    return pairing_manager.list_authorized_devices()


@router.delete("/devices/{device_id}")
def revoke_device(device_id: str):
    """Revokes a paired mobile device."""
    success = pairing_manager.revoke_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found.")
    return {"revoked": True, "device_id": device_id}


@router.post("/files/send-to-laptop")
async def receive_mobile_file(file: UploadFile = File(...)):
    """Receives a file transferred from Android companion and saves to MobileSync directory."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    safe_filename = os.path.basename(file.filename).strip()
    if not safe_filename or safe_filename in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename or path traversal detected.")

    sync_dir = os.path.abspath(os.path.join(os.path.expanduser("~"), "Downloads", "MobileSync"))
    os.makedirs(sync_dir, exist_ok=True)
    destination = os.path.join(sync_dir, safe_filename)

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "success": True,
        "file_name": safe_filename,
        "saved_path": destination,
        "size_bytes": os.path.getsize(destination)
    }


@router.get("/files/download")
def download_file_to_mobile(file_path: str = Query(...)):
    """Downloads an authorized file from laptop to mobile companion."""
    sync_dir = os.path.abspath(os.path.join(os.path.expanduser("~"), "Downloads", "MobileSync"))

    if os.path.isabs(file_path):
        abs_path = os.path.abspath(file_path)
    else:
        abs_path = os.path.abspath(os.path.join(sync_dir, file_path))

    # Path boundary enforcement: prevent arbitrary file reading (e.g. .env, SSH keys)
    try:
        if os.path.commonpath([abs_path, sync_dir]) != sync_dir:
            raise HTTPException(status_code=403, detail="Access denied: Requested file is outside authorized MobileSync directory.")
    except (ValueError, Exception):
        raise HTTPException(status_code=403, detail="Access denied: Requested file is outside authorized MobileSync directory.")

    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(
        abs_path,
        filename=os.path.basename(abs_path)
    )
