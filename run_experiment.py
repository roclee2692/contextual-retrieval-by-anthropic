#!/usr/bin/env python3
"""
统一实验运行脚本
根据命令行参数自动切换实验环境并运行对应测试
"""
import os
import sys
import shutil
from pathlib import Path

EXPERIMENTS = {
    "canteen": {
        "name": "食堂菜单实验 (Phase 1: Exp 1-3)",
        "env_file": ".env.canteen",
        "test_script": "scripts/test_ab_simple.py",
        "description": "Baseline RAG vs CR Enhanced vs Jieba+KG"
    },
    "flood": {
        "name": "防洪预案实验 (Phase 2: Exp 4-5)",
        "env_file": ".env.flood",
        "test_script": "scripts/run_flood_comparison.py",
        "description": "CR (Flood) vs Deep Knowledge Graph"
    }
}

def show_menu():
    print("\n" + "="*60)
    print("  🧪 多实验环境切换器")
    print("="*60)
    for key, exp in EXPERIMENTS.items():
        print(f"\n[{key}] {exp['name']}")
        print(f"    {exp['description']}")
    print("\n" + "="*60)

def switch_experiment(exp_key):
    """切换实验环境"""
    if exp_key not in EXPERIMENTS:
        print(f"❌ 错误: 未知的实验 '{exp_key}'")
        print(f"   可用选项: {', '.join(EXPERIMENTS.keys())}")
        return False
    
    exp = EXPERIMENTS[exp_key]
    env_source = Path(exp["env_file"])
    env_target = Path(".env")
    
    if not env_source.exists():
        print(f"❌ 配置文件不存在: {env_source}")
        return False
    
    # 备份当前 .env
    if env_target.exists():
        shutil.copy(env_target, ".env.backup")
    
    # 复制新配置
    shutil.copy(env_source, env_target)
    print(f"\n✅ 已切换到: {exp['name']}")
    print(f"   配置文件: {env_source} -> {env_target}")
    return True

def run_build():
    """运行数据库构建"""
    print("\n🔨 开始构建数据库...")
    os.system("python scripts/create_save_db.py")

def run_test(exp_key):
    """运行测试脚本"""
    exp = EXPERIMENTS[exp_key]
    print(f"\n🧪 运行测试: {exp['test_script']}")
    os.system(f"python {exp['test_script']}")

def main():
    if len(sys.argv) < 2:
        show_menu()
        print("\n使用方法:")
        print("  python run_experiment.py <experiment> [--build] [--test]")
        print("\n示例:")
        print("  python run_experiment.py canteen --build --test  # 构建+测试")
        print("  python run_experiment.py flood --test             # 仅测试")
        sys.exit(0)
    
    exp_key = sys.argv[1]
    
    # 切换环境
    if not switch_experiment(exp_key):
        sys.exit(1)
    
    # 执行操作
    if "--build" in sys.argv:
        run_build()
    
    if "--test" in sys.argv:
        run_test(exp_key)
    
    if "--build" not in sys.argv and "--test" not in sys.argv:
        print("\n💡 提示: 使用 --build 构建数据库, 使用 --test 运行测试")

if __name__ == "__main__":
    main()
