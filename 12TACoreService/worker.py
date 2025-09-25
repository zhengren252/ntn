#!/usr/bin/env python3
"""Worker process entry point for TACoreService."""

import os
import sys
import signal
import logging
import asyncio
import threading
from typing import Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tacoreservice.config import get_settings
from tacoreservice.workers.worker import Worker
from tacoreservice.monitoring.logger import setup_logging


class WorkerProcess:
    """Worker process manager."""

    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.worker: Optional[Worker] = None
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

        self.logger.info("Worker process initialized")

    def setup(self):
        """Setup worker process."""
        try:
            # Setup logging
            setup_logging()
            self.logger.info("Logging setup completed")

            # Initialize worker
            self.logger.info("Initializing Worker instance...")
            self.worker = Worker()
            self.logger.info("Worker instance initialized successfully")

            self.logger.info("Worker process setup completed")

        except Exception as e:
            self.logger.error(f"Failed to setup worker process: {e}")
            import traceback

            self.logger.error(f"Setup traceback: {traceback.format_exc()}")
            raise

    def start(self):
        """Start the worker process."""
        try:
            self.running = True

            self.logger.info("Starting worker process...")

            if self.worker:
                self.logger.info("Worker instance exists, starting thread...")

                # Start worker in a separate thread with exception handling
                def worker_thread_wrapper():
                    try:
                        self.logger.info("Worker thread wrapper starting...")
                        self.logger.info("About to call worker.start()")
                        print("DEBUG: About to call worker.start()")
                        self.worker.start()
                        print("DEBUG: worker.start() completed")
                        self.logger.info("worker.start() completed")
                    except Exception as e:
                        print(f"DEBUG: Worker thread failed: {e}")
                        self.logger.error(f"Worker thread failed: {e}")
                        import traceback

                        print(
                            f"DEBUG: Worker thread traceback: {traceback.format_exc()}"
                        )
                        self.logger.error(
                            f"Worker thread traceback: {traceback.format_exc()}"
                        )
                        # Re-raise the exception to ensure it's not silently ignored
                        raise

                print("DEBUG: Creating worker thread...")
                self.worker_thread = threading.Thread(
                    target=worker_thread_wrapper, daemon=True
                )
                print("DEBUG: Worker thread created, starting...")
                self.worker_thread.start()
                print("DEBUG: Worker thread start() called")
                self.logger.info("Worker thread started")
                print(f"DEBUG: Worker thread is_alive: {self.worker_thread.is_alive()}")
                import time

                time.sleep(1)
                print(
                    f"DEBUG: Worker thread is_alive after 1s: {self.worker_thread.is_alive()}"
                )
            else:
                self.logger.error("No worker instance available!")

        except Exception as e:
            self.logger.error(f"Failed to start worker process: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.stop()
            raise

    def stop(self):
        """Stop the worker process."""
        try:
            self.running = False

            self.logger.info("Stopping worker process...")

            if self.worker:
                self.worker.stop()
                self.logger.info("Worker stopped")

            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=5)
                self.logger.info("Worker thread joined")

            self.logger.info("Worker process stopped successfully")

        except Exception as e:
            self.logger.error(f"Error stopping worker process: {e}")


def setup_signal_handlers(worker_process: WorkerProcess):
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down worker gracefully...")
        worker_process.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main worker entry point."""
    worker_process = WorkerProcess()

    try:
        # Setup worker process
        worker_process.setup()

        # Setup signal handlers
        setup_signal_handlers(worker_process)

        # Start worker process
        worker_process.start()

        # Keep the main thread alive while worker is running
        while worker_process.running:
            try:
                import time

                time.sleep(1)
            except KeyboardInterrupt:
                break

    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt")
    except Exception as e:
        logging.error(f"Worker process failed: {e}")
        sys.exit(1)
    finally:
        worker_process.stop()


if __name__ == "__main__":
    main()
