import streamlit as st
import pandas as pd
import os
import glob
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# Cấu hình giao diện trang web
st.set_page_config(page_title="Trợ lý KPI AI", page_icon="📊")
st.title("📊 Chatbot Truy Vấn Dữ Liệu KPI 2025")

# Lấy khóa bảo mật AI từ hệ thống
api_key = st.secrets["GEMINI_API_KEY"]

# Hàm tự động đọc tất cả file CSV
@st.cache_data
def load_all_csvs():
    csv_files = glob.glob("*.csv")
    dataframes = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            dataframes.append(df)
        except Exception as e:
            pass
    return dataframes

dfs = load_all_csvs()

# Khởi tạo "Bộ não" AI
if dfs:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0)
    agent = create_pandas_dataframe_agent(llm, dfs, verbose=True, allow_dangerous_code=True)
else:
    st.error("Không tìm thấy file dữ liệu nào!")

# Xây dựng giao diện Chatbot
if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Khung nhập câu hỏi
if prompt := st.chat_input("Ví dụ: Doanh thu cửa hàng Đỗ Quang tháng 1 là bao nhiêu?"):
    # Hiển thị câu hỏi của user
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AI xử lý và trả lời
    with st.chat_message("assistant"):
        with st.spinner("AI đang tính toán số liệu..."):
            try:
                response = agent.run(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error("Xin lỗi, tôi không thể tìm thấy dữ liệu phù hợp hoặc câu hỏi quá phức tạp.")
