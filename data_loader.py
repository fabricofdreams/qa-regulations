import streamlit as st
import datetime


def get_metadata(genres_dict, status_dict, themes_dict,  months_dict):
    genres_list = [key for key in genres_dict]
    themes_list = [key for key in themes_dict]
    status_list = [key for key in status_dict]
    months_list = [key for key in months_dict]
    current_year = datetime.datetime.now().year
    years_list = list(range(1900, current_year + 1))
    days_list = list(range(1, 32))

    st.subheader("Add metadata")
    title = st.text_input(
        "Title:", help="Write a brief title for the regulation.")
    col11, col12 = st.columns(2)
    col21, col22, col23, col24 = st.columns(4)

    with col11:
        genre = st.selectbox("Genre:", options=genres_list, index=1,
                             help="Select type of regulations from the list.")
        status = st.selectbox("Status:", options=status_list,
                              help="Select the status from the list")
    with col12:
        dependency = st.text_input(
            "Dependency:", help="Write the name of the dependecy that generates the regulation.")
        theme = st.selectbox("Theme:", options=themes_list, index=1,
                             help="Select the theme or topic from the list.")
    with col21:
        code = st.text_input(
            "Code:", help="Write the number/code of the regulation.")
    with col22:
        year = st.selectbox(
            "Year:", options=years_list, index=71)
    with col23:
        month = st.selectbox(
            "Month:", options=months_list)
    with col24:
        day = st.selectbox(
            "Day:",  options=days_list)

    metadata = {
        "genre": genre,
        "status": status,
        "dependency": dependency,
        "theme": theme,
        "title": title,
        "code": code,
        "year": year,
        "month": month,
        "day": day
    }

    empty_keys = [key for key, value in metadata.items() if value ==
                  "" or value is None]
    counter = len(empty_keys)
    if empty_keys:
        st.warning(f"Keys with empty values: {counter}")
    else:
        st.success("Ready: Not empty values")
        file_name = f"{genres_dict[genre]}#{year}#{code}#{themes_dict[theme]}#{status_dict[status]}.pdf"
        return file_name
