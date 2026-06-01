# Travel Concierge — Lab 3 (chủ đề Du lịch)

## Cấu trúc

```
src/tools/
  data/travel_data.json   # mock vé, khách sạn, mã SUMMER/FAMILY
  travel_tools.py         # search_flights, get_hotel_rate, apply_promo
  registry.py             # specs + execute_tool
src/agent/agent.py        # ReAct loop
chatbot.py                # baseline không tool
main.py                   # CLI agent / chatbot / compare
```

## Chạy

```bash
conda activate vinai
pip install streamlit

# Giao diện web + ReAct trace + Evaluation (EVALUATION.md) + log
streamlit run streamlit_app.py

# Test tool (không cần API)
pytest tests/test_travel_tools.py -v

# Chatbot baseline
python chatbot.py

# ReAct agent
python main.py --mode agent

# So sánh cả hai
python main.py --mode compare -q "Tôi ở HCM, đi Đà Nẵng 3 ngày 2 đêm, 2 người, 15/07/2026, mã SUMMER. Tổng chi phí?"
```

Cấu hình `.env`: `DEFAULT_PROVIDER=google`, `GEMINI_API_KEY=...`, `DEFAULT_MODEL=gemini-2.5-flash`

Log: thư mục `logs/`

## Câu mẫu (multi-step)

> Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?

Agent nên: `search_flights` → `get_hotel_rate` (nights=2) → cộng subtotal → `apply_promo(SUMMER)`.
