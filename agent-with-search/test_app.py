import streamlit as st

st.title("Test App")
st.write("If you see this, Streamlit is working!")

if st.button("Click me"):
    st.success("Button clicked!")