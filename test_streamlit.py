import streamlit as st

st.title("Halo Fakultas!")
nama = st.text_input("Masukkan namamu:")

if st.button("Sapa"):
    st.success(f"Halo, {nama}! Selamat datang.")