# Lab 3 — Travel Concierge: Chatbot vs ReAct Agent

**Khóa học:** Agentic AI · **Lab:** Chatbot baseline vs ReAct Agent có tool & telemetry

---

## Giới thiệu đề tài

Nhóm triển khai **Travel Concierge** — trợ lý du lịch nội địa Việt Nam — để so sánh hai cách dùng LLM:

| Thành phần | Mô tả |
| :--- | :--- |
| **Chatbot baseline** | Một lần gọi LLM, **không** gọi tool; trả lời tư vấn / ước lượng giá. |
| **ReAct Agent** | Vòng lặp **Thought → Action → Observation**; gọi tool mock để lấy số liệu có kiểm chứng. |

**Luồng nghiệp vụ mẫu:** khách ở HCM → Đà Nẵng (3 ngày 2 đêm, 2 người, ngày khởi hành, mã **SUMMER**) → agent gọi lần lượt:

1. `search_flights` — giá vé một chiều  
2. `get_hotel_rate` — giá khách sạn × số đêm  
3. `apply_promo` — giảm giá trên subtotal  

**Kết quả chuẩn (mock data):** **4.860.000 VND** (3.000.000 vé + 2.400.000 khách sạn − 10% SUMMER).

Mọi bước được ghi log JSON (`REACT_CYCLE`, `LLM_METRIC`) trong thư mục `logs/` để phân tích lỗi và so sánh với rubric trong [SCORING.md](SCORING.md).

---

## Thành viên nhóm

| STT | Họ tên | MSSV | Vai trò / đóng góp |
| ---: | :--- | :--- | :--- |
| 1 | *Phan Võ Trọng Tiển* | *2A202600781* | *ReAct agent, telemetry* |
| 2 | *Võ Tấn Trung* | *2A202600642* | *travel tools, mock data* |
| 3 | *Đào Văn Tuân* | *2A202600609* | *(ví dụ: Streamlit, evaluation)* |
| 4 | *Nguyễn Bá Thành* | *2A202600675* | *(ví dụ: Streamlit, evaluation)* |
- **Tên nhóm:** Lab3-Travel-Concierge  
- **Báo cáo nhóm:** [report/group_report/GROUP_REPORT_LAB3_TRAVEL.md](report/group_report/GROUP_REPORT_LAB3_TRAVEL.md)

---

## Cấu trúc dự án

```
Day-3-Lab-Chatbot-vs-react-agent/
├── chatbot.py                 # Baseline không tool
├── main.py                    # CLI: agent | chatbot | compare
├── streamlit_app.py           # Giao diện web + trace + evaluation
├── src/
│   ├── agent/agent.py         # ReAct loop
│   ├── tools/                 # search_flights, get_hotel_rate, apply_promo
│   ├── core/                  # OpenAI / Gemini / Local providers
│   ├── telemetry/             # Logger + metrics
│   └── evaluation/            # Token, latency, failure classification
├── tests/test_travel_tools.py
├── logs/                      # Log JSON theo ngày
└── failure_trace_queries.md   # Câu hỏi tạo trace lỗi (RCA)
```

---

## Hướng dẫn chạy

### 1. Môi trường

```bash
conda activate vinai
cd Day-3-Lab-Chatbot-vs-react-agent
pip install -r requirements.txt
```

### 2. Cấu hình API

Sao chép file mẫu và điền key:

```bash
copy .env.example .env
```

Chỉnh `.env` (chọn **một** provider chính):

```env
# OpenAI (khuyến nghị cho demo ổn định)
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Hoặc Google Gemini
# DEFAULT_PROVIDER=google
# DEFAULT_MODEL=gemini-2.5-flash
# GEMINI_API_KEY=...

# Hoặc local (xem mục dưới)
# DEFAULT_PROVIDER=local
# LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
```

> Trên Windows, nếu key trong biến môi trường hệ thống lệch với `.env`, project dùng `load_dotenv(override=True)` trong `src/config.py`.

### 3. Chạy ứng dụng

**Giao diện web (khuyến nghị):**

```bash
streamlit run streamlit_app.py
```

Mở trình duyệt: `http://localhost:8501` — xem ReAct trace, so sánh chatbot/agent, tab Evaluation.

**Dòng lệnh:**

```bash
# ReAct agent + in trace
python main.py --mode agent

# Chatbot baseline
python main.py --mode chatbot

# So sánh cùng một câu hỏi
python main.py --mode compare -q "Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?"
```

**Test tool (không cần API):**

```bash
pytest tests/test_travel_tools.py -v
```

### 4. Câu hỏi mẫu

| Mục đích | Câu hỏi |
| :--- | :--- |
| **Success (multi-step)** | Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính? |
| **Fail — route** | Tìm vé SGN đến Nha Trang (CXR) ngày 2026-07-15 cho 2 người. |
| **Fail — promo** | Tổng đơn 5.400.000 VND, áp mã WINTER. |

Thêm câu test: [failure_trace_queries.md](failure_trace_queries.md).

### 5. Xem log

Sau mỗi lần chạy, mở `logs/YYYY-MM-DD.log` (JSON lines): `AGENT_START`, `REACT_CYCLE`, `LLM_METRIC`, `CHATBOT_START`, …

---

## Chạy model local (tùy chọn)

Dùng **Phi-3-mini** qua `llama-cpp-python` khi không muốn gọi API cloud.

1. Tải [Phi-3-mini-4k-instruct-q4.gguf](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf) (~2.2 GB) vào `models/`.
2. Cài package: `pip install llama-cpp-python`
3. Trong `.env`: `DEFAULT_PROVIDER=local`

Nếu gặp lỗi **`Windows Error 0xc000001d`** (CPU không hỗ trợ AVX2), build lại với:

```powershell
pip uninstall llama-cpp-python -y
$env:FORCE_CMAKE = "1"
$env:CMAKE_ARGS = "-DLLAMA_AVX=off -DLLAMA_AVX2=off -DLLAMA_FMA=off -DLLAMA_F16C=off"
pip install llama-cpp-python --no-cache-dir --force-reinstall
```

Provider cloud (`openai` / `google`) **không** cần cài `llama-cpp-python` — factory chỉ load provider được chọn.

---

## Tài liệu liên quan

| File | Nội dung |
| :--- | :--- |
| [SCORING.md](SCORING.md) | Rubric chấm điểm nhóm + cá nhân |
| [EVALUATION.md](EVALUATION.md) | Token, latency, failure codes |
| [TRAVEL_README.md](TRAVEL_README.md) | Ghi chú nhanh chủ đề travel |
| [report/group_report/GROUP_REPORT_LAB3_TRAVEL.md](report/group_report/GROUP_REPORT_LAB3_TRAVEL.md) | Báo cáo nhóm |

---

*Lab 3 — Production-grade agentic prototype với telemetry và phân tích lỗi có chủ đích.*
