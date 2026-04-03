import streamlit as st
import pandas as pd
import os
import io
from PIL import Image
from streamlit_gsheets import GSheetsConnection
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. CẤU HÌNH GIAO DIỆN NÂNG CẤP ---
st.set_page_config(page_title="Trợ lý KPI Toàn Năng", page_icon="📈", layout="wide")
st.title("📈 Trợ lý AI Phân Tích KPI & Vẽ Biểu Đồ")

api_key = st.secrets["GEMINI_API_KEY"]

# --- 2. CẤU HÌNH GOOGLE SHEETS (SỬA Ở ĐÂY) ---
# Dán đường link Google Sheets của bạn:
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Gpemfz8h1trFZz28IkASZ5osMQnkgjy6YX3BVUPmTI0/edit2"

# Ghi chính xác tên các Sheet bạn muốn đọc:
SHEET_NAMES = ["Cửa hàng 2025", "Cửa hàng 2026", "Dự Án Online 2025", "Dự Án Online 2026", "Các nguồn 2025", "Các nguồn 2026"] 
# ---------------------------------------------

# --- 3. HÀM TẢI DỮ LIỆU ---
@st.cache_data(ttl=600)
def load_gsheets_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    dataframes = []
    for sheet in SHEET_NAMES:
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet)
            if not df.empty:
                dataframes.append(df)
        except Exception as e:
            st.warning(f"⚠️ Bỏ qua sheet '{sheet}' vì lỗi: {e}")
    return dataframes

# --- TÍNH NĂNG 1: GIAO DIỆN SIDEBAR (THANH BÊN) ---
with st.sidebar:
    st.header("⚙️ Bảng Điều Khiển")
    
    # Nút bấm làm mới dữ liệu tức thì không cần chờ 10 phút
    if st.button("🔄 Làm mới dữ liệu ngay", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    
    # Khu vực xem trước dữ liệu (Data Preview)
    st.subheader("👁️ Dữ liệu đang phân tích")
    dfs = load_gsheets_data()
    if dfs:
        for i, df in enumerate(dfs):
            with st.expander(f"Xem bảng {i+1} ({len(df)} dòng)"):
                st.dataframe(df.head(5)) # Chỉ hiện 5 dòng đầu cho gọn
    else:
        st.warning("Chưa có dữ liệu.")

# --- 4. KHỞI TẠO AI (BỔ SUNG QUY TẮC VẼ BIỂU ĐỒ) ---
QUY_TAC = """
Bạn là Giám đốc Phân tích Dữ liệu.
1. Trả lời bằng Tiếng Việt, ngắn gọn, chính xác. KHÔNG tự bịa số liệu.
2. NẾU NGƯỜI DÙNG YÊU CẦU VẼ BIỂU ĐỒ: Bắt buộc import `matplotlib.pyplot as plt`. Sau khi vẽ xong, bạn PHẢI lưu ảnh bằng lệnh `plt.savefig('bieudo.png', bbox_inches='tight')`. Không sử dụng plt.show(). Trả lời người dùng: "Tôi đã vẽ biểu đồ cho bạn ở bên dưới."
"""

if dfs:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)
        agent = create_pandas_dataframe_agent(
            llm, dfs, verbose=True, allow_dangerous_code=True, handle_parsing_errors=True, prefix=QUY_TAC
        )
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo AI: {e}")

# --- 5. TÍNH NĂNG TRÍ NHỚ & KHUNG CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Nút gợi ý câu hỏi nhanh (nằm trên khung chat)
col1, col2, col3 = st.columns(3)
quick_prompt = None
if col1.button("📊 Báo cáo tổng doanh thu"): quick_prompt = "Tổng doanh thu trong bảng là bao nhiêu?"
if col2.button("📈 Vẽ biểu đồ doanh thu"): quick_prompt = "Hãy vẽ biểu đồ cột thể hiện doanh thu."
if col3.button("🔍 Cửa hàng nào cao nhất?"): quick_prompt = "Cửa hàng nào có doanh thu cao nhất?"

# Hiển thị lịch sử chat (Bao gồm cả ảnh biểu đồ cũ)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message:
            st.image(message["image"])

# Nhận câu hỏi từ nút bấm hoặc do người dùng tự gõ
prompt = quick_prompt or st.chat_input("Hỏi tôi phân tích hoặc yêu cầu vẽ biểu đồ...")

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("AI đang phân tích và xử lý..."):
            try:
                # CẤP TRÍ NHỚ: Gom 4 tin nhắn gần nhất đưa cho AI để nó hiểu ngữ cảnh
                history_context = ""
                if len(st.session_state.messages) > 1:
                    history_context = "Ngữ cảnh cuộc trò chuyện trước đó:\n"
                    for msg in st.session_state.messages[-5:-1]:
                        history_context += f"{msg['role']}: {msg['content']}\n"
                
                full_prompt = f"{history_context}\n\nCâu hỏi hiện tại: {prompt}"
                
                # AI Xử lý
                result = agent.invoke({"input": full_prompt}, config={"callbacks": []})
                response = result["output"]
                st.markdown(response)
                
                msg_data = {"role": "assistant", "content": response}
                
                # BẮT ẢNH BIỂU ĐỒ TỪ AI (NẾU CÓ)
                if os.path.exists("bieudo.png"):
                    with open("bieudo.png", "rb") as f:
                        img_data = f.read()
                        img = Image.open(io.BytesIO(img_data))
                        st.image(img)
                        msg_data["image"] = img # Lưu ảnh vào trí nhớ để lần sau load lại
                    os.remove("bieudo.png") # Xóa file rác

                st.session_state.messages.append(msg_data)

            except Exception as e:
                st.error(f"⚠️ Hệ thống đang gặp lỗi xử lý. Chi tiết: {e}")
