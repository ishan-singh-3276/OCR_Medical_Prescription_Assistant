import pytesseract
from PIL import Image
import os
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
import easyocr
from db_helper import init_db, create_user, verify_user, save_patient_info, get_patient_info

load_dotenv()

# Initialize database
init_db()

# Page config
st.set_page_config(page_title="Medical Prescription Assistant", layout="centered")

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None

# Authentication UI
if not st.session_state.authenticated:
    st.title("🏥 Medical Prescription Assistant")
    st.write("Please log in or sign up to continue.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Log in with existing account", use_container_width=True):
            st.session_state.auth_mode = "login"
    
    with col2:
        if st.button("Sign up by creating a new account", use_container_width=True):
            st.session_state.auth_mode = "signup"
    
    if "auth_mode" in st.session_state:
        st.markdown("---")
        
        if st.session_state.auth_mode == "login":
            st.markdown("### 🔐 Log In")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Log In", use_container_width=True)
                
                if submit:
                    if username and password:
                        success, message = verify_user(username, password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.username = username
                            patient_info = get_patient_info(username)
                            if patient_info:
                                st.session_state.patient_info = patient_info
                                st.session_state.patient_info_completed = True
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please enter both username and password")
        
        elif st.session_state.auth_mode == "signup":
            st.markdown("### 📝 Sign Up")
            with st.form("signup_form"):
                st.markdown("**Account Information**")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                st.markdown("**Patient Information**")
                col1, col2 = st.columns(2)
                
                with col1:
                    age = st.number_input("Age", min_value=1, max_value=120, value=25, step=1)
                    gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
                    weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=70.0, step=0.1)
                
                with col2:
                    height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=170.0, step=0.1)
                    blood_group = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"])
                
                existing_conditions = st.text_area("Existing Medical Conditions (if any)", 
                                                   placeholder="e.g., Diabetes, Hypertension, Asthma...")
                allergies = st.text_area("Known Allergies (if any)", 
                                        placeholder="e.g., Penicillin, Peanuts, Latex...")
                current_medications = st.text_area("Current Medications (if any)", 
                                                  placeholder="e.g., Metformin 500mg twice daily, Aspirin 75mg...")
                medical_history = st.text_area("Relevant Medical History (optional)", 
                                              placeholder="e.g., Previous surgeries, family history...")
                
                submit = st.form_submit_button("Sign Up", use_container_width=True)
                
                if submit:
                    if not username or not password or not confirm_password:
                        st.error("Please fill in all fields")
                    elif password != confirm_password:
                        st.error("Passwords do not match")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters long")
                    else:
                        patient_data = {
                            'age': age,
                            'gender': gender,
                            'weight': weight,
                            'height': height,
                            'blood_group': blood_group,
                            'existing_conditions': existing_conditions if existing_conditions else "None",
                            'allergies': allergies if allergies else "None",
                            'current_medications': current_medications if current_medications else "None",
                            'medical_history': medical_history if medical_history else "None"
                        }
                        success, message = create_user(username, password, patient_data)
                        if success:
                            st.success("✅ Sign up complete! Please log in with your credentials.")
                            st.session_state.auth_mode = "login"
                            st.rerun()
                        else:
                            st.error(message)
    
    st.stop()

# Main application starts here (only shown if authenticated)
st.title("🏥 Medical Prescription Assistant")
st.write(f"Welcome, {st.session_state.username}! Get personalized medical assistance based on your prescription.")

# Logout button
if st.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.auth_mode = None
    st.rerun()

st.markdown("---")

# Initialize session state for chat history and extracted text
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "extracted_text_tesseract" not in st.session_state:
    st.session_state.extracted_text_tesseract = ""
if "extracted_text_easyocr" not in st.session_state:
    st.session_state.extracted_text_easyocr = ""
if "initial_analysis" not in st.session_state:
    st.session_state.initial_analysis = ""
if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}
if "patient_info_completed" not in st.session_state:
    st.session_state.patient_info_completed = False

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Show patient info summary
st.markdown("### 👤 Your Information")
col1, col2 = st.columns(2)

with col1:
    st.write(f"**Age:** {st.session_state.patient_info['age']}")
    st.write(f"**Gender:** {st.session_state.patient_info['gender']}")
    st.write(f"**Weight:** {st.session_state.patient_info['weight']} kg")
    st.write(f"**Height:** {st.session_state.patient_info['height']} cm")
    st.write(f"**Blood Group:** {st.session_state.patient_info['blood_group']}")

with col2:
    st.write(f"**Existing Conditions:** {st.session_state.patient_info['existing_conditions']}")
    st.write(f"**Allergies:** {st.session_state.patient_info['allergies']}")
    st.write(f"**Current Medications:** {st.session_state.patient_info['current_medications']}")
    st.write(f"**Medical History:** {st.session_state.patient_info['medical_history']}")

st.markdown("---")

# Image uploader
upload_image = st.file_uploader("Upload a prescription image", type=["png", "jpg", "jpeg"])

