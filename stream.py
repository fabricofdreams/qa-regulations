import streamlit as st

st.set_page_config("Test")
st.header("Just testing")

with st.sidebar:
    selection = st.radio(
        label="Do you need to load additional data?",
        options=["Yes", "No"],
        captions=["It is Visible", "It is Unvisible"],
        key="options",
        horizontal=True
    )
    if selection == "Yes":
        st.write(selection)
