import socket


def debug_socket_6221(host, port=5025):
    print(f"--- 開始偵錯連線: {host}:{port} ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)

        print("正在嘗試 Connect...")
        s.connect((host, port))
        print("Connect 成功！")

        cmd = "*IDN?\n"
        print(f"發送指令: {repr(cmd)}")
        s.sendall(cmd.encode("utf-8"))

        print("等待儀器回傳...")
        response = b""
        while True:
            try:
                chunk = s.recv(1024)
                if not chunk:
                    break
                response += chunk
                if b"\n" in chunk:
                    break
            except socket.timeout:
                print("讀取逾時：儀器沒有在規定時間內回傳資料。")
                break

        if response:
            print(f"接收到原始資料: {repr(response)}")
            print(f"解碼後的字串: {response.decode('utf-8').strip()}")
        else:
            print("警告：連線成功但未收到任何回傳。")

    except Exception as e:
        print(f"連線過程中發生錯誤: {type(e).__name__}: {e}")
    finally:
        s.close()
        print("--- 偵錯結束 ---")


if __name__ == "__main__":
    debug_socket_6221("192.168.0.10")  # 請替換為你的 IP