if upload_image is not None:
    # Show uploaded image
    image = Image.open(upload_image)
    st.image(image, caption="Uploaded Image", use_container_width=True)

    # Button to trigger LLM processing
    if st.button("Get OCR Response"):
        with st.spinner("Processing image and waiting for response..."):
            # OCR with Tesseract
            text_tesseract = pytesseract.image_to_string(image)
            
            # OCR with EasyOCR
            reader = easyocr.Reader(['en'])
            results_easyocr = reader.readtext(image)
            text_easyocr = ' '.join([result[1] for result in results_easyocr])
            
            # OCR with LLM (Gemini)
            model_ocr = genai.GenerativeModel("gemini-2.5-flash")
            prompt_ocr = """
            Please analyze this image and extract all the text you can find.
            Provide the extracted text in a clear, readable format.
            If there are any handwritten or printed text, include it.
            Organize the text as it appears in the image.
            Do not add any additional commentary, just provide the extracted text.
            """
            response_ocr = model_ocr.generate_content([prompt_ocr, image])
            text_llm = response_ocr.text
            
            # Store the texts
            st.session_state.extracted_text_tesseract = text_tesseract
            st.session_state.extracted_text_easyocr = text_easyocr
            st.session_state.extracted_text_llm = text_llm
            
            # Use LLM OCR text for analysis
            text = text_llm

            # Create patient context string
            patient_context = f"""
            Patient Information:
            - Age: {st.session_state.patient_info['age']} years
            - Gender: {st.session_state.patient_info['gender']}
            - Weight: {st.session_state.patient_info['weight']} kg
            - Height: {st.session_state.patient_info['height']} cm
            - Blood Group: {st.session_state.patient_info['blood_group']}
            - Existing Conditions: {st.session_state.patient_info['existing_conditions']}
            - Known Allergies: {st.session_state.patient_info['allergies']}
            - Current Medications: {st.session_state.patient_info['current_medications']}
            - Medical History: {st.session_state.patient_info['medical_history']}
            """
            
            prompt = f"""
            You are a medical assistant analyzing a prescription for a specific patient.
            
            {patient_context}
            
            The following is text extracted from a scanned medical prescription.

            Please:
            1. Identify the medicine names mentioned.
            2. For each medicine, provide:
               - A brief, clear explanation of what the medicine is used for
               - Any relevant considerations based on the patient's profile (age, existing conditions, allergies, current medications)
               - Potential interactions or concerns specific to this patient
            3. Format the output as a numbered list like:
            1. <Medicine Name> : <Brief Explanation>
               Patient-specific considerations: <Relevant notes based on patient profile>

            ---
            Extracted Text:
            \"\"\"
            {text}
            \"\"\"
            """

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            st.session_state.initial_analysis = response.text

            # Clear previous chat history when new image is analyzed
            st.session_state.chat_history = []

            # Display extracted OCR text
            st.markdown("### 📝 Extracted OCR Text")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**▪️ Tesseract OCR:**")
                st.info(st.session_state.extracted_text_tesseract)
            
            with col2:
                st.markdown("**▪️ EasyOCR:**")
                st.info(st.session_state.extracted_text_easyocr)
            
            with col3:
                st.markdown("**▪️ LLM OCR:**")
                st.info(st.session_state.extracted_text_llm)

            # Output the response
            st.markdown("### 💊 Medicine Analysis")
            st.success(response.text)
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if user_question := st.chat_input("Ask a question about the prescription..."):
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_question)

            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Create patient context string
                    patient_context = f"""
                    Patient Information:
                    - Age: {st.session_state.patient_info['age']} years
                    - Gender: {st.session_state.patient_info['gender']}
                    - Weight: {st.session_state.patient_info['weight']} kg
                    - Height: {st.session_state.patient_info['height']} cm
                    - Blood Group: {st.session_state.patient_info['blood_group']}
                    - Existing Conditions: {st.session_state.patient_info['existing_conditions']}
                    - Known Allergies: {st.session_state.patient_info['allergies']}
                    - Current Medications: {st.session_state.patient_info['current_medications']}
                    - Medical History: {st.session_state.patient_info['medical_history']}
                    """
                    
                    # Create context-aware prompt
                    context_prompt = f"""
                    You are a helpful, personalized medical assistant. You are providing medical advice to a specific patient.
                    
                    {patient_context}
                    
                    You have already analyzed this prescription for the patient:
                    
                    Extracted Text from Prescription:
                    \"\"\"
                    {st.session_state.extracted_text_tesseract}
                    \"\"\"
                    
                    Initial Analysis:
                    \"\"\"
                    {st.session_state.initial_analysis}
                    \"\"\"
                    
                    Previous Conversation:
                    {chr(10).join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.chat_history[:-1]])}
                    
                    Current User Question: {user_question}
                    
                    Please provide a helpful, accurate, and personalized response based on:
                    1. The prescription information above
                    2. The patient's specific profile (age, gender, existing conditions, allergies, current medications, medical history)
                    3. Any potential interactions or considerations specific to this patient
                    
                    Always consider the patient's individual circumstances when providing medical advice.
                    """
                    
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(context_prompt)
                    assistant_response = response.text
                    
                    st.markdown(assistant_response)
                    
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})

        # Optional: Clear chat button
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()