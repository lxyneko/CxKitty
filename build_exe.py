#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CxKitty 打包脚本
使用 PyInstaller 将项目打包成 exe 文件
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def install_pyinstaller():
    """安装 PyInstaller"""
    print("正在安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def create_spec_file():
    """创建 PyInstaller spec 文件"""
    try:
        import ddddocr
        import os
        ddddocr_path = os.path.dirname(ddddocr.__file__)
    except ImportError:
        print("错误: 未找到 ddddocr 库，请先执行 'pip install ddddocr'")
        sys.exit(1)

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yml', '.'),
        ('imgs', 'imgs'),
        ('session', 'session'),
        ('export', 'export'),
        ('logs', 'logs'),
        (r'{ddddocr_path}', 'ddddocr')
    ],
    hiddenimports=[
        'rich.console',
        'rich.layout',
        'rich.live',
        'rich.panel',
        'rich.prompt',
        'rich.traceback',
        'rich.align',
        'cv2',
        'numpy',
        'ddddocr',
        'lxml',
        'yaml',
        'jsonpath',
        'bs4',
        'dataclasses_json',
        'yarl',
        'qrcode',
        'pycryptodome',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CxKitty',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='imgs/demo1.png' if os.path.exists('imgs/demo1.png') else None,
)
"""
    
    with open('CxKitty.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("已创建 CxKitty.spec 文件")

def build_exe():
    """构建 exe 文件"""
    print("开始构建 exe 文件...")
    
    # 确保必要的目录存在
    for dir_name in ['session', 'export', 'logs']:
        Path(dir_name).mkdir(exist_ok=True)
    
    # 使用 spec 文件构建
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", 
        "--clean",  # 清理临时文件
        "CxKitty.spec"
    ])
    
    print("构建完成！")
    print("exe 文件位置: dist/CxKitty.exe")

def main():
    """主函数"""
    print("=== CxKitty 打包工具 ===")
    
    try:
        # 检查是否已安装 PyInstaller
        try:
            import PyInstaller
            print("PyInstaller 已安装")
        except ImportError:
            install_pyinstaller()
        
        # 创建 spec 文件
        create_spec_file()
        
        # 构建 exe
        build_exe()
        
        print("\n=== 打包成功！ ===")
        print("可执行文件位置: dist/CxKitty.exe")
        print("请将整个 dist 目录分发给用户")
        
    except Exception as e:
        print(f"Error occurred during build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 