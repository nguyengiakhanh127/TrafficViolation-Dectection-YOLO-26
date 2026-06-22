import sys
import os
import threading

# Đảm bảo project root nằm trong sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()


def start_web_server(host: str, port: int):
    """Khởi chạy FastAPI server trong thread riêng."""
    import uvicorn
    from web.backend.main import app
    uvicorn.run(app, host=host, port=port, log_level="info")


def start_gui():
    """Khởi chạy giao diện PyQt6 (blocking — chạy trên main thread)."""
    from PyQt6.QtWidgets import QApplication
    from shared.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def main():
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", 8000))

    # Khởi chạy web server trong daemon thread
    web_thread = threading.Thread(
        target=start_web_server,
        args=(host, port),
        daemon=True
    )
    web_thread.start()

    # Khởi chạy GUI trên main thread (bắt buộc cho PyQt6)
    start_gui()


if __name__ == "__main__":
    main()
