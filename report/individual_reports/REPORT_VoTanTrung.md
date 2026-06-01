# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Võ Tấn Trung]
- **Student ID**: [2A202600642]
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong Lab 3, phần đóng góp kỹ thuật tập trung vào việc mở rộng Travel Concierge Agent theo hướng dễ quan sát lỗi hơn và có khả năng lấy thông tin du lịch ngoài mock data. Các thay đổi chính nằm ở tầng tool, ReAct registry, Streamlit UI và phần evaluation.

- **Modules Implemented**:
  - `src/tools/failure_simulation.py`: thêm cơ chế mô phỏng lỗi có kiểm soát.
  - `src/tools/travel_tools.py`: tích hợp mô phỏng lỗi vào các tool hiện có và thêm tool `search_attractions`.
  - `src/tools/registry.py`: đăng ký tool mới để ReAct Agent có thể gọi.
  - `src/agent/agent.py`: cập nhật rule để agent dùng `search_attractions` khi người dùng hỏi về địa danh/khu tham quan.
  - `streamlit_app.py`: thêm lựa chọn mô phỏng lỗi trên UI và thêm câu mẫu cho SerpAPI.
  - `src/evaluation/metrics_report.py`: bổ sung phân loại lỗi `TOOL_TIMEOUT`.

- **Code Highlights**:
  - Tool mô phỏng lỗi sử dụng context manager để bật/tắt scenario theo từng lần chạy:

```python
with failure_simulation(simulate):
    return agent.run(query, print_trace=show_react)
```

  - Các scenario mô phỏng được hỗ trợ:
    `tool_timeout`, `flight_not_found`, `hotel_not_found`, `promo_not_found`.

  - Tool SerpAPI mới:

```python
def search_attractions(destination: str, query: str = "", limit: int = 5) -> str:
    api_key = os.getenv("SERPAPI_API_KEY")
    ...
```

  Tool này tìm địa danh, khu tham quan hoặc điểm du lịch theo điểm đến người dùng yêu cầu. Kết quả được tóm tắt thành danh sách ngắn gồm tên địa điểm, mô tả và link nếu SerpAPI trả về.

- **Documentation**:
  - Cập nhật `README.md` với biến môi trường `SERPAPI_API_KEY`.
  - Thêm ví dụ CLI:

```bash
python main.py --mode agent -q "Tôi muốn đi Đà Nẵng, hãy tìm vài địa danh và khu tham quan nổi bật."
```

  - Cập nhật `failure_trace_queries.md` để mô tả cách tạo lỗi giả lập ổn định khi demo.

Về tương tác với ReAct loop, các tool đều đi qua `execute_tool()` trong `src/tools/registry.py`. Agent nhận output từ tool dưới dạng `Observation`, sau đó dùng Observation đó để quyết định bước kế tiếp hoặc tạo `Final Answer`. Nhờ vậy, cả mock data, lỗi mô phỏng và kết quả SerpAPI đều đi qua cùng một cơ chế Thought -> Action -> Observation.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  Trong quá trình phân tích failure trace, một vấn đề quan trọng là khó tạo lỗi ổn định để demo và đánh giá. Ví dụ, lỗi timeout hoặc lỗi "không tìm thấy dữ liệu" phụ thuộc vào prompt, model hoặc dữ liệu mock. Nếu chỉ dựa vào câu hỏi tự nhiên, agent có thể không gọi đúng tool cần kiểm thử.

- **Log Source**:
  Các lỗi được quan sát qua tab ReAct Trace, Log phiên JSON trên Streamlit và event `REACT_CYCLE` trong `logs/YYYY-MM-DD.log`. Với mô phỏng lỗi, Observation có dạng:

```text
Simulated timeout: tool 'search_flights' exceeded the allowed response time.
```

hoặc:

```text
No flights found (simulated): the flight catalog returned empty data for this route/date.
```

- **Diagnosis**:
  Đây không phải lỗi của LLM đơn thuần, mà là thiếu cơ chế kiểm thử có kiểm soát ở tầng tool. Khi muốn đánh giá reliability, cần có cách tái tạo các tình huống như timeout, missing flight data, missing hotel data hoặc invalid promo mà không phụ thuộc vào API thật hay hành vi ngẫu nhiên của model.

- **Solution**:
  Thêm module `failure_simulation.py` với context manager `failure_simulation(mode)`. Mỗi tool kiểm tra mode hiện tại trước khi đọc dữ liệu thật. Nếu mode đang bật, tool trả về Observation lỗi giả lập. Streamlit UI có dropdown **Mô phỏng lỗi (agent)** để chọn nhanh scenario. CLI cũng hỗ trợ:

```bash
python main.py --mode agent --simulate tool_timeout
python main.py --mode agent --simulate flight_not_found
python main.py --mode agent --simulate hotel_not_found
python main.py --mode agent --simulate promo_not_found
```

Ngoài ra, `metrics_report.py` được cập nhật để nhận diện timeout giả lập thành failure code `TOOL_TIMEOUT`, giúp phần Evaluation phản ánh lỗi rõ ràng hơn.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
   `Thought` giúp agent chia nhỏ bài toán thành từng bước rõ ràng. Với bài toán tính chi phí du lịch, agent cần gọi flight tool, hotel tool, sau đó dùng promo tool. Chatbot baseline có thể trả lời nhanh hơn nhưng dễ ước lượng số không kiểm chứng. ReAct Agent chậm hơn, nhưng từng con số đều có nguồn từ Observation.

2. **Reliability**:
   Agent có thể tệ hơn chatbot trong các câu hỏi tư vấn chung như "Đà Nẵng tháng 7 có gì hay?". Nếu prompt không tốt, agent có thể cố gọi tool dù câu hỏi chỉ cần trả lời tự nhiên. Agent cũng có thêm rủi ro parser, sai format Action hoặc hết `max_steps`. Vì vậy ReAct mạnh hơn ở tác vụ cần dữ liệu và tính toán, nhưng không phải lúc nào cũng tốt hơn chatbot.

3. **Observation**:
   Observation là phần làm cho agent "bám đất". Khi tool trả `No flights found`, agent không nên bịa giá vé mà phải báo route chưa có trong catalog. Khi `apply_promo` trả `Invalid promo code`, agent phải giải thích mã không hợp lệ và gợi ý các mã hiện có. Observation cũng giúp debug dễ hơn vì có thể nhìn thấy chính xác bước nào khiến kết quả sai.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  Khi số tool tăng lên, nên dùng tool routing hoặc retrieval để chọn tool phù hợp thay vì đưa toàn bộ tool spec vào prompt. Các tool gọi web như SerpAPI cũng nên chạy bất đồng bộ hoặc có cache để giảm latency.

- **Safety**:
  Cần thêm guardrail để agent không tự bịa số liệu ngoài Observation. Với tool web search, nên lọc domain, giới hạn số kết quả, và hiển thị nguồn rõ ràng trong Final Answer. Không nên để agent dùng kết quả web như dữ liệu tuyệt đối nếu nguồn không đáng tin.

- **Performance**:
  ReAct nhiều bước tốn token và latency. Có thể tối ưu bằng cách rút gọn transcript, cache kết quả tool, giới hạn số vòng lặp, và dùng model nhỏ hơn cho bước chọn tool. Với các truy vấn địa danh, cache theo `destination + query` sẽ giúp giảm chi phí SerpAPI.

---

> [!NOTE]
> Personal information fields are intentionally left blank. Rename this file to the required submission filename if needed.
