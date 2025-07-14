import streamlit as st
import boto3

st.set_page_config(page_title="benefit-claims")  # HTML title
st.title("benefit-claims")  # page title

bucket_name = "benefit-claim-ingestion-bucket-sdf123"
s3 = boto3.client("s3")

uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png"],label_visibility="collapsed")
if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

go_button = st.button("Analyze the file", type="primary")  # display a primary button


if go_button: 
    doc_bytes = uploaded_file.getvalue()
    s3.put_object(Body=doc_bytes, Bucket=bucket_name, Key=uploaded_file.name)
    
