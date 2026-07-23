import time
import io
import threading
from flask import Flask, request, send_file, render_template_string, redirect
from werkzeug.serving import make_server

UPLOAD_PASSWORD = 'cool'
RATE_LIMIT = 5  # Max uploads per minute per IP

# Shared state
# files format: { 'filename': {'content': b'...', 'requests': {'ip_address': 'pending'|'approved'}} }
files = {}
# upload_history format: { 'ip_address': [timestamp1, timestamp2, ...] }
upload_history = {}

public_app = Flask('public')
admin_app = Flask('admin')

# ==========================================
# PUBLIC APP (Port 8000)
# ==========================================

PUBLIC_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Quick Share (Public)</title></head>
<body style="font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px;">
    <h2>Upload File</h2>
    <form action="/upload" method="post" enctype="multipart/form-data" style="margin-bottom: 30px;">
        <label>Upload Password:</label><br>
        <input type="password" name="password" required style="margin-bottom: 10px;"><br>
        <input type="file" name="file" required style="margin-bottom: 10px;"><br>
        <input type="submit" value="Upload" style="padding: 5px 15px;">
    </form>
    
    <hr>
    
    <h2>Available Files</h2>
    <ul style="list-style-type: none; padding: 0;">
        {% for filename, data in files.items() %}
            <li style="margin-bottom: 15px; padding: 15px; border: 1px solid #ccc; border-radius: 4px; background: #fafafa;">
                <strong style="font-size: 1.1em;">{{ filename }}</strong>
                <br><br>
                <form action="/download/{{ filename }}" method="get" style="display:inline;">
                    <input type="submit" value="Request / Download File" style="padding: 8px 15px; cursor: pointer;">
                </form>
                
                {% set ip_status = data['requests'].get(request.remote_addr) %}
                {% if ip_status == 'pending' %}
                    <span style="color: #ff9800; font-weight: bold; margin-left: 15px;">⏳ Request Pending Admin Approval...</span>
                {% elif ip_status == 'approved' %}
                    <span style="color: #4CAF50; font-weight: bold; margin-left: 15px;">✅ Approved! Click button to download.</span>
                {% endif %}
            </li>
        {% else %}
            <p>No files available.</p>
        {% endfor %}
    </ul>
