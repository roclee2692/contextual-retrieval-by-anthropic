# 龙子湖食堂 RAG 系统 - 快速启动脚本

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "龙子湖食堂 RAG 系统 - 环境检查" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

# 1. 检查 WSL Ollama 连接
Write-Host "`n[1/5] 检查 WSL Ollama 服务..." -ForegroundColor Yellow

$ollamaUrl = "http://localhost:11434/api/tags"
try {
    $response = Invoke-WebRequest -Uri $ollamaUrl -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ Ollama 服务正常运行" -ForegroundColor Green

    # 检查是否有 gemma2:12b 模型
    $models = ($response.Content | ConvertFrom-Json).models
    $hasGemma = $models | Where-Object { $_.name -like "*gemma2*12b*" }

    if ($hasGemma) {
        Write-Host "✓ 检测到 gemma2:12b 模型" -ForegroundColor Green
    } else {
        Write-Host "⚠ 未检测到 gemma2:12b 模型" -ForegroundColor Yellow
        Write-Host "  可用模型: $($models.name -join ', ')" -ForegroundColor Gray
        Write-Host "  请在 WSL 中运行: ollama pull gemma2:12b" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ 无法连接到 Ollama 服务" -ForegroundColor Red
    Write-Host "  请在 WSL 中启动: ollama serve" -ForegroundColor Red
    Write-Host "`n按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# 2. 检查 Python 环境
Write-Host "`n[2/5] 检查 Python 环境..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python 已安装: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python 未安装或不在 PATH 中" -ForegroundColor Red
    Write-Host "`n按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# 3. 检查依赖
Write-Host "`n[3/5] 检查 Python 依赖..." -ForegroundColor Yellow

$requiredPackages = @(
    "llama-index-core",
    "llama-index-llms-ollama",
    "fastapi",
    "streamlit",
    "chromadb"
)

$missingPackages = @()
foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -eq 0) {
    Write-Host "✓ 所有依赖已安装" -ForegroundColor Green
} else {
    Write-Host "⚠ 缺少以下依赖: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "  正在安装..." -ForegroundColor Yellow
    pip install -r requirements.txt -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "✗ 依赖安装失败" -ForegroundColor Red
    }
}

# 4. 检查 .env 配置
Write-Host "`n[4/5] 检查 .env 配置..." -ForegroundColor Yellow

if (Test-Path ".env") {
    Write-Host "✓ .env 文件存在" -ForegroundColor Green

    $envContent = Get-Content ".env"
    $hasOllamaUrl = $envContent | Select-String "OLLAMA_BASE_URL"

    if ($hasOllamaUrl) {
        Write-Host "✓ OLLAMA_BASE_URL 已配置" -ForegroundColor Green
    } else {
        Write-Host "⚠ OLLAMA_BASE_URL 未配置，添加默认值" -ForegroundColor Yellow
        Add-Content ".env" "OLLAMA_BASE_URL=`"http://localhost:11434`""
    }
} else {
    Write-Host "✗ .env 文件不存在" -ForegroundColor Red
}

# 5. 检查数据文件
Write-Host "`n[5/5] 检查数据文件..." -ForegroundColor Yellow

if (Test-Path "data") {
    $pdfFiles = Get-ChildItem "data" -Filter "*.pdf"
    if ($pdfFiles.Count -gt 0) {
        Write-Host "✓ 找到 $($pdfFiles.Count) 个 PDF 文件" -ForegroundColor Green
        foreach ($file in $pdfFiles) {
            Write-Host "  - $($file.Name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠ data 目录为空，请添加 PDF 文件" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ data 目录不存在" -ForegroundColor Red
}

# 显示菜单
Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host "准备就绪！请选择操作:" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

Write-Host "`n1. 创建数据库 (python create_save_db.py)" -ForegroundColor White
Write-Host "2. 启动 FastAPI 服务 (python app.py)" -ForegroundColor White
Write-Host "3. 测试 API 接口 (python test_api.py)" -ForegroundColor White
Write-Host "4. 运行 A/B 对比测试 (python test_ab_comparison.py)" -ForegroundColor White
Write-Host "5. 启动 Streamlit UI (streamlit run main.py)" -ForegroundColor White
Write-Host "6. 查看测试指南 (打开 TEST_GUIDE.md)" -ForegroundColor White
Write-Host "0. 退出" -ForegroundColor White

Write-Host "`n请输入选项 (0-6): " -NoNewline -ForegroundColor Yellow
$choice = Read-Host

switch ($choice) {
    "1" {
        Write-Host "`n开始创建数据库..." -ForegroundColor Green
        Write-Host "注意: 这可能需要较长时间，取决于文档大小`n" -ForegroundColor Yellow
        python create_save_db.py
    }
    "2" {
        Write-Host "`n启动 FastAPI 服务..." -ForegroundColor Green
        Write-Host "API 将运行在 http://127.0.0.1:8000" -ForegroundColor Cyan
        Write-Host "按 Ctrl+C 停止服务`n" -ForegroundColor Yellow
        python app.py
    }
    "3" {
        Write-Host "`n测试 API 接口..." -ForegroundColor Green
        Write-Host "确保 FastAPI 服务已在另一个终端启动`n" -ForegroundColor Yellow
        python test_api.py
    }
    "4" {
        Write-Host "`n运行 A/B 对比测试..." -ForegroundColor Green
        Write-Host "这将测试 20 个问题，可能需要较长时间`n" -ForegroundColor Yellow
        python test_ab_comparison.py
    }
    "5" {
        Write-Host "`n启动 Streamlit UI..." -ForegroundColor Green
        Write-Host "确保 FastAPI 服务已在另一个终端启动" -ForegroundColor Yellow
        Write-Host "UI 将在浏览器中自动打开`n" -ForegroundColor Cyan
        streamlit run main.py
    }
    "6" {
        Write-Host "`n打开测试指南..." -ForegroundColor Green
        if (Test-Path "TEST_GUIDE.md") {
            Start-Process "TEST_GUIDE.md"
        } else {
            Write-Host "TEST_GUIDE.md 文件不存在" -ForegroundColor Red
        }
    }
    "0" {
        Write-Host "`n再见！" -ForegroundColor Cyan
        exit 0
    }
    default {
        Write-Host "`n无效选项" -ForegroundColor Red
    }
}

Write-Host "`n按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

