"""WebSocket 终端端点。

使用 PTY（伪终端）实现真实终端体验：
- Windows: winpty (pywinpty)
- Linux/Mac: pty (标准库)

协议：
- 客户端 → 服务端：{ "type": "input", "data": "ls\r" }
- 服务端 → 客户端：{ "type": "output", "data": "..." }
- 客户端 → 服务端：{ "type": "resize", "cols": 80, "rows": 24 }
"""
import asyncio
import json
import os
import sys

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["Terminal"])


def _create_pty(cols: int = 80, rows: int = 24):
    """创建 PTY，跨平台兼容。"""
    if sys.platform == "win32":
        # Windows: winpty
        from winpty import PTY

        pty = PTY(cols, rows)
        # 默认用系统 shell
        shell = os.environ.get("COMSPEC", "cmd.exe")
        pty.spawn(shell)
        return pty, "winpty"
    else:
        # Linux/Mac: pty
        import pty as pty_module
        import termios
        import struct
        import fcntl

        master_fd, slave_fd = pty_module.openpty()
        # 设置窗口大小
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

        pid = os.fork()
        if pid == 0:
            # 子进程
            os.close(master_fd)
            os.setsid()
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            shell = os.environ.get("SHELL", "/bin/bash")
            os.execvp(shell, [shell])
        else:
            os.close(slave_fd)
            return (master_fd, pid), "posix"


def _read_pty(pty, backend: str) -> str:
    """从 PTY 读取输出。"""
    if backend == "winpty":
        return pty.read()
    else:
        master_fd, _ = pty
        try:
            data = os.read(master_fd, 65536)
            return data.decode("utf-8", errors="replace")
        except OSError:
            return ""


def _write_pty(pty, backend: str, data: str) -> None:
    """向 PTY 写入输入。"""
    if backend == "winpty":
        pty.write(data)
    else:
        master_fd, _ = pty
        os.write(master_fd, data.encode("utf-8"))


def _resize_pty(pty, backend: str, cols: int, rows: int) -> None:
    """调整 PTY 窗口大小。"""
    if backend == "winpty":
        pty.set_size(cols, rows)
    else:
        import struct
        import fcntl
        import termios

        master_fd, _ = pty
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)


@router.websocket("/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket 终端。"""
    await websocket.accept()

    # 工作目录：项目运行时目录
    cwd = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )

    # 创建 PTY
    try:
        pty, backend = _create_pty()
    except Exception as e:
        await websocket.send_text(
            json.dumps({"type": "output", "data": f"\r\n终端启动失败: {e}\r\n"})
        )
        await websocket.close()
        return

    await websocket.send_text(
        json.dumps(
            {
                "type": "output",
                "data": f"\x1b[32m终端已连接 (cwd: {cwd})\x1b[0m\r\n\r\n",
            }
        )
    )

    # 后台读取 PTY 输出并推给前端
    async def read_loop():
        loop = asyncio.get_event_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, _read_pty, pty, backend)
                if data:
                    await websocket.send_text(
                        json.dumps({"type": "output", "data": data})
                    )
                else:
                    await asyncio.sleep(0.01)
            except Exception:
                break

    reader_task = asyncio.create_task(read_loop())

    # 接收前端输入并写入 PTY
    try:
        while True:
            msg = await websocket.receive_text()
            payload = json.loads(msg)

            if payload["type"] == "input":
                _write_pty(pty, backend, payload["data"])
            elif payload["type"] == "resize":
                cols = payload.get("cols", 80)
                rows = payload.get("rows", 24)
                _resize_pty(pty, backend, cols, rows)
            elif payload["type"] == "kill":
                break
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        # 清理 PTY
        try:
            if backend == "winpty":
                # winpty 没有 close，靠 GC
                del pty
            else:
                master_fd, pid = pty
                os.close(master_fd)
                try:
                    os.kill(pid, 9)
                except OSError:
                    pass
        except Exception:
            pass
