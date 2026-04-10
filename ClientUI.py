from flask import Flask, render_template_string, jsonify, request
import threading
import json
import time
import os

app = Flask(__name__)

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN
# ==========================================
PIPE_NAME = r'\\.\pipe\NcsAvUpdaterPipe'
TARGET_DIR = r'D:\ProjectTraining\AvScanVirus'

# ==========================================
# BIẾN TOÀN CỤC LƯU TRẠNG THÁI UPDATE
# ==========================================
update_state = {
    "pct": 0,
    "text": "Đang chờ lệnh...",
    "status_color": "blue",
    "is_updating": False,
    "popup": None,  
    "buttons_disabled": False
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AvScanVirus - Trung Tâm Cập Nhật</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; display: flex; justify-content: center; gap: 20px;}
        .panel { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .control-panel { width: 450px; }
        .tree-panel { width: 400px; display: flex; flex-direction: column;}
        
        h2 { color: #333; margin-top: 0; text-align: center; font-size: 22px;}
        h3 { color: #555; border-bottom: 2px solid #eee; padding-bottom: 5px; margin-top: 0; display: flex; justify-content: space-between; align-items: center;}
        
        /* Progress Bar */
        .status-text { font-weight: bold; margin-bottom: 10px; display: block; }
        .progress-container { width: 100%; background-color: #e0e0e0; border-radius: 5px; margin-bottom: 5px; height: 20px; overflow: hidden;}
        .progress-bar { height: 100%; background-color: #0078D7; width: 0%; transition: width 0.3s ease; }
        .detail-text { font-size: 13px; color: gray; display: block; margin-bottom: 20px; min-height: 20px;}
        
        /* Buttons */
        .btn-row { display: flex; gap: 10px; }
        button { flex: 1; padding: 12px; font-size: 14px; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; color: white; transition: 0.3s; }
        button:disabled { background-color: #ccc !important; cursor: not-allowed; }
        .btn-update { background-color: #0078D7; }
        .btn-update:hover:not(:disabled) { background-color: #005A9E; }
        .btn-rollback { background-color: #6c757d; }
        .btn-rollback:hover:not(:disabled) { background-color: #5a6268; }
        
        /* Tree Panel */
        .btn-refresh { background-color: #28a745; padding: 5px 10px; font-size: 12px; flex: none; width: auto;}
        .tree-box { flex-grow: 1; overflow-y: auto; background: #fafafa; border: 1px solid #ddd; padding: 10px; border-radius: 5px; max-height: 400px;}
        ul.tree { list-style: none; padding-left: 20px; margin: 0; font-size: 14px;}
        ul.tree-root { padding-left: 0; }
        ul.tree li { margin: 2px 0; } 
        
        summary { cursor: pointer; font-weight: bold; padding: 5px; border-radius: 4px; display: block; user-select: none;}
        summary:hover { background: #e9ecef; }
        
        /* Chỉnh CSS cho file bấm được */
        .file-item { padding: 5px; color: #333; display: inline-block; width: 90%; border-radius: 3px;} 
        .file-clickable { cursor: pointer; }
        .file-clickable:hover { background-color: #e3f2fd; color: #0078D7; font-weight: bold;}
        
        /* CSS CHO MODAL XEM FILE XỊN XÒ */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); justify-content: center; align-items: center; z-index: 1000; }
        .modal-content { background: white; padding: 20px; border-radius: 8px; width: 600px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 5px 25px rgba(0,0,0,0.3);}
        .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 10px; }
        .modal-title { font-weight: bold; font-size: 16px; color: #333; }
        .close-btn { background: #dc3545; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; flex: none;}
        .close-btn:hover { background: #c82333; }
        .file-viewer { flex-grow: 1; overflow-y: auto; background: #1e1e1e; color: #d4d4d4; padding: 15px; font-family: Consolas, monospace; font-size: 14px; white-space: pre-wrap; border-radius: 4px; }
    </style>
</head>
<body>

    <div class="panel control-panel">
        <h2>🛡️ HỆ THỐNG CẬP NHẬT ANTIVIRUS</h2>
        
        <span id="statusLabel" class="status-text" style="color: blue;">Trạng thái: Đang chờ lệnh...</span>
        
        <div class="progress-container">
            <div id="progressBar" class="progress-bar"></div>
        </div>
        <span id="detailLabel" class="detail-text"></span>
        
        <div class="btn-row">
            <button id="btnUpdate" class="btn-update" onclick="startAction('update')">🚀 KIỂM TRA & CẬP NHẬT</button>
            <button id="btnRollback" class="btn-rollback" onclick="startAction('rollback')">⏪ QUAY VỀ BẢN CŨ</button>
        </div>
    </div>

    <div class="panel tree-panel">
        <h3>
            <span>📂 Kết quả thư mục</span>
            <button class="btn-refresh" onclick="loadTree()">🔄 Làm mới</button>
        </h3>
        
        <div class="tree-box" id="treeContainer">
            Đang tải cấu trúc thư mục...
        </div>
    </div>

    <div class="modal-overlay" id="fileModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title" id="modalTitle">Đang xem file...</span>
                <button class="close-btn" onclick="closeModal()">Đóng</button>
            </div>
            <div class="file-viewer" id="fileContent">Nội dung file sẽ hiện ở đây...</div>
        </div>
    </div>

    <script>
        window.onload = function() {
            loadTree();
            setInterval(pollStatus, 500); 
        };

        function startAction(action) {
            document.getElementById('btnUpdate').disabled = true;
            document.getElementById('btnRollback').disabled = true;
            
            fetch('/api/start?action=' + action + '&t=' + Date.now(), { cache: 'no-store' })
                .then(res => res.json())
                .then(data => {
                    if(data.status !== 'success') {
                        alert("Lỗi: " + data.message);
                    }
                });
        }

        function pollStatus() {
            fetch('/api/status?t=' + Date.now(), { cache: 'no-store' })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('progressBar').style.width = data.pct + '%';
                    document.getElementById('detailLabel').innerText = data.text;
                    
                    const statusLbl = document.getElementById('statusLabel');
                    statusLbl.innerText = "Trạng thái: " + (data.is_updating ? `Đang xử lý... ${Math.round(data.pct)}%` : data.text);
                    statusLbl.style.color = data.status_color;

                    document.getElementById('btnUpdate').disabled = data.buttons_disabled;
                    document.getElementById('btnRollback').disabled = data.buttons_disabled;

                    if(data.popup) {
                        alert(`[${data.popup.title}]\\n${data.popup.msg}`);
                        fetch('/api/clear_popup?t=' + Date.now(), { cache: 'no-store' }); 
                        loadTree(); 
                    }
                });
        }

        function loadTree() {
            fetch('/api/tree?t=' + Date.now(), { cache: 'no-store' })
                .then(res => res.text())
                .then(html => {
                    document.getElementById('treeContainer').innerHTML = html;
                });
        }

        function viewFile(filePath) {
            document.getElementById('fileModal').style.display = 'flex';
            document.getElementById('modalTitle').innerText = '📄 ' + filePath.split('/').pop();
            document.getElementById('fileContent').innerText = 'Đang tải nội dung file...';

            fetch('/api/read_file?path=' + encodeURIComponent(filePath) + '&t=' + Date.now(), { cache: 'no-store' })
                .then(res => res.json())
                .then(data => {
                    if(data.status === 'success') {
                        document.getElementById('fileContent').innerText = data.content;
                    } else {
                        document.getElementById('fileContent').innerText = 'Lỗi: ' + data.message;
                    }
                })
                .catch(err => {
                    document.getElementById('fileContent').innerText = 'Lỗi kết nối tới Server!';
                });
        }

        function closeModal() {
            document.getElementById('fileModal').style.display = 'none';
        }
    </script>
</body>
</html>
"""

def update_worker(action_type):
    global update_state
    update_state["pct"] = 0
    update_state["text"] = "Đang kết nối đến Core Engine..."
    update_state["status_color"] = "black"
    update_state["is_updating"] = True
    update_state["buttons_disabled"] = True
    update_state["popup"] = None

    is_self_updating = False

    try:
        with open(PIPE_NAME, 'r+b', buffering=0) as pipe:
            pipe.write(f"{action_type}\n".encode('utf-8')) 
            response = pipe.read(1024).decode('utf-8').strip()

        if response in ["OK_STARTING", "ERR_ALREADY_UPDATING"]:
            pipe = None
            for i in range(15):
                try:
                    time.sleep(0.5)
                    pipe = open(PIPE_NAME, 'r+b', buffering=0)
                    break 
                except FileNotFoundError:
                    continue 
            
            if pipe is None:
                trigger_error("C++ quá tải, không thể kết nối lại ống nước IPC!")
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
                        
                        update_state["pct"] = pct
                        update_state["text"] = msg_text
                        update_state["status_color"] = "#0078D7"
                        
                        if pct >= 99.0 and "lot xac" in msg_text.lower():
                            is_self_updating = True
                            break 
                        
                        if not data.get('is_updating', False):
                            handle_finish_logic(pct, msg_text)
                            break
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                if not is_self_updating:
                    raise e 
            finally:
                pipe.close()

            # ==============================================================
            # BẢN VÁ: CLIENT KHÔN HƠN! TỰ ĐỘNG CHỐT ĐƠN KHI NỐI ĐƯỢC ỐNG NƯỚC
            # ==============================================================
            if is_self_updating:
                update_state["pct"] = 99.0
                update_state["text"] = "Đang khởi động lại hệ thống (Chuyển Slot)..."
                time.sleep(3) 
                
                reconnected = False
                for i in range(15):
                    try:
                        # Chỉ cần cắm được ống nước vào là chứng tỏ con EXE mới đã sống!
                        with open(PIPE_NAME, 'r+b', buffering=0) as new_pipe:
                            reconnected = True
                            # Ép thành công luôn 100%, không thèm quan tâm thằng C++ nói gì!
                            handle_finish_logic(100.0, "Đã cập nhật (lột xác) và kết nối lại thành công!")
                            break
                    except FileNotFoundError:
                        update_state["text"] = f"Đang chờ phiên bản mới thức dậy... ({i+1}/15)"
                        time.sleep(1) 
                
                if not reconnected:
                    trigger_error("Phiên bản mới bị lỗi khởi động! AppLauncher đã tự động Rollback về bản cũ.")

        elif response == "NO_UPDATE_NEEDED":
            update_state["pct"] = 100
            update_state["text"] = "Không cần cập nhật thêm."
            update_state["status_color"] = "#107C10"
            update_state["is_updating"] = False
            update_state["buttons_disabled"] = False
            update_state["popup"] = {"title": "Thông báo", "msg": "Hệ thống đang ở phiên bản mới nhất!", "type": "success"}
        else:
            trigger_error(f"Core Engine từ chối: {response}")

    except FileNotFoundError:
        trigger_error("Không tìm thấy Service C++. Bạn đã bật AppLauncher chưa?")
    except Exception as e:
        trigger_error(f"Lỗi Pipe: {str(e)}")

def handle_finish_logic(pct, text):
    global update_state
    update_state["pct"] = pct
    update_state["text"] = text
    update_state["is_updating"] = False
    update_state["buttons_disabled"] = False

    if pct >= 100:
        if "[RECOVERY]" in text:
            update_state["status_color"] = "#D83B01"
            update_state["popup"] = {"title": "Tính năng Bảo vệ", "msg": "Phiên bản mới bị lỗi khởi động. Hệ thống đã quay về bản cũ!", "type": "warning"}
        elif "[MANUAL_ROLLBACK]" in text:
            update_state["status_color"] = "#D83B01"
            update_state["popup"] = {"title": "Hạ cấp thành công", "msg": "Đã khôi phục về phiên bản dự phòng thành công!", "type": "success"}
        else:
            update_state["status_color"] = "#107C10"
            update_state["popup"] = {"title": "Thành công", "msg": text, "type": "success"}
    else:
        text_lower = text.lower()
        if "cu nhat" in text_lower or "khong the ha cap" in text_lower:
            update_state["status_color"] = "#6c757d"
            update_state["popup"] = {"title": "Thông báo", "msg": "Hệ thống đang ở phiên bản dự phòng cuối cùng!", "type": "info"}
        else:
            update_state["status_color"] = "#D83B01"
            update_state["popup"] = {"title": "Lỗi xử lý", "msg": f"Chi tiết: {text}", "type": "warning"}

def trigger_error(msg):
    global update_state
    update_state["pct"] = 0
    update_state["text"] = msg
    update_state["status_color"] = "red"
    update_state["is_updating"] = False
    update_state["buttons_disabled"] = False
    update_state["popup"] = {"title": "Lỗi hệ thống", "msg": msg, "type": "error"}

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/start')
def start_action():
    action = request.args.get('action', 'update')
    threading.Thread(target=update_worker, args=(action,), daemon=True).start()
    return jsonify({"status": "success"})

@app.route('/api/status')
def get_status():
    return jsonify(update_state)

@app.route('/api/clear_popup')
def clear_popup():
    update_state["popup"] = None
    return jsonify({"status": "success"})

@app.route('/api/tree')
def get_tree():
    def build_tree_html(current_dir, is_root=False):
        if not os.path.exists(current_dir):
            return "<span style='color:red'>Không tìm thấy thư mục: " + current_dir + "</span>"
            
        html = '<ul class="tree tree-root">' if is_root else '<ul class="tree">'
        try:
            items = sorted(os.listdir(current_dir), key=lambda x: (not os.path.isdir(os.path.join(current_dir, x)), x.lower()))
        except Exception:
            return "</ul>"
            
        for item in items:
            full_path = os.path.join(current_dir, item)
            rel_path = os.path.relpath(full_path, TARGET_DIR).replace('\\', '/')
            
            if os.path.isdir(full_path):
                html += f'<li><details><summary>📁 {item}</summary>{build_tree_html(full_path)}</details></li>'
            else:
                if item.endswith(('.exe', '.dll', '.dat', '.pdb')):
                    html += f'<li><div class="file-item">📄 {item} <span style="color:#aaa;font-size:11px;float:right">(Binary)</span></div></li>'
                else:
                    html += f'<li><div class="file-item file-clickable" onclick="viewFile(\'{rel_path}\')">📄 {item}</div></li>'
        html += '</ul>'
        return html

    return build_tree_html(TARGET_DIR, is_root=True)

@app.route('/api/read_file')
def read_file():
    rel_path = request.args.get('path', '')
    if not rel_path:
        return jsonify({"status": "error", "message": "Không có đường dẫn."})
    
    target_file = os.path.abspath(os.path.join(TARGET_DIR, rel_path))
    
    if not target_file.startswith(TARGET_DIR) or not os.path.isfile(target_file):
        return jsonify({"status": "error", "message": "File không hợp lệ hoặc không tồn tại."})
        
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"status": "success", "content": content})
    except UnicodeDecodeError:
        return jsonify({"status": "error", "message": "Đây là file nhị phân (.exe, .dll,...) hoặc file mã hóa. Không thể xem dưới dạng văn bản!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    print("🚀 Web Client đang chạy! Gửi IP:5001 cho sếp kiểm tra update nhé!")
    app.run(host='0.0.0.0', port=5001, debug=True)