# 龙子湖食堂 RAG 系统 - 问题修复总结

## ✅ 已解决的问题

### 1. 数据库创建成功
- ✅ 向量数据库（ChromaDB）已创建
- ✅ BM25 索引已创建
- 位置：`./src/db/canteen_db_vectordb/` 和 `./src/db/canteen_db_bm25/`

### 2. Embedding 模型不匹配问题已修复
**问题**：
- 数据库创建时使用：`BAAI/bge-base-en-v1.5` (768维)
- 测试时尝试使用：`BAAI/bge-small-zh-v1.5` (512维)
- 导致错误：`Collection expecting embedding with dimension of 768, got 512`

**解决方案**：
已修改以下文件使用正确的模型：
- ✅ `test_ab_simple.py` - 改用 `bge-base-en-v1.5`
- ✅ `quick_test.py` - 改用 `bge-base-en-v1.5`

---

## 🚀 如何运行测试

### 方法 1：使用 PowerShell 脚本（推荐）
```powershell
.\run_test.ps1
```
然后选择：
- [1] 快速测试 (3个问题)
- [2] 标准测试 (5个问题)  
- [3] 完整测试 (20个问题)

### 方法 2：直接运行 Python 命令
```powershell
# 快速测试（3个问题）
python test_ab_simple.py 3

# 标准测试（5个问题）
python test_ab_simple.py 5

# 完整测试（20个问题）
python test_ab_simple.py
```

### 方法 3：简化验证测试
```powershell
python simple_test.py
```

---

## 📊 测试说明

### 测试内容
对比两种检索方法：
- **方法 A**：纯向量检索
- **方法 B**：混合检索（向量 + BM25）

### 测试问题示例
1. 龙子湖校区有几个食堂？
2. 哪个食堂最便宜？
3. 哪个食堂的菜品种类最多？
... (共20个问题)

### 输出结果
测试完成后会生成：
- `ab_test_results_YYYYMMDD_HHMMSS.json` - JSON格式结果
- `ab_test_report_YYYYMMDD_HHMMSS.txt` - 文本格式报告

---

## ⚠️ 注意事项

1. **首次运行会下载模型**
   - `BAAI/bge-base-en-v1.5` 约 438MB
   - 使用国内镜像加速（已配置）

2. **确保 Ollama 服务运行**
   ```bash
   # 在 WSL 中运行
   ollama serve
   ```

3. **如果遇到网络问题**
   - 脚本已配置使用 HuggingFace 镜像
   - 如仍超时，可多次重试

---

## 🔧 故障排除

### 问题1：维度不匹配错误
```
Collection expecting embedding with dimension of 768, got 512
```
**解决**：确保所有脚本使用 `BAAI/bge-base-en-v1.5`（已修复）

### 问题2：Ollama 连接失败
```
无法连接到 Ollama 服务
```
**解决**：
1. 在 WSL 中运行 `ollama serve`
2. 检查 `.env` 中的 `OLLAMA_BASE_URL` 配置

### 问题3：数据库找不到
```
向量数据库不存在
```
**解决**：先运行 `python create_save_db.py` 创建数据库

---

## 📝 下一步建议

### 如果想使用中文模型（可选）
1. 删除现有数据库：
   ```powershell
   Remove-Item -Recurse -Force .\src\db\canteen_db_*
   ```

2. 修改 `src/contextual_retrieval/save_vectordb.py`：
   ```python
   # 第16行改为：
   embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")
   ```

3. 重新创建数据库：
   ```powershell
   python create_save_db.py
   ```

4. 测试脚本会自动匹配（已改为中文模型）

---

## ✨ 项目完成状态

- [x] Ollama 连接测试
- [x] 数据库创建
- [x] 修复模型匹配问题
- [ ] 运行 A/B 对比测试 ← **你现在这里**
- [ ] 查看测试报告
- [ ] （可选）启动 API 服务

---

**现在可以运行测试了！建议使用：**
```powershell
python test_ab_simple.py 3
```

