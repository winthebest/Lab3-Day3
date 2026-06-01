# Individual Report: Lab 3 - Travel Concierge

- **Student Name**: Nguyễn Bá Thành
- **Student ID**: 2A202600675
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

- **Modules reviewed / summarized**:
  - `src/agent/agent.py` — ReAct loop implementation, parsing Thought/Action/Final Answer and orchestration of tool calls.
  - `src/tools/travel_tools.py` — Mock travel tools: `search_flights`, `get_hotel_rate`, `apply_promo`, `search_attractions` and argument parsing.
  - `src/core/provider_factory.py` & `src/config.py` — Provider selection (openai/google/local) and `.env` loading.
  - `src/telemetry/logger.py` & `src/telemetry/metrics.py` — Event logging and metric tracking for evaluation and failure analysis.
  - `streamlit_app.py` — Web UI for running and comparing Chatbot vs ReAct agent, attaching evaluation reports.

- **What I did for this report**:
  - Đọc và tóm tắt các thành phần chính trong `src/` để mô tả kiến trúc và luồng dữ liệu.
  - Kiểm tra các file chạy được: `main.py`, `chatbot.py`, `streamlit_app.py` để mô tả cách chạy và các tuỳ chọn (provider, simulate).
  - Chạy qua các unit tests trong `tests/` (tham khảo `tests/test_travel_tools.py`) để hiểu các kịch bản mô phỏng lỗi.

- **Code highlights / important behaviors**:
  - `ReActAgent.get_system_prompt()` ép định dạng output LLM với `Thought:` và `Action:` giúp parse tự động trong agent.
  - Tool implementations trả về chuỗi mô tả (không objects) — thuận tiện cho logging và display nhưng cần parse khi tính toán.
  - `provider_factory.py` chỉ load provider được chọn để tránh import nặng khi không cần (local vs cloud).

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Khi kích hoạt simulation "flight_not_found", `search_flights` trả về một thông báo mô phỏng chứa "No flights" và từ khoá "simulated" (xem `src/tools/failure_simulation.py` và `tests/test_travel_tools.py`).

- **Log Source**: ReAct cycle events được ghi bằng `logger.log_event('REACT_CYCLE', payload)` trong `src/agent/agent.py` và toàn bộ session events có thể xem trong file `logs/YYYY-MM-DD.log` (Streamlit hiển thị tail log).

- **Diagnosis**: Nguyên nhân do chế độ `failure_simulation` ép `simulated_observation` (được repo sử dụng cho testing), agent nhận observation chứa chuỗi lỗi thay vì dữ liệu hợp lệ, dẫn tới vòng lặp dừng sớm hoặc trả về Final Answer sai.

- **Solution / Mitigation**:
  - Trong production, tách trạng thái error/empty response rõ ràng (ví dụ: trả về JSON với `status` + `message`) để agent có thể quyết định retry/switch-tool.
  - Thêm timeout và retry policy trong `execute_tool` (registry) để phân biệt network timeout với data-not-found.
  - Khi debug, dùng `streamlit_app.py` để kiểm tra `react_trace` và log JSON để xác định cycle lỗi nhanh.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: ReAct cho phép LLM tách phần "tư duy" (Thought) và hành động (Action) — điều này hữu dụng khi cần nhiều bước, vì mỗi hành động trả về observation có thể kiểm chứng. Chatbot đơn lẻ thường đưa ước lượng tổng quát nhưng dễ bị hallucinate về số.

2. **Reliability**: ReAct có thể kém hơn Chatbot khi tools mô phỏng lỗi hoặc tools yếu — agent có thể bị kẹt trong vòng lặp gọi tool nhiều lần. Chatbot đôi khi ổn định hơn cho câu hỏi mô tả/du lịch chung.

3. **Observation influence**: Observation sạch (ví dụ: văn bản chứa giá tiền rõ ràng) giúp agent tiến tới Final Answer chính xác. Observation dạng lỗi cần policy: retry, bỏ qua tool, hoặc fallback sang Chatbot-style estimate.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Chạy tool calls bất đồng bộ (async) để giảm tổng wall-clock khi có nhiều LLM calls.
- **Safety & Robustness**: Chuẩn hoá định dạng trả về từ tools (structured JSON) và thêm "Supervisor" kiểm tra consistency trước khi Final Answer.
- **Performance**: Cache kết quả tool calls theo route/date để tránh gọi lại cùng một thông tin lặp.

## VII. Personal reflection

Làm việc với kiến trúc ReAct giúp tôi hiểu rõ giá trị của "observations" có kiểm chứng khi xây multi-step agents. Để triển khai thực tế, cần chuẩn hoá interfaces giữa agent và tools, cùng policy robust cho lỗi tool.
