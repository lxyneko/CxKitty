import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 请替换为更安全的密钥
socketio = SocketIO(app, cors_allowed_origins='*')

# 简单的用户名密码
USERNAME = 'admin'
PASSWORD = 'admin123'


# 支持多个实例管理，每个实例独立进程、输出缓存
RUNNABLE_SCRIPTS = {}
INSTANCE_OUTPUTS = {}  # {instance_key: [output_lines]}
INSTANCE_LOCKS = {}   # {instance_key: threading.Lock()}

def add_instance(instance_key, name=None):
    if instance_key not in RUNNABLE_SCRIPTS:
        RUNNABLE_SCRIPTS[instance_key] = {
            'name': name or instance_key,
            'status': 'stopped',
            'process': None,
            'log_path': f'logs/{instance_key}.log'
        }
        INSTANCE_OUTPUTS[instance_key] = []
        INSTANCE_LOCKS[instance_key] = threading.Lock()


import subprocess
import threading
PYTHON_PATH = r'C:/Users/lxyneko/Documents/Git/CxKitty/.venv/Scripts/python.exe'


def get_scripts():
    return RUNNABLE_SCRIPTS

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html', scripts=get_scripts())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# 启动脚本实例

@app.route('/start', methods=['POST'])
def start_script():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    script_key = request.form['script_key']
    scripts = get_scripts()
    if script_key in scripts and scripts[script_key]['status'] == 'stopped':
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path = scripts[script_key]['log_path']
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['CXKITTY_WEB'] = '1'
        proc = subprocess.Popen([PYTHON_PATH, 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, bufsize=1, universal_newlines=True, env=env)
        scripts[script_key]['process'] = proc
        scripts[script_key]['status'] = 'running'
        # 后台线程写日志和缓存输出
        def log_writer(p, log_path, instance_key):
            with open(log_path, 'w', encoding='utf-8') as f:
                for line in iter(p.stdout.readline, ''):
                    f.write(line)
                    f.flush()
                    with INSTANCE_LOCKS[instance_key]:
                        INSTANCE_OUTPUTS[instance_key].append(line)
        t = threading.Thread(target=log_writer, args=(proc, log_path, script_key), daemon=True)
        t.start()
        flash(f'脚本 {script_key} 已启动')
    return redirect(url_for('index'))

# 停止脚本实例

@app.route('/stop', methods=['POST'])
def stop_script():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    script_key = request.form['script_key']
    scripts = get_scripts()
    if script_key in scripts and scripts[script_key]['status'] == 'running':
        proc = scripts[script_key]['process']
        if proc:
            proc.terminate()
            scripts[script_key]['process'] = None
        scripts[script_key]['status'] = 'stopped'
        flash(f'脚本 {script_key} 已停止')
    return redirect(url_for('index'))

# 查看脚本终端输出
@app.route('/log/<script_key>')
def view_log(script_key):
    scripts = get_scripts()
    if script_key in scripts and 'log_path' in scripts[script_key]:
        log_path = scripts[script_key]['log_path']
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
        except Exception:
            log_content = '日志文件不存在或无法读取。'
    else:
        log_content = '未找到日志文件。'
    return render_template('log.html', script_key=script_key, log_content=log_content)

# 重命名脚本实例
@app.route('/rename', methods=['POST'])
def rename_script():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    script_key = request.form['script_key']
    new_name = request.form['new_name']
    scripts = get_scripts()
    if script_key in scripts:
        scripts[script_key]['name'] = new_name
        flash(f'脚本 {script_key} 已重命名为 {new_name}')
    return redirect(url_for('index'))



# 多实例终端相关
@app.route('/terminal/<instance_key>')
def terminal_page(instance_key):
    return render_template('terminal.html', instance_key=instance_key)

@socketio.on('input')
def handle_input(data):
    instance_key = data.get('instance_key')
    input_data = data.get('input')
    scripts = get_scripts()
    if instance_key in scripts:
        proc = scripts[instance_key]['process']
        if proc and proc.stdin:
            try:
                proc.stdin.write(input_data)
                proc.stdin.flush()
            except Exception:
                pass

@socketio.on('fetch_output')
def fetch_output(data):
    instance_key = data.get('instance_key')
    if instance_key in INSTANCE_OUTPUTS:
        with INSTANCE_LOCKS[instance_key]:
            out = ''.join(INSTANCE_OUTPUTS[instance_key])
            INSTANCE_OUTPUTS[instance_key].clear()
            emit('output', out)
# 添加实例接口
@app.route('/add_instance', methods=['POST'])
def add_instance_route():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    instance_key = request.form['instance_key']
    name = request.form.get('name', instance_key)
    add_instance(instance_key, name)
    flash(f'已添加实例 {instance_key}')
    return redirect(url_for('index'))


if __name__ == '__main__':
    socketio.run(app, debug=True)
