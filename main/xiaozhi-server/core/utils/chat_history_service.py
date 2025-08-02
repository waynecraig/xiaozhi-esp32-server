import datetime
import json
import jwt
from typing import Optional, Dict, Any
from config.logger import setup_logging

TAG = __name__


class ChatHistoryService:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.chat_history_config = config.get("chat-history-server", {})
        self.enabled = bool(self.chat_history_config.get("url") and self.chat_history_config.get("secret"))
        
        if self.enabled:
            self.base_url = self.chat_history_config["url"].rstrip("/")
            self.secret = self.chat_history_config["secret"]
            self.logger.bind(tag=TAG).info(f"Chat history service enabled: {self.base_url}")
        else:
            self.logger.bind(tag=TAG).info("Chat history service disabled - no configuration found")

    def _generate_jwt_token(self, device_id: str) -> str:
        """Generate JWT token for chat history server authentication"""
        payload = {
            "device_id": device_id,
            "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=3600),
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def _make_request_sync(self, method: str, url: str, headers: Dict[str, str], data: Optional[Dict[str, Any]] = None) -> bool:
        """Make synchronous HTTP request to chat history server"""
        if not self.enabled:
            return False
            
        try:
            import requests
            timeout = 10  # 10 second timeout
            if method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
                if response.status_code in [200, 201]:
                    return True
                else:
                    self.logger.bind(tag=TAG).warning(
                        f"Chat history request failed: {response.status_code} - {response.text}"
                    )
                    return False
            else:
                self.logger.bind(tag=TAG).error(f"Unsupported HTTP method: {method}")
                return False
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat history request error: {e}")
            return False

    def report_message(self, device_id: str, role: str, text: str, image_base64: Optional[str] = None) -> None:
        """Report a chat message to the chat history server"""
        if not self.enabled or not device_id:
            return

        try:
            # Generate JWT token
            token = self._generate_jwt_token(device_id)
            
            # Prepare request data
            data = {
                "role": role,
                "text": text
            }
            if image_base64:
                data["image_base64"] = image_base64

            # Prepare headers
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Make request
            url = f"{self.base_url}/devices/{device_id}/messages"
            success = self._make_request_sync("POST", url, headers, data)
            
            if success:
                self.logger.bind(tag=TAG).debug(f"Successfully reported message for device {device_id}")
            else:
                self.logger.bind(tag=TAG).warning(f"Failed to report message for device {device_id}")
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error reporting message: {e}")

    def report_chat_end(self, device_id: str) -> None:
        """Report that a chat session has ended"""
        if not self.enabled or not device_id:
            return

        try:
            # Generate JWT token
            token = self._generate_jwt_token(device_id)
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Make request
            url = f"{self.base_url}/devices/{device_id}/chat_end"
            success = self._make_request_sync("POST", url, headers)
            
            if success:
                self.logger.bind(tag=TAG).debug(f"Successfully reported chat end for device {device_id}")
            else:
                self.logger.bind(tag=TAG).warning(f"Failed to report chat end for device {device_id}")
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error reporting chat end: {e}") 