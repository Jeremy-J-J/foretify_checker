import os 
import requests
import time 
import subprocess
import signal
import json
from threading import Timer
from get_error import get_error

osc_path = '/home/user01/Desktop/zjutest/CQU_osc/generated_scenarios_v2'




class ForetifyRunner:
    def __init__(self, port=33917):
        self.port = port
        self.process = None
        self.timeout_seconds = 300  # 30秒超时
    
    def start_foretify(self, osc_file):
        """启动 foretify 进程"""
        # 先停止任何正在运行的进程
        self.stop_foretify()
        
        # 构建命令
        cmd = f'foretify --enable_status_server --status_server_port {self.port} --load {osc_file}'
        print(f"启动命令: {cmd}")
        
        # 启动进程（后台运行）
        self.process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # 创建新的进程组
        )
        
        # 设置超时定时器
        timer = Timer(self.timeout_seconds, self.stop_foretify)
        timer.start()
        
        # 等待进程启动
        time.sleep(3)
        return self.process
    
    def stop_foretify(self):
        """停止 foretify 进程"""
        if self.process and self.process.poll() is None:
            print("停止之前的 foretify 进程...")
            # 终止整个进程组
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait(timeout=5)
            self.process = None
    
    def check_status(self, max_retries=300):
        """检查状态，等待加载完成"""
        url = f'http://localhost:{self.port}/status'
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"状态检查 {attempt+1}/{max_retries}: {data.get('status')}")
                        
                        if data.get('status') == 'LOAD_SUCCEED':
                            return data
                        elif data.get('status') == 'LOAD_FAILED':
                            print(f"加载失败: {data}")
                            return None
                    except json.JSONDecodeError:
                        print(f"响应不是有效的JSON: {response.text}")
            except requests.exceptions.ConnectionError:
                print(f"连接尝试 {attempt+1}/{max_retries}: 服务未就绪")
            except requests.exceptions.RequestException as e:
                print(f"请求错误: {e}")
            
            time.sleep(1)
        
        print(f"在 {max_retries} 次尝试后未能获取状态")
        return None
    
    def run_file(self, osc_file):
        """运行单个OSC文件"""
        print(f"\n{'='*60}")
        print(f"处理文件: {osc_file}")
        print(f"{'='*60}")
        
        # 启动 foretify
        process = self.start_foretify(osc_file)
        if not process:
            print("启动 foretify 失败")
            return None
        
        # 检查状态
        status = self.check_status()
        
        # 如果进程还在运行，停止它
        if process and process.poll() is None:
            # 读取输出
            try:
                stdout, stderr = process.communicate(timeout=2)
                if stdout:
                    print(f"标准输出: {stdout.decode()[:500]}...")  # 只打印前500字符
                if stderr:
                    print(f"标准错误: {stderr.decode()[:500]}...")
            except subprocess.TimeoutExpired:
                self.stop_foretify()
        
        return status

def check_port_available(port=33917):
    """检查端口是否可用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except socket.error:
        print(f"端口 {port} 被占用")
        return False

def kill_process_on_port(port=33917):
    """杀死占用端口的进程"""
    try:
        # Linux/Mac
        cmd = f"lsof -ti:{port} | xargs kill -9 2>/dev/null"
        os.system(cmd)
        print(f"已清理端口 {port} 上的进程")
    except:
        pass


def main_folder():
    # 创建 runner 实例
    runner = ForetifyRunner(port=33917)
    
    # 确保开始时端口是空闲的
    kill_process_on_port(33917)
    
    success_count = 0
    total_count = 0
    # 遍历目录
    for dir_name in os.listdir(osc_path):
        dir_path = os.path.join(osc_path, dir_name)
        if os.path.isdir(dir_path):
            print(f"\n进入目录: {dir_name}")
            
            for file in os.listdir(dir_path):
                if file.endswith('.osc'):
                    file_path = os.path.join(dir_path, file)
                    total_count += 1
                    # 检查端口是否可用
                    if not check_port_available(33917):
                        kill_process_on_port(33917)
                        time.sleep(1)
                    
                    # 运行文件
                    status = runner.run_file(file_path)
                    
                    if status:
                        print(f"✅ 文件 {file} 处理成功")
                        print(f"   状态: {status}")
                        success_count += 1
                    else:
                        print(f"❌ 文件 {file} 处理失败")

                    
                    # 在处理下一个文件前暂停一下
                    time.sleep(2)
    
    print("\n所有文件处理完成！")
    print(f"成功处理 {success_count}/{total_count} 个文件")

def main_jsonl():
    runner = ForetifyRunner(port=33917)
    
    # 确保开始时端口是空闲的
    kill_process_on_port(33917)
    
    success_count = 0
    total_count = 0
    jsonl_path = "/home/user01/Desktop/zjutest/generated_data/converted_genoscs.jsonl"
    index = 0
    for line in open(jsonl_path, 'r'):
        data = json.loads(line)
        contents = data['messages'][2]['content']
        # remove the ````osc` and ` ````
        contents = contents.replace('```osc\n', '').replace('\n```', '').strip()  # 提取文件路径并去除多余的标记
        temp_file_path = f"/tmp/test_osc/temp_{index}.osc"
        with open(temp_file_path, 'w') as f:
            f.write(contents)
        total_count += 1
        # 检查端口是否可用
        if not check_port_available(33917):
            kill_process_on_port(33917)
            time.sleep(1)
        
        # 运行文件
        status = runner.run_file(temp_file_path)
        
        if status:
            print(f"✅ 文件 {temp_file_path} 处理成功")
            print(f"   状态: {status}")
            success_count += 1
        else:
            print(f"❌ 文件 {temp_file_path} 处理失败")
        
        # 在处理下一个文件前暂停一下
        time.sleep(2)
        index += 1
    
    print("\n所有文件处理完成！")
    print(f"成功处理 {success_count}/{total_count} 个文件")


if __name__ == "__main__":
    main_folder()