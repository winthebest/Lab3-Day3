# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đào Văn Tuân
- **Student ID**: 2A202600609
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong Lab 3, phần đóng góp của tôi tập trung vào **mở rộng agent travel** (tool mới + dữ liệu mock) và **cải thiện Streamlit** để so sánh GPT và Gemini trực tiếp trên giao diện, không chỉ qua file `.env`.

- **Modules Implemented / Updated**:
  - `src/core/llm_runtime.py` — quản lý provider/model theo phiên (ưu tiên hơn `.env` khi chạy Streamlit).
  - `src/core/provider_factory.py` — đọc cấu hình hiệu lực từ `llm_runtime` khi gọi `get_llm_provider()`.
  - `src/tools/travel_tools.py` — thêm `estimate_trip_cost` và `get_weather_forecast`.
  - `src/tools/data/travel_data.json` — bổ sung catalog `weather` (mock) cho DAD, HAN, SGN.
  - `src/tools/registry.py` — đăng ký tool mới vào `TOOL_REGISTRY` / `TOOL_SPECS`.
  - `src/agent/agent.py` — cập nhật rule system prompt (ưu tiên `estimate_trip_cost`, dùng `get_weather_forecast` khi hỏi thời tiết).
  - `streamlit_app.py` — sidebar chọn **GPT (OpenAI)** / **Gemini (Google)** + model; hiển thị provider trong kết quả; câu mẫu thời tiết.
  - `tests/test_travel_tools.py` — unit test cho tool mới.

- **Code Highlights**:

**1. Chọn LLM trên Streamlit (GPT ↔ Gemini)**

```python
def set_session_llm(provider: str, model: str) -> None:
    ...
    _session_provider = p
    _session_model = model
```

Sidebar gọi `set_session_llm()` mỗi lần rerun; `get_llm_provider()` lấy `(provider, model)` từ `get_effective_config()` trước khi tạo `ReActAgent` hoặc chạy chatbot.

**2. Tool `estimate_trip_cost` — gộp vé + khách sạn + promo**

```python
def estimate_trip_cost(
    origin: str, destination: str, depart_date: str,
    passengers: int = 1, nights: int = 2, ...
    promo_code: str = "",
) -> str:
    ...
    subtotal = flight_total + hotel_total
    if promo_code:
        promo_out = apply_promo(promo_code, subtotal)
```

Giảm số vòng ReAct khi người dùng hỏi *tổng chi phí* (câu mẫu Đà Nẵng + SUMMER).

**3. Tool `get_weather_forecast` — dự báo mock**

```python
weather = weather_by_city.get(city_code)
...
lines.append(
    f"- {row['date']}: {row['condition']}, "
    f"{row['temp_min_c']}–{row['temp_max_c']}°C, ..."
)
```

Dữ liệu đọc từ `travel_data.json` → không cần API thời tiết thật; phù hợp lab và demo ổn định.

- **Documentation (tương tác ReAct)**:
  - Mọi tool đi qua `execute_tool()` trong `registry.py` → agent nhận **Observation** dạng chuỗi.
  - Agent parse `Action: tool_name(...)` → gọi tool → append `Observation: ...` vào transcript cho vòng LLM tiếp theo.
  - `estimate_trip_cost` tái sử dụng logic `normalize_city`, catalog `routes`/`hotels`/`promos` — đồng bộ với `search_flights` / `get_hotel_rate` / `apply_promo`.
  - `get_weather_forecast` dùng chung `normalize_city` (HCM→SGN, Đà Nẵng→DAD) để tránh agent gọi sai mã thành phố.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  Khi chạy agent với câu hỏi thời tiết tại điểm **chưa có trong catalog mock** (ví dụ Nha Trang / CXR), tool `get_weather_forecast` trả về:

```text
No weather forecast (mock) for 'Nha Trang' (code CXR). Available cities: DAD (Đà Nẵng), HAN (Hà Nội), SGN (TP. Hồ Chí Minh).
```

  Một số lần chạy, agent vẫn cố **Final Answer** bằng cách “đoán” nhiệt độ thay vì nói rõ không có dữ liệu — trace ReAct cho thấy Observation đã báo lỗi nhưng bước sau không xử lý đúng.

- **Log Source**:
  - Event `REACT_CYCLE` trong `logs/YYYY-MM-DD.log` (payload có `observation` chứa `No weather forecast`).
  - Tab **ReAct Trace** / **Log phiên (JSON)** trên `streamlit_app.py` — cycle có icon cảnh báo khi observation chứa `not found` / `error`.

