# 龙子湖食堂 RAG 系统 - A/B 测试指南

## 环境配置

### 1. WSL Ollama 配置

在 WSL (Linux) 中启动 Ollama 服务：

```bash
# 确保已安装 ollama 和下载 gemma2:12b 模型
ollama serve
```

检查 Ollama 是否运行：
```bash
curl http://localhost:11434/api/tags
```

### 2. 获取 WSL IP 地址

如果需要从 Windows 访问 WSL 的 Ollama：

**方法 1：使用 localhost (推荐)**
- Windows 11/10 最新版本支持直接通过 localhost 访问 WSL 服务
- 在 `.env` 文件中设置：`OLLAMA_BASE_URL="http://localhost:11434"`

**方法 2：使用 WSL IP**
在 WSL 中运行：
```bash
ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1
```

得到类似 `172.x.x.x` 的 IP，然后在 `.env` 中设置：
```
OLLAMA_BASE_URL="http://172.x.x.x:11434"
```

### 3. Python 环境配置

在 Windows 中（项目根目录）：

```powershell
# 创建虚拟环境（可选）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置 .env 文件

确保 `.env` 文件内容如下：

```env
DATA_DIR="./data"
SAVE_DIR="./src/db"
VECTOR_DB_PATH="./src/db/canteen_db_vectordb"
BM25_DB_PATH="./src/db/canteen_db_bm25"
COLLECTION_NAME="ncwu_canteen_collection"
API_URL="http://127.0.0.1:8000/rag-chat"
OLLAMA_BASE_URL="http://localhost:11434"
```

## 测试流程

### 步骤 1：创建数据库（首次运行）

```powershell
python create_save_db.py
```

这将：
- 读取 `./data` 目录下的 PDF 文件
- 使用 WSL 的 Ollama (gemma2:12b) 为每个文本块生成上下文
- 创建 ChromaDB 向量数据库
- 创建 BM25 索引

**注意**：这个过程可能需要较长时间（取决于文档大小和 chunk 数量）

### 步骤 2：启动 FastAPI 服务

在新终端中：

```powershell
python app.py
```

API 将在 http://127.0.0.1:8000 启动

### 步骤 3：测试 API（可选）

在新终端中：

```powershell
python test_api.py
```

或使用 curl：

```powershell
# PowerShell
$body = @{query="龙子湖校区有几个食堂？"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://127.0.0.1:8000/rag-chat" -Method POST -Body $body -ContentType "application/json"
```

### 步骤 4：运行 A/B 对比测试

在新终端中：

```powershell
python test_ab_comparison.py
```

这将：
1. 创建两个索引：
   - 普通 RAG（不加上下文）
   - 上下文增强 RAG（加上下文）
2. 对 20 个测试问题分别测试两种方法
3. 生成对比报告（JSON 和 TXT 格式）

### 步骤 5：启动 Streamlit UI（可选）

```powershell
streamlit run main.py
```

在浏览器中打开 http://localhost:8501

## 测试问题列表（20 条）

1. 龙子湖校区有几个食堂？
2. 哪个食堂最便宜？
3. 哪个食堂的菜品种类最多？
4. 食堂的营业时间是什么时候？
5. 早餐有什么推荐的？
6. 哪里可以吃到面食？
7. 哪个食堂的环境最好？
8. 有清真餐厅吗？
9. 晚上宵夜哪里可以吃？
10. 哪个食堂离教学楼最近？
11. 食堂可以用支付宝吗？
12. 哪里有麻辣烫？
13. 食堂的米饭多少钱？
14. 哪个食堂人最少？
15. 有没有水果店？
16. 食堂二楼有什么特色？
17. 周末食堂开门吗？
18. 哪里可以吃到炒菜？
19. 食堂有WiFi吗？
20. 学生推荐去哪个食堂？

## 预期结果

测试完成后会生成：

1. **ab_test_results_YYYYMMDD_HHMMSS.json** - 详细的 JSON 数据
2. **ab_test_report_YYYYMMDD_HHMMSS.txt** - 可读性好的文本报告

报告包含：
- 每个问题的两种方法的回答
- 响应时间对比
- 平均性能统计

## 常见问题

### Q1: 连接不上 WSL 的 Ollama

**解决方案**：
1. 确保 WSL 中 `ollama serve` 正在运行
2. 检查防火墙设置
3. 尝试使用 WSL IP 而不是 localhost
4. 在 WSL 中运行：`ollama serve --host 0.0.0.0`

### Q2: 导入错误

**解决方案**：
```powershell
pip install -r requirements.txt --upgrade
```

### Q3: 内存不足

gemma2:12b 模型较大，如果遇到内存问题：
1. 确保 WSL 有足够内存（至少 16GB 系统内存）
2. 或改用更小的模型，如 `gemma2:2b`

### Q4: ChromaDB 创建失败

**解决方案**：
```powershell
# 删除旧数据库重试
Remove-Item -Recurse -Force .\src\db\*
python create_save_db.py
```

## 性能优化建议

1. **使用 SSD** - 将项目放在 SSD 上可显著提升向量检索速度
2. **调整 chunk_size** - 默认 512，可根据文档特点调整
3. **增加 top_k** - 默认检索 3 个相关块，可增加到 5
4. **使用 GPU** - 如果有 GPU，可配置 Ollama 使用 GPU 加速

## 文件说明

- `test_ab_comparison.py` - A/B 对比测试主脚本
- `test_api.py` - API 接口测试脚本
- `create_save_db.py` - 数据库创建脚本
- `app.py` - FastAPI 服务
- `main.py` - Streamlit UI
- `.env` - 环境配置文件

## 下一步

测试完成后，可以：
1. 分析 A/B 测试报告，对比两种方法的效果
2. 调整 prompt 模板优化回答质量
3. 尝试不同的 chunk_size 和 overlap
4. 测试其他文档