</body>
</html>
'''

@public_app.route('/')
def index():
    return render_template_string(PUBLIC_HTML, files=files)

@public_app.route('/upload', methods=['POST'])
def upload():
    # IP-based Rate Limiting
    ip = request.remote_addr
    now = time.time()
    
    user_times = upload_history.get(ip, [])
    user_times = [t for t in user_times if now - t < 60]
    
    if len(user_times) >= RATE_LIMIT:
        upload_history[ip] = user_times
        return "Rate limit exceeded (max 5 uploads per minute). Try again later. <a href='/'>Go back</a>", 429
        
    user_times.append(now)
    upload_history[ip] = user_times

    password = request.form.get('password')
    if password != UPLOAD_PASSWORD:
        return "Unauthorized: Wrong upload password. <a href='/'>Go back</a>", 401
    
    file = request.files.get('file')
    if file and file.filename:
        # Save file content in RAM, initialize empty requests dict
        files[file.filename] = {
            'content': file.read(),
            'requests': {}
        }
        return f"File '{file.filename}' uploaded successfully! <a href='/'>Go back</a>"
    return "Bad Request: No file provided. <a href='/'>Go back</a>", 400

@public_app.route('/download/<filename>', methods=['GET'])
def download(filename):
    if filename not in files:
        return "File not found.", 404
        
    ip = request.remote_addr
    status = files[filename]['requests'].get(ip)
    
    if status == 'approved':
        return send_file(
            io.BytesIO(files[filename]['content']),
            as_attachment=True,
            download_name=filename
        )
    elif status == 'pending':
        return f"Your download request from IP {ip} is still pending approval by the admin. <a href='/'>Go back</a>"
    else:
        # Create a new download request
        files[filename]['requests'][ip] = 'pending'
        return f"Download requested for '{filename}'. Please wait for admin to approve your IP ({ip}). <a href='/'>Go back</a>"

# ==========================================
# ADMIN APP (Port 5000)
# ==========================================

ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard</title></head>
<body style="font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px;">
    <h2>Managerial Dashboard</h2>
    <p>Rate limits active: <strong>{{ upload_history|length }}</strong> IP(s) tracked in the last minute.</p>
    <hr>
    
    <h2>Uploaded Files & Requests (RAM)</h2>
    {% for filename, data in files.items() %}
        <div style="margin-bottom: 25px; padding: 15px; border: 2px solid #555; border-radius: 8px; background: #f9f9f9;">
            <h3 style="margin-top: 0;">{{ filename }} <span style="font-size: 14px; color: #666; font-weight: normal;">({{ data['content']|length }} bytes)</span></h3>
            
            <div style="margin-bottom: 15px;">
                <a href="/download/{{ filename }}" style="text-decoration: none;">
                    <button style="padding: 8px 15px; background-color: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">⬇️ Admin Direct Download</button>
                </a>
                <form action="/delete/{{ filename }}" method="post" style="display:inline; margin-left: 10px;">
                    <input type="submit" value="🗑️ Delete File from RAM" style="padding: 8px 15px; background-color: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">
                </form>
            </div>
            
            <h4 style="margin-bottom: 5px;">IP Download Requests:</h4>
            {% if data['requests'] %}
                <ul style="list-style-type: none; padding-left: 0;">
                {% for ip, status in data['requests'].items() %}
                    <li style="padding: 10px; border-bottom: 1px solid #ddd; background: {{ '#e8f5e9' if status == 'approved' else '#fff3e0' }};">
                        <strong>{{ ip }}</strong> - Status: 
                        <span style="color: {{ '#2e7d32' if status == 'approved' else '#e65100' }}; font-weight: bold;">
                            {{ status|upper }}
                        </span>
                        
                        <form action="/approve/{{ filename }}/{{ ip }}" method="post" style="display:inline; float: right;">
                            {% if status == 'approved' %}
                                <input type="submit" value="Revoke Approval" style="padding: 5px 10px; cursor: pointer;">
                            {% else %}
                                <input type="submit" value="Approve IP" style="padding: 5px 10px; background-color: #4CAF50; color: white; border: none; cursor: pointer;">
                            {% endif %}
                        </form>
                        <div style="clear: both;"></div>
                    </li>
                {% endfor %}
                </ul>
            {% else %}
                <p style="color: #888; font-style: italic;">No IP has requested this file yet.</p>
            {% endif %}
        </div>
    {% else %}
        <p>No files in memory.</p>
    {% endfor %}
</body>
</html>
'''

@admin_app.route('/')
def admin_index():
    return render_template_string(ADMIN_HTML, files=files, upload_history=upload_history)

@admin_app.route('/approve/<filename>/<ip>', methods=['POST'])
def approve_ip(filename, ip):
    if filename in files and ip in files[filename]['requests']:
        current_status = files[filename]['requests'][ip]
        # Toggle status
        files[filename]['requests'][ip] = 'pending' if current_status == 'approved' else 'approved'
    return redirect('/')

@admin_app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if filename in files:
        del files[filename]
    return redirect('/')

@admin_app.route('/download/<filename>')
def admin_download(filename):
    # Admins bypass ALL IP checks and passwords
    if filename in files:
        return send_file(
            io.BytesIO(files[filename]['content']),
            as_attachment=True,
            download_name=filename
        )
    return "Not Found", 404

# ==========================================
# THREADING & STARTUP
# ==========================================

class ServerThread(threading.Thread):
    def __init__(self, app, host, port):
        threading.Thread.__init__(self)
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

if __name__ == '__main__':
    public_thread = ServerThread(public_app, '0.0.0.0', 8000)
    admin_thread = ServerThread(admin_app, '127.0.0.1', 5000)
    
    print("Starting dual-port in-memory server...")
    print("=======================================")
    print(f"Public server running on http://0.0.0.0:8000 (Uploads & Download Requests)")
    print("Admin server running on  http://127.0.0.1:5000 (IP x File Approval Dashboard)")
    print("=======================================")
    print("Press Ctrl+C to shut down both servers.")
    
    public_thread.start()
    admin_thread.start()
    
    try:
        public_thread.join()
        admin_thread.join()
    except KeyboardInterrupt:
        print("Shutting down...")
        public_thread.server.shutdown()
        admin_thread.server.shutdown()
