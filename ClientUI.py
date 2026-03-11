import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import json
import time

PIPE_NAME = r'\\.\pipe\NcsAvUpdaterPipe'

class UpdaterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AvScanVirus - Trung Tâm Cập Nhật")
        self.root.geometry("460x280") 
        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')
        self.q = queue.Queue()

        self.title_label = tk.Label(root, text="HỆ THỐNG CẬP NHẬT ANTIVIRUS", font=("Segoe UI", 14, "bold"), fg="#333333")
        self.title_label.pack(pady=(20, 10))

        self.status_label = tk.Label(root, text="Trạng thái: Đang chờ lệnh...", font=("Segoe UI", 10), fg="blue")
        self.status_label.pack(pady=5)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=380, mode="determinate")
        self.progress.pack(pady=10)

        self.detail_label = tk.Label(root, text="", font=("Segoe UI", 9), fg="gray")
        self.detail_label.pack(pady=0)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=(15, 10))

        self.update_btn = tk.Button(btn_frame, text="🚀 KIỂM TRA & CẬP NHẬT", font=("Segoe UI", 10, "bold"), 
                                    bg="#0078D7", fg="white", activebackground="#005A9E", activeforeground="white",
                                    relief="flat", cursor="hand2", command=lambda: self.start_action("update"), width=22, height=2)
        self.update_btn.grid(row=0, column=0, padx=5)

        self.rollback_btn = tk.Button(btn_frame, text="⏪ QUAY VỀ BẢN CŨ", font=("Segoe UI", 10, "bold"), 
                                    bg="#6c757d", fg="white", activebackground="#5a6268", activeforeground="white",
                                    relief="flat", cursor="hand2", command=lambda: self.start_action("rollback"), width=20, height=2)
        self.rollback_btn.grid(row=0, column=1, padx=5)

        # CỜ CHỐNG SPAM POPUP (Chỉ hiện 1 lần duy nhất mỗi lượt)
        self.popup_shown = False

        self.root.after(100, self.process_queue)

    def process_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                
                if msg['type'] == 'progress':
                    pct = msg['pct']
                    text = msg['text']
                    is_updating = msg['is_updating']

                    # LUÔN CẬP NHẬT THANH TIẾN ĐỘ VÀ CHỮ TRƯỚC
                    self.progress['value'] = pct
                    self.detail_label.config(text=text)
                    self.status_label.config(text=f"Đang xử lý... {int(pct)}%", fg="#0078D7")

                    # NẾU C++ ĐÃ BÁO XONG VIỆC VÀ CHƯA HIỆN POPUP NÀO
                    if not is_updating and not self.popup_shown:
                        self.popup_shown = True # Khóa mõm, cấm hiện thêm popup
                        self.reset_buttons()

                        if pct >= 100:
                            if "[RECOVERY]" in text:
                                self.status_label.config(text="Khôi phục phiên bản an toàn!", fg="#D83B01")
                                messagebox.showwarning("Tính năng Bảo vệ", "Phiên bản mới bị lỗi khởi động. Hệ thống đã kích hoạt màng lọc an toàn và quay về bản cũ!")
                            elif "[MANUAL_ROLLBACK]" in text:
                                self.status_label.config(text="Hạ cấp thành công!", fg="#D83B01")
                                messagebox.showinfo("Thông báo", "Đã khôi phục về phiên bản dự phòng trước đó thành công!")
                            else:
                                self.status_label.config(text="Hoàn tất thành công!", fg="#107C10") 
                                messagebox.showinfo("Thành công", text)
                        else:
                            text_lower = text.lower()
                            if "cu nhat" in text_lower or "khong the ha cap" in text_lower:
                                self.status_label.config(text="Đã ở phiên bản gốc!", fg="#6c757d") 
                                messagebox.showinfo("Thông báo", "Hệ thống đang ở phiên bản dự phòng cuối cùng. Không thể quay về cũ hơn được nữa!")
                            else:
                                self.status_label.config(text="Đã chặn thao tác lỗi!", fg="#D83B01")
                                messagebox.showwarning("Lỗi xử lý", f"Chi tiết: {text}")

                elif msg['type'] == 'error' and not self.popup_shown:
                    self.popup_shown = True
                    self.status_label.config(text="Lỗi hệ thống!", fg="red")
                    self.detail_label.config(text=msg['text'])
                    self.reset_buttons()
                    messagebox.showerror("Thông báo", msg['text'])
                
                elif msg['type'] == 'uptodate' and not self.popup_shown:
                    self.popup_shown = True
                    self.progress['value'] = 100
                    self.status_label.config(text="Hệ thống đang ở phiên bản mới nhất!", fg="#107C10")
                    self.detail_label.config(text="Không cần cập nhật thêm.")
                    self.reset_buttons()
                    messagebox.showinfo("Thông báo", "Antivirus của bạn đã được cập nhật đầy đủ!")

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def reset_buttons(self):
        self.update_btn.config(state=tk.NORMAL, bg="#0078D7", text="🚀 KIỂM TRA LẠI")
        self.rollback_btn.config(state=tk.NORMAL, bg="#6c757d")

    def start_action(self, action_type):
        self.update_btn.config(state=tk.DISABLED, bg="gray")
        self.rollback_btn.config(state=tk.DISABLED, bg="gray")
        self.status_label.config(text="Đang kết nối đến Core Engine...", fg="black")
        self.progress['value'] = 0
        self.detail_label.config(text="")
        
        # Reset lại cờ chống Spam khi bắt đầu lượt bấm nút mới
        self.popup_shown = False 
        threading.Thread(target=self.update_worker, args=(action_type,), daemon=True).start()

    def update_worker(self, action_type):
        try:
            with open(PIPE_NAME, 'r+b', buffering=0) as pipe:
                pipe.write(f"{action_type}\n".encode('utf-8')) 
                response = pipe.read(1024).decode('utf-8').strip()

            if response in ["OK_STARTING", "ERR_ALREADY_UPDATING"]:
                is_self_updating = False
                
                pipe = None
                for i in range(15):
                    try:
                        time.sleep(0.5)
                        pipe = open(PIPE_NAME, 'r+b', buffering=0)
                        break 
                    except FileNotFoundError:
                        continue 
                
                if pipe is None:
                    self.q.put({'type': 'error', 'text': "C++ quá tải, không thể kết nối lại ống nước IPC!"})
                    return

                try:
                    pipe.write(b"stream\n")
                    while True:
                        line = pipe.readline()
                        if not line: break
                        
                        try:
                            data = json.loads(line.decode('utf-8').strip())
                            pct = data.get('progress', 0)
                            msg_text = data.get('message', '')
                            
                            self.q.put({
                                'type': 'progress',
                                'pct': pct,
                                'text': msg_text,
                                'is_updating': data.get('is_updating', False)
                            })
                            
                            # ===============================================================
                            # CHỖ NÀY LÀ CÁI ĐÃ HÀNH HẠ BÁC NÃY GIỜ ĐÂY! CHỈ LỘT XÁC KHI CÓ CHỮ!
                            # ===============================================================
                            if pct >= 99.0 and "lot xac" in msg_text.lower():
                                is_self_updating = True
                                break 
                            
                            if not data.get('is_updating', False):
                                break
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    if not is_self_updating:
                        raise e 
                finally:
                    pipe.close()

                # Tái kết nối chỉ dành cho Update bản thân (C++ báo lột xác)
                if is_self_updating:
                    self.q.put({
                        'type': 'progress',
                        'pct': 99.0,
                        'text': "Đang khởi động lại hệ thống (Chuyển Slot)...",
                        'is_updating': True
                    })
                    time.sleep(3) 
                    
                    reconnected = False
                    for i in range(15):
                        try:
                            with open(PIPE_NAME, 'r+b', buffering=0) as new_pipe:
                                reconnected = True
                                new_pipe.write(b"stream\n")
                                first_line = new_pipe.readline()
                                
                                if first_line:
                                    try:
                                        data = json.loads(first_line.decode('utf-8').strip())
                                        self.q.put({
                                            'type': 'progress',
                                            'pct': data.get('progress', 100.0),
                                            'text': data.get('message', 'Đã kết nối lại thành công.'),
                                            'is_updating': False
                                        })
                                    except json.JSONDecodeError:
                                        pass
                                break
                        except FileNotFoundError:
                            self.q.put({
                                'type': 'progress',
                                'pct': 99.0,
                                'text': f"Đang chờ phiên bản mới thức dậy... ({i+1}/15)",
                                'is_updating': True
                            })
                            time.sleep(1) 
                    
                    if not reconnected:
                        self.q.put({
                            'type': 'error', 
                            'text': "Phiên bản mới bị lỗi khởi động! AppLauncher đã tự động Rollback về bản cũ."
                        })

            elif response == "NO_UPDATE_NEEDED":
                self.q.put({'type': 'uptodate'})
            else:
                self.q.put({'type': 'error', 'text': f"Core Engine từ chối: {response}"})

        except FileNotFoundError:
            self.q.put({'type': 'error', 'text': "Không tìm thấy Service C++. Bạn đã bật máy chủ chưa?"})
        except Exception as e:
            self.q.put({'type': 'error', 'text': f"Lỗi Pipe: {str(e)}"})

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    app = UpdaterGUI(root)
    root.mainloop()