# Câu hỏi tạo Failed Trace — Lab Travel Agent

Dùng với **Agent v1** (chưa sửa prompt) để thu trace lỗi trong `logs/YYYY-MM-DD.log`  
Tìm event `REACT_CYCLE` có `observation` lỗi hoặc Final Answer sai logic.

## Cách chạy

```cmd
conda activate vinai
cd D:\Lab\Day-3-Lab-Chatbot-vs-react-agent
python main.py --mode agent -q "CÂU_HỎI_Ở_DƯỚI"
```

So sánh chatbot (dễ fail kiểu khác):

```cmd
python main.py --mode chatbot -q "CÂU_HỎI_Ở_DƯỚI"
```

---

## 1. Tool trả lỗi — route không có trong mock

**Câu hỏi:**
```
Tìm vé máy bay từ SGN đến Nha Trang (CXR) ngày 2026-07-15 cho 2 người.
```

**Kỳ vọng fail:** `Observation` chứa `No flights found` / route không tồn tại.

**Loại lỗi:** Empty observation / no data.

---

## 2. Tool trả lỗi — mã giảm giá sai

**Câu hỏi:**
```
Tôi đi Đà Nẵng, tổng đơn 5.400.000 VND, áp dụng mã khuyến mãi WINTER.
```

**Kỳ vọng fail:** `Invalid promo code 'WINTER'`.

**Loại lỗi:** Tool error / invalid args.

---

## 3. Hallucination — tool không tồn tại

**Câu hỏi:**
```
Đặt khách sạn Đà Nẵng 2 đêm ngày 15/07/2026, dùng tool book_hotel ngay.
```

**Kỳ vọng fail:** `Tool 'book_hotel' not found`.

**Loại lỗi:** Hallucinated tool.

---

## 4. Hallucination — tên tool gần đúng

**Câu hỏi:**
```
Tra giá phòng khách sạn Đà Nẵng bằng search_hotels(city=DAD, nights=2).
```

**Kỳ vọng fail:** `search_hotels` không có — chỉ có `get_hotel_rate`.

**Loại lỗi:** Hallucinated tool name.

---

## 5. Sai tham số — mã sân bay / thành phố

**Câu hỏi:**
```
Tìm vé từ HCM đến Da Nang ngày 2026-07-15, 2 người. (không dùng mã IATA)
```

**Kỳ vọng fail:** Agent gọi `search_flights(origin="HCM", destination="Da Nang")` → route lỗi hoặc normalize sai.

**Loại lỗi:** Wrong IATA / parser args (sửa ở v2 bằng prompt + map city).

---

## 6. Logic sai — nhầm số đêm

**Câu hỏi:**
```
Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?
```

**Kỳ vọng fail (mềm):** Agent gọi `nights=3` thay vì `2` → subtotal / promo sai so với đáp án đúng **4.860.000 VND**.

**Loại lỗi:** Logic error (trace vẫn “chạy xong” nhưng Final Answer sai).

**Đáp án đúng tham chiếu:**
- Vé: 3.000.000 | KS 2 đêm: 2.400.000 | Trước promo: 5.400.000 | Sau SUMMER: **4.860.000**

---

## 7. Logic sai — vé “khứ hồi” (đã gặp khi chạy thành công)

**Câu hỏi:** (cùng câu mẫu ở mục 6)

**Kỳ vọng fail (mềm):** Tool `search_flights` là **một chiều** nhưng Final Answer ghi **“vé khứ hồi”**.

**Loại lỗi:** Observation đúng, câu trả lời sai (hallucinate loại vé).

---

## 8. Timeout — hết số bước

**Câu hỏi:** (câu mẫu đầy đủ — xem mục 6)

```cmd
python main.py --mode agent --max-steps 2 -q "Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?"
```

**Kỳ vọng fail:** Không đủ bước gọi đủ 3 tool → không có Final Answer đúng / `AGENT_END` với kết quả dở.

**Loại lỗi:** Max steps exceeded.

---

## 9. Thiếu Thought (ReAct format)

**Câu hỏi:** (câu mẫu mục 6 — chạy vài lần với Gemini/OpenAI)

**Kỳ vọng fail (mềm):** Trong log `REACT_CYCLE`, `"thought": null` ở cycle 1–3.

**Loại lỗi:** ReAct format incomplete (sửa prompt v2).

---

## 10. Chatbot baseline — bịa số (so sánh, không phải agent trace)

**Câu hỏi:**
```
Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?
```

```cmd
python main.py --mode chatbot -q "..."
```

**Kỳ vọng:** Không có `REACT_CYCLE`; câu trả lời ước lượng / số không khớp tool mock → dùng trong bảng **Chatbot vs Agent**.

---

## Ghi vào báo cáo (mẫu ngắn)

| # | Câu hỏi (rút gọn) | Loại fail | Observation / Final Answer sai |
|---|-------------------|-----------|------------------------------|
| 1 | SGN → CXR | No route | `No flights found...` |
| 2 | Mã WINTER | Invalid promo | `Invalid promo code...` |
| 3 | book_hotel | Hallucination | `Tool 'book_hotel' not found` |
| 6 | 3N2Đ + SUMMER | Logic | nights=3 hoặc tổng ≠ 4.86M |
| 7 | 3N2Đ + SUMMER | Wording | “khứ hồi” vs one-way |

**Success trace (đối chiếu):** cùng câu mục 6, agent gọi đủ `search_flights` → `get_hotel_rate(nights=2)` → `apply_promo(SUMMER, 5400000)` → **4.860.000 VND**.

---

*Nguồn: LAB_IDEAS.html · tools: `search_flights`, `get_hotel_rate`, `apply_promo`*
