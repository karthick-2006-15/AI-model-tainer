"""
Unit tests for Android Mobile Companion Integration, Pairing & File Transfer
"""

import pytest
import io
from starlette.testclient import TestClient
from api.main import app
from modules.mobile.pairing import pairing_manager


def test_pairing_manager_lifecycle():
    # 1. Initiate pairing
    init_res = pairing_manager.initiate_pairing(device_name="Pixel 8 Pro")
    assert "pairing_code" in init_res
    assert "secret_key" in init_res
    assert "qr_payload" in init_res
    pairing_code = init_res["pairing_code"]

    # 2. Confirm pairing with client public key
    client_pub_key = "test_ed25519_pubkey_abcdef123456"
    success, err, device_info = pairing_manager.confirm_pairing(
        pairing_code=pairing_code,
        device_name="Pixel 8 Pro",
        client_public_key=client_pub_key
    )
    assert success is True
    assert err is None
    assert device_info["device_name"] == "Pixel 8 Pro"
    assert "token" in device_info
    device_id = device_info["device_id"]

    # 3. Verify generated token
    token = device_info["token"]
    assert pairing_manager.verify_token(token, client_pub_key) is True
    assert pairing_manager.verify_token("invalid_token", client_pub_key) is False

    # 4. List devices
    devices = pairing_manager.list_authorized_devices()
    assert any(d["id"] == device_id for d in devices)

    # 5. Revoke device
    revoked = pairing_manager.revoke_device(device_id)
    assert revoked is True


def test_mobile_rest_endpoints():
    with TestClient(app) as client:
        # 1. Initiate pairing API
        init_res = client.post("/api/mobile/pairing/initiate", json={"device_name": "Galaxy S24"})
        assert init_res.status_code == 200
        init_data = init_res.json()
        code = init_data["pairing_code"]

        # 2. Confirm pairing API
        confirm_res = client.post("/api/mobile/pairing/confirm", json={
            "pairing_code": code,
            "device_name": "Galaxy S24",
            "public_key": "pub_key_s24_galaxy_999"
        })
        assert confirm_res.status_code == 200
        confirm_data = confirm_res.json()
        assert confirm_data["authorized"] is True
        device_id = confirm_data["device_id"]

        # 3. List devices API
        list_res = client.get("/api/mobile/devices")
        assert list_res.status_code == 200
        devices = list_res.json()
        assert any(d["id"] == device_id for d in devices)

        # 4. File transfer from mobile to laptop
        dummy_file = io.BytesIO(b"Mobile captured image or audio payload")
        file_res = client.post(
            "/api/mobile/files/send-to-laptop",
            files={"file": ("mobile_photo.jpg", dummy_file, "image/jpeg")}
        )
        assert file_res.status_code == 200
        file_data = file_res.json()
        assert file_data["success"] is True
        assert file_data["file_name"] == "mobile_photo.jpg"
