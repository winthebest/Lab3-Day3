# Individual Report: Lab 3 — Chatbot vs ReAct Agent

- **Student Name**: Phan Võ Trọng Tiển
- **Student ID**: 2A202600781
- **Date**: 2026-06-01
- **Vai trò nhóm:** Thiết kế kiến trúc và triển khai **toàn bộ codebase** Lab 3 (Travel Concierge)

---

## I. Technical Contribution (15 Points)

Tôi **thiết kế và hiện thực hóa toàn bộ hệ thống** từ skeleton lab thành prototype Travel Concierge hoàn chỉnh: chatbot baseline, ReAct agent, lớp tool mock, đa provider LLM, telemetry, evaluation và giao diện Streamlit. Các thành viên khác hỗ trợ review, test và bổ sung báo cáo theo từng hạng mục rubric.

### Kiến trúc tổng thể (do tôi thiết kế)

```text
User → [chatbot.py | main.py | streamlit_app.py]
         ↓
    provider_factory → OpenAI | Gemini | Local (LLMProvider)
         ↓
    ReActAgent.run() ↔ registry.execute_tool() ↔ travel_tools + travel_data.json
         ↓
    telemetry (logger + metrics) → logs/*.log → metrics_report / UI Evaluation
```

### Modules Implemented (toàn bộ dự án)

| Lớp | Module | Mô tả thiết kế / triển khai |
| :--- | :--- | :--- |
| **Entry** | `chatbot.py`, `main.py`, `streamlit_app.py` | Baseline 1-shot; CLI `agent` / `chatbot` / `compare`; UI trace + evaluation |
| **Agent** | `src/agent/agent.py` | ReAct loop, system prompt v2, parse Thought/Action/Final Answer, `REACT_CYCLE` |
| **Tools** | `src/tools/travel_tools.py`, `registry.py`, `data/travel_data.json` | 3 tool du lịch, mock catalog, `parse_tool_args`, `TOOL_SPECS` |
| **LLM** | `src/core/*_provider.py`, `provider_factory.py`, `config.py` | Interface provider; lazy import; `load_dotenv(override=True)` |
| **Observability** | `src/telemetry/logger.py`, `metrics.py` | JSON logs, `LLM_METRIC`, cost/latency mock |
| **Evaluation** | `src/evaluation/metrics_report.py` | Token efficiency, latency, `classify_failures` |
| **QA / docs** | `tests/test_travel_tools.py`, `failure_trace_queries.md`, `README.md` | Test tool; playbook RCA; hướng dẫn chạy |

### Code Highlights

Vòng lặp ReAct — trung tâm thiết kế agent:

```92:101:src/agent/agent.py
            if action:
                tool_name, arg_string = action
                action_str = f"{tool_name}({arg_string})"
                observation = execute_tool(tool_name, arg_string)
                cycle["action"] = action_str
                cycle["observation"] = observation
                self.react_trace.append(cycle)
                self._log_react_cycle(cycle)

                transcript += f"\n{content.strip()}\nObservation: {observation}\n"
```

Tách provider để Streamlit/CLI không phụ thuộc `llama_cpp` khi dùng cloud API:

```19:38:src/core/provider_factory.py
    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider
        return OpenAIProvider(...)
    if provider == "google":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(...)
    if provider == "local":
        from src.core.local_provider import LocalProvider
        return LocalProvider(...)
```

### Documentation — Luồng end-to-end

1. **Chatbot:** một `llm.generate()` + system prompt «không có API giá» → baseline so sánh.
2. **Agent:** `get_tool_specs()` → prompt → lặp Thought/Action → `execute_tool` → Observation trong transcript.
3. **Telemetry:** mọi bước ghi `logs/YYYY-MM-DD.log` phục vụ group report và tab Evaluation.
4. **Chủ đề Travel:** chọn mock thay vì finance để demo multi-step rõ (vé + khách sạn + promo).

---

## II. Debugging Case Study (10 Points)

*Ví dụ lỗi phát hiện khi tích hợp toàn stack (agent + parser + prompt + log).*

### Problem Description

Agent trả **5.670.000 VND** thay vì **4.860.000 VND** với câu chuẩn SUMMER, dù observation vé/khách sạn đúng.

### Log Source

File: `logs/2026-06-01.log` (~08:33, GPT-4o)

```json
"action": "apply_promo(code=\"SUMMER\", subtotal=3000000+2400000)",
"observation": "Subtotal 3,000,000 VND − discount 300,000 VND = 2,700,000 VND.",
"final_answer": "... là 5,670,000 VND."
```

### Diagnosis

| Thành phần hệ thống | Vấn đề |
| :--- | :--- |
| **LLM** | Gửi biểu thức thay vì số nguyên |
| **`parse_tool_args`** | Regex chỉ bắt literal đầu → `subtotal=3000000` |
| **Prompt / TOOL_SPECS** | Chưa khóa contract «integer subtotal only» |

### Solution (đã áp dụng trong thiết kế v2)

1. System prompt: bắt buộc Thought; không bịa số; map IATA; `nights=2` cho 3N2Đ.
2. `TOOL_SPECS`: ghi **one-way**, ví dụ `apply_promo(..., subtotal=8400000)`.
3. Run sau (~08:42): `subtotal=5400000` → **4.860.000 VND** — xác nhận trên cùng codebase.
4. Backlog: validate `parse_tool_args` từ chối `+` trong giá trị số.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Quan sát khi thiết kế và chạy thử cả hai nhánh trên cùng một repo.*

### 1. Reasoning — Vai trò `Thought`

Thiết kế ReAct buộc tách **kế hoạch** (Thought) và **thực thi** (Action). Chatbot baseline cố ý giữ một lần gọi để thấy rõ giới hạn: trả lời mượt nhưng không bind catalog. Đây là lý do lab có hai entry point song song (`chatbot.py` vs `main.py --mode agent`).

### 2. Reliability — Agent tệ hơn Chatbot khi nào?

| Tình huống | Kết luận thiết kế |
| :--- | :--- |
| Tư vấn chung, không cần giá | Chatbot đủ; agent dễ over-tool |
| Định giá multi-step | Agent đúng nếu observation + parser ổn |
| Latency / chi phí | Agent luôn nặng hơn (nhiều `LLM_METRIC`) |

### 3. Observation — Ảnh hưởng bước sau

Thiết kế tool trả text có cấu trúc (giá × số khách/đêm) để LLM bước sau chỉ việc cộng và gọi `apply_promo`. Lỗi 5.67M chứng minh **contract tool + parser** quan trọng ngang prompt — đã ghi vào `failure_trace_queries.md` và `classify_failures()`.

---

## IV. Future Improvements (5 Points)

| Hướng | Đề xuất (từ góc người thiết kế hệ thống) |
| :--- | :--- |
| **Scalability** | Tách service tool (REST) khỏi process agent; queue async |
| **Safety** | Lớp validate args trước `execute_tool`; supervisor audit Action |
| **Performance** | RAG chọn tool khi >10 tools; cache observation; streaming UI |

---

> Nộp: `REPORT_Phan_Vo_Trong_Tien.md`
