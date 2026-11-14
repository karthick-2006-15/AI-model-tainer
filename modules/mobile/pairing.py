"""
Cryptographic Device Pairing & Authentication Engine
Implements one-time QR code secret exchange, device authorization, and secure session tokens.
"""

import hmac
import hashlib
import secrets
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from storage.db.connection import SessionLocal
from storage.db.models import Device
from core.config.settings import settings

logger = logging.getLogger("jarvis.mobile.pairing")


class DevicePairingManager:
    def __init__(self):
        self._pending_pairing_codes: Dict[str, Dict[str, Any]] = {}

    def initiate_pairing(self, device_name: str = "Android Device") -> Dict[str, Any]:
        """
        Generates an ephemeral 256-bit pairing secret and pairing code for QR display on HUD.
        Valid for 5 minutes.
        """
        pairing_code = f"JARVIS-{secrets.token_hex(3).upper()}"
        secret_key = secrets.token_hex(32)
        expires_at = time.time() + 300  # 5 minutes

        self._pending_pairing_codes[pairing_code] = {
            "pairing_code": pairing_code,
            "secret_key": secret_key,
            "device_name": device_name,
            "expires_at": expires_at
        }

        # QR payload contains host, port, pairing code, and secret
        qr_payload = {
            "host": settings.JARVIS_HOST,
            "port": settings.JARVIS_PORT,
            "code": pairing_code,
            "secret": secret_key
        }

        logger.info(f"Initiated pairing challenge '{pairing_code}' for {device_name}")
        return {
            "pairing_code": pairing_code,
            "secret_key": secret_key,
            "expires_in_seconds": 300,
            "qr_payload": qr_payload
        }

    def confirm_pairing(
        self,
        pairing_code: str,
        device_name: str,
        client_public_key: str
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validates pairing code submitted by the Android companion app and registers device.
        Returns:
            (success: bool, error_msg: Optional[str], device_info: Optional[Dict])
        """
        challenge = self._pending_pairing_codes.get(pairing_code)
        if not challenge:
            return False, "Invalid or expired pairing code.", None

        if time.time() > challenge["expires_at"]:
            self._pending_pairing_codes.pop(pairing_code, None)
            return False, "Pairing code has expired. Please initiate again.", None

        # Clean up used challenge
        self._pending_pairing_codes.pop(pairing_code, None)

        # Generate cryptographic device token
        device_token = self.generate_device_token(client_public_key)

        # Record or update device in database
        with SessionLocal() as db:
            device = (
                db.query(Device)
                .filter(Device.public_key == client_public_key)
                .first()
            )
            if device:
                device.device_name = device_name
                device.is_authorized = True
                device.last_seen = datetime.now(timezone.utc)
                db.commit()
                db.refresh(device)
            else:
                device = Device(
                    device_name=device_name,
                    device_type="android_mobile",
                    public_key=client_public_key,
                    is_authorized=True,
                    last_seen=datetime.now(timezone.utc)
                )
                db.add(device)
                db.commit()
                db.refresh(device)

            device_id = device.id

        logger.info(f"Device paired and authorized: {device_name} (ID: {device_id})")
        return True, None, {
            "device_id": device_id,
            "device_name": device_name,
            "token": device_token,
            "authorized": True
        }

    def verify_token(self, token: str, public_key: str) -> bool:
        """Verifies HMAC signature of a device token."""
        expected = self.generate_device_token(public_key)
        return hmac.compare_digest(token, expected)

    @staticmethod
    def generate_device_token(public_key: str) -> str:
        """Generates an HMAC-SHA256 signature binding the public key to server secret."""
        key = settings.JARVIS_SECRET_KEY.encode("utf-8")
        msg = f"jarvis_device_token:{public_key}".encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    @staticmethod
    def list_authorized_devices() -> list:
        """Returns all paired devices."""
        with SessionLocal() as db:
            devices = db.query(Device).order_by(Device.last_seen.desc()).all()
            return [
                {
                    "id": d.id,
                    "device_name": d.device_name,
                    "device_type": d.device_type,
                    "is_authorized": d.is_authorized,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    "created_at": d.created_at.isoformat() if d.created_at else None
                }
                for d in devices
            ]

    @staticmethod
    def revoke_device(device_id: str) -> bool:
        """Revokes authorization for a paired device."""
        with SessionLocal() as db:
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                return False
            device.is_authorized = False
            db.commit()
            logger.info(f"Revoked authorization for device: {device.device_name} ({device_id})")
            return True


# Global singleton instance
pairing_manager = DevicePairingManager()