- **Diagnosis**:
  - **Tool spec**: đã trả về thông báo rõ và liệt kê city khả dụng — phía tool ổn.
  - **Prompt/model**: system prompt chưa nhấn mạnh *“nếu observation báo không có dữ liệu mock thì không bịa số, hãy trả lời dựa trên danh sách city có sẵn hoặc đề xuất đổi điểm đến”*.
  - **So sánh provider**: với **Gemini**, đôi khi vẫn viết Final Answer tổng quát; với **GPT**, thường tuân thủ observation tốt hơn trong cùng câu hỏi (quan sát khi đổi provider trên sidebar).

- **Solution**:
  - Bổ sung rule trong `agent.py`: khi observation chứa `No weather` / `not found`, agent phải thừa nhận giới hạn mock data.
  - Thêm câu mẫu Streamlit **🌤 Thời tiết Đà Nẵng** (destination có trong catalog) để demo đúng luồng tool thành công.
  - Khi debug: bật sidebar **GPT vs Gemini**, chạy cùng một câu hỏi và so sánh tab Evaluation (token, số vòng ReAct, reliability).

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
   Khối **Thought** giúp agent lập kế hoạch nhiều bước (vé → khách sạn → promo → thời tiết) thay vì trả lời một lần như chatbot. Với câu *“Tổng chi phí + thời tiết Đà Nẵng 15/07”*, ReAct có thể gọi `estimate_trip_cost` rồi `get_weather_forecast` — mỗi bước có số liệu kiểm chứng trong Observation. Chatbot baseline thường đưa khoảng giá và mô tả thời tiết chung chung, dễ **hallucinate** số VND và % mưa.

2. **Reliability**:
   ReAct **kém hơn** chatbot khi:
   - Tool trả lỗi / không có data (route CXR, city không có weather mock) — agent tốn thêm vòng LLM mà vẫn có thể sai Final Answer.
   - Câu hỏi mơ hồ (“đi biển cho vui”) — agent gọi nhiều tool không cần thiết, tăng token và latency.
   - `max_steps` thấp — chưa kịp `Final Answer` sau 2–3 Action.

   Chatbot ổn định hơn cho **tư vấn chung** (ẩm thực, văn hóa) không cần số liệu catalog.

3. **Observation influence**:
   Observation dạng **bảng giá rõ** (từ `estimate_trip_cost`) giúp bước sau chỉ cần tóm tắt tiếng Việt + VND. Observation dạng **lỗi có hướng dẫn** (liệt kê city/route khả dụng) nên dẫn agent sang hành động sửa tham số; nếu chỉ ghi `error` chung chung, agent dễ lặp lại cùng Action. Việc đổi **GPT/Gemini** trên sidebar cho thấy cùng Observation nhưng **bước Thought kế tiếp** khác nhau — quan trọng khi đánh giá lab.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  Tách weather mock sang service riêng hoặc API thật (OpenWeather); cache observation theo `(city_code, start_date)` để nhiều user không gọi lặp catalog JSON.

- **Safety**:
  Validator trước `Final Answer`: kiểm tra số VND trong câu trả lời có khớp Observation gần nhất không; chặn câu trả lời khi tool báo `not found` mà vẫn có con số cụ thể.

- **Performance**:
  Tool `estimate_trip_cost` đã giảm vòng ReAct — mở rộng pattern “composite tool” cho các câu hỏi phổ biến (vé + khách sạn + weather 3 ngày). Với >10 tool, dùng retrieval chọn tool thay vì liệt kê hết trong system prompt.

- **UX (Streamlit)**:
  Nút **so sánh GPT vs Gemini** trên cùng một câu hỏi (đã có compare Chatbot/Agent) — có thể thêm hàng so sánh song song hai provider cho agent để phục vụ báo cáo nhóm.

---

## V. Personal Reflection

Lab 3 giúp tôi thấy rõ: agent mạnh không chỉ ở prompt mà ở **thiết kế tool + dữ liệu mock có cấu trúc**. Phần tôi làm (`estimate_trip_cost`, `get_weather_forecast`, chọn GPT/Gemini trên UI) hướng tới demo ổn định và đo lường được (trace, token, reliability). Để đưa vào production cần chuẩn hóa response tool (JSON + `status`), policy xử lý lỗi rõ ràng, và không phụ thuộc hoàn toàn vào việc model “tự hiểu” Observation tiếng Anh.

**Cách chạy phần đóng góp:**

```bash
streamlit run streamlit_app.py
# Sidebar: chọn GPT (gpt-4o) hoặc Gemini (gemini-1.5-flash)
# Câu mẫu: "🌤 Thời tiết Đà Nẵng" hoặc "✅ Đà Nẵng + SUMMER"
```

```bash
python -m pytest tests/test_travel_tools.py -q
```
