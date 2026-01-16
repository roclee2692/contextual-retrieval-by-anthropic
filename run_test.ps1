# 龙子湖食堂 RAG 测试启动脚本
# 注意：确保 test_ab_simple.py 使用 BAAI/bge-base-en-v1.5 模型（与数据库一致）

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 78) -ForegroundColor Cyan
Write-Host "  龙子湖食堂 RAG 系统 - 快速测试" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 78) -ForegroundColor Cyan

# 切换到项目目录
Set-Location -Path "D:\DpanPython\python-projects\contextual-retrieval-by-anthropic"

Write-Host "`n[1/3] 检查数据库状态..." -ForegroundColor Green
if (Test-Path ".\src\db\canteen_db_vectordb") {
    Write-Host "  ✓ 向量数据库已存在" -ForegroundColor Green
} else {
    Write-Host "  ✗ 向量数据库不存在，请先运行: python create_save_db.py" -ForegroundColor Red
    exit 1
}

if (Test-Path ".\src\db\canteen_db_bm25") {
    Write-Host "  ✓ BM25 数据库已存在" -ForegroundColor Green
} else {
    Write-Host "  ✗ BM25 数据库不存在，请先运行: python create_save_db.py" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/3] 选择测试模式:" -ForegroundColor Green
Write-Host "  [1] 快速测试 (3个问题)" -ForegroundColor Cyan
Write-Host "  [2] 标准测试 (5个问题)" -ForegroundColor Cyan
Write-Host "  [3] 完整测试 (20个问题)" -ForegroundColor Cyan
Write-Host "  [4] 启动 API 服务" -ForegroundColor Cyan
Write-Host "  [5] 测试 Ollama 连接" -ForegroundColor Cyan

$choice = Read-Host "`n请选择 (1-5)"

switch ($choice) {
    "1" {
        Write-Host "`n[3/3] 运行快速测试 (3个问题)..." -ForegroundColor Green
        python test_ab_simple.py 3
    }
    "2" {
        Write-Host "`n[3/3] 运行标准测试 (5个问题)..." -ForegroundColor Green
        python test_ab_simple.py 5
    }
    "3" {
        Write-Host "`n[3/3] 运行完整测试 (20个问题)..." -ForegroundColor Green
        python test_ab_simple.py
    }
    "4" {
        Write-Host "`n[3/3] 启动 FastAPI 服务..." -ForegroundColor Green
        Write-Host "  API 地址: http://127.0.0.1:8000" -ForegroundColor Yellow
        Write-Host "  按 Ctrl+C 停止服务`n" -ForegroundColor Yellow
        python app.py
    }
    "5" {
        Write-Host "`n[3/3] 测试 Ollama 连接..." -ForegroundColor Green
        python test_ollama_connection.py
    }
    default {
        Write-Host "`n✗ 无效选择" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 78) -ForegroundColor Cyan
Write-Host "  完成！" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 78) -ForegroundColor Cyan

