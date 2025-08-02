import queue
import threading
import time
from typing import Optional, Dict, Any
from core.utils.chat_history_service import ChatHistoryService

TAG = __name__


class ChatHistoryQueue:
    """Global chat history reporting queue for non-blocking reporting"""
    
    def __init__(self, config: dict):
        self.chat_history_service = ChatHistoryService(config)
        self.report_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        self._start_worker()
    
    def _start_worker(self):
        """Start the background worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def _worker(self):
        """Background worker that processes chat history reports"""
        while not self.stop_event.is_set():
            try:
                # Get item from queue with timeout to allow checking stop event
                item = self.report_queue.get(timeout=1)
                if item is None:  # Poison pill
                    break
                
                try:
                    # Process the report
                    self._process_report(*item)
                except Exception as e:
                    # Log error but continue processing
                    print(f"Chat history report processing error: {e}")
                finally:
                    self.report_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Chat history queue worker error: {e}")
    
    def _process_report(self, device_id: str, role: str, text: str, image_base64: Optional[str] = None):
        """Process a single chat history report"""
        if role == "user":
            self.chat_history_service.report_message(device_id, role, text, image_base64)
        elif role == "assistant":
            self.chat_history_service.report_message(device_id, role, text)
        elif role == "chat_end":
            self.chat_history_service.report_chat_end(device_id)
    
    def enqueue_message(self, device_id: str, role: str, text: str, image_base64: Optional[str] = None):
        """Enqueue a message for reporting"""
        if not self.chat_history_service.enabled or not device_id:
            return
        
        try:
            self.report_queue.put((device_id, role, text, image_base64))
        except Exception as e:
            print(f"Failed to enqueue chat history message: {e}")
    
    def enqueue_chat_end(self, device_id: str):
        """Enqueue a chat end report"""
        if not self.chat_history_service.enabled or not device_id:
            return
        
        try:
            self.report_queue.put((device_id, "chat_end", "", None))
        except Exception as e:
            print(f"Failed to enqueue chat end report: {e}")
    
    def stop(self):
        """Stop the worker thread"""
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2)


# Global instance
_chat_history_queue = None


def get_chat_history_queue(config: dict = None) -> ChatHistoryQueue:
    """Get or create the global chat history queue instance"""
    global _chat_history_queue
    if _chat_history_queue is None and config is not None:
        _chat_history_queue = ChatHistoryQueue(config)
    return _chat_history_queue


def enqueue_chat_message(device_id: str, role: str, text: str, image_base64: Optional[str] = None):
    """Enqueue a chat message for reporting"""
    queue = get_chat_history_queue()
    if queue:
        queue.enqueue_message(device_id, role, text, image_base64)


def enqueue_chat_end(device_id: str):
    """Enqueue a chat end report"""
    queue = get_chat_history_queue()
    if queue:
        queue.enqueue_chat_end(device_id) 