import streamlit as st
import anthropic
import base64
import json
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="ECG Analysis System",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2563eb 0%, #4f46e5 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-card {
        background-color: #f8fafc;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .finding-positive {
        color: #dc2626;
        font-weight: bold;
    }
    .finding-negative {
        color: #16a34a;
    }
    .metric-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        text-align: center;
    }
    .info-box {
        background-color: #dbeafe;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
    .warning-box {
        background-color: #fef3c7;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
    }
    .success-box {
        background-color: #d1fae5;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #10b981;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

def encode_image(image_file):
    """Convert uploaded file to base64"""
    bytes_data = image_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def analyze_ecg_with_claude(image_file, api_key):
    """Analyze ECG using Claude API"""
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Determine file type and prepare content
    file_type = image_file.type
    base64_data = encode_image(image_file)
    
    analysis_prompt = """You are an expert cardiologist analyzing an ECG. Analyze this ECG image using standard ECG grid parameters (0.04s horizontal, 1mm = 0.1mV vertical).

Provide detailed analysis for:

1. LBBB Assessment:
   - QRS duration (≥120ms?)
   - R wave morphology in I, aVL, V5-V6
   - Q waves in I, V5, V6
   - S waves in V1-V3
   - R-peak time in V6
   - Strauss criteria (QRS ≥140ms men/≥130ms women, mid-QRS notch/slur)

2. LVH Assessment:
   - Sokolow-Lyon: S(V1) + R(V5/6)
   - Cornell: S(V3) + R(aVL)
   - R in aVL
   - Supportive features (LAD, strain pattern)

3. LVH with LBBB:
   - QRS duration >160ms
   - Modified Sokolow-Lyon ≥45mm
   - R in aVL ≥11mm

4. RBBB Assessment:
   - QRS duration
   - rsR' pattern in V1
   - Terminal S waves in I, aVL, V5, V6
   - Appropriate discordance

5. RVH Assessment:
   - RAD (>+110°)
   - R wave in V1
   - R/S ratio in V1
   - qR pattern
   - RV strain pattern

6. RVH with RBBB:
   - RAD >110°
   - R' height in V1
   - R/S ratio in V1

7. Chamber Enlargement in AF:
   - LAE: f-wave characteristics in V1
   - RAE: f-wave characteristics in V1, II, III, aVF

Return results in JSON format with this exact structure:
{
  "rhythmAnalysis": "description of rhythm",
  "qrsDuration": number in ms,
  "heartRate": number,
  "findings": {
    "lbbb": {
      "present": true/false,
      "criteria": ["list of met criteria"],
      "confidence": "high/medium/low",
      "straussCriteria": true/false
    },
    "lvh": {
      "present": true/false,
      "criteria": ["list of met criteria"],
      "sokolowLyon": number,
      "cornell": number,
      "confidence": "high/medium/low"
    },
    "lvhWithLbbb": {
      "assessable": true/false,
      "findings": ["list of findings"]
    },
    "rbbb": {
      "present": true/false,
      "criteria": ["list of met criteria"],
      "confidence": "high/medium/low"
    },
    "rvh": {
      "present": true/false,
      "criteria": ["list of met criteria"],
      "confidence": "high/medium/low"
    },
    "rvhWithRbbb": {
      "assessable": true/false,
      "findings": ["list of findings"]
    },
    "atrialEnlargement": {
      "lae": true/false,
      "rae": true/false,
      "details": "description"
    }
  },
  "clinicalSignificance": "interpretation and clinical context",
  "recommendations": ["list", "of", "recommendations"]
}"""

    # Prepare message content based on file type
    if file_type == 'application/pdf':
        content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64_data
                }
            },
            {"type": "text", "text": analysis_prompt}
        ]
    else:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file_type,
                    "data": base64_data
                }
            },
            {"type": "text", "text": analysis_prompt}
        ]
    
    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    
    # Extract response
    response_text = message.content[0].text
    
    # Try to extract JSON
    try:
        # Find JSON in response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            return {"error": False, "rawAnalysis": response_text}
    except Exception as e:
        return {"error": False, "rawAnalysis": response_text}

def display_finding_card(title, data, icon="📊"):
    """Display a finding card"""
    st.markdown(f"### {icon} {title}")
    
    with st.container():
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, bool):
                    status = "✅ Positive" if value else "❌ Negative"
                    color_class = "finding-positive" if value else "finding-negative"
                    st.markdown(f"**{key.replace('_', ' ').title()}:** <span class='{color_class}'>{status}</span>", unsafe_allow_html=True)
                elif isinstance(value, list):
                    st.markdown(f"**{key.replace('_', ' ').title()}:**")
                    for item in value:
                        st.markdown(f"  • {item}")
                elif isinstance(value, (int, float)):
                    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                else:
                    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🫀 ECG Analysis System</h1>
    <p>Advanced ECG interpretation for LBBB, RBBB, LVH, RVH, and Chamber Enlargement</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_key = st.text_input("Anthropic API Key", type="password", help="Enter your Anthropic API key")
    
    st.markdown("---")
    
    st.markdown("""
    ### 📋 Analysis Parameters
    
    **Standard ECG Grid:**
    - Horizontal: 0.04s per small box
    - Vertical: 1mm = 0.1 mV
    - Paper speed: 25 mm/s
    
    **Analyzed Conditions:**
    - ✅ LBBB (Standard & Strauss)
    - ✅ LVH (Sokolow-Lyon, Cornell)
    - ✅ LVH with LBBB
    - ✅ RBBB
    - ✅ RVH
    - ✅ RVH with RBBB
    - ✅ Atrial enlargement (LAE/RAE)
    """)
    
    st.markdown("---")
    
    st.info("💡 Upload a clear ECG image for best results")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload ECG")
    
    uploaded_file = st.file_uploader(
        "Choose an ECG file",
        type=['jpg', 'jpeg', 'png', 'pdf'],
        help="Upload ECG in JPG, JPEG, PNG, or PDF format"
    )
    
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file
        
        # Display preview for images
        if uploaded_file.type != 'application/pdf':
            st.subheader("📸 Preview")
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
        else:
            st.success(f"✅ PDF uploaded: {uploaded_file.name}")
    
    # Analyze button
    if st.session_state.uploaded_file is not None:
        if st.button("🔍 Analyze ECG", type="primary", use_container_width=True):
            if not api_key:
                st.error("⚠️ Please enter your Anthropic API key in the sidebar")
            else:
                with st.spinner("🔬 Analyzing ECG... This may take a moment..."):
                    try:
                        results = analyze_ecg_with_claude(st.session_state.uploaded_file, api_key)
                        st.session_state.analysis_results = results
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")

with col2:
    st.header("📊 Analysis Results")
    
    if st.session_state.analysis_results is None:
        st.info("👈 Upload an ECG and click 'Analyze ECG' to see results")
    else:
        results = st.session_state.analysis_results
        
        if results.get('error'):
            st.error(f"❌ {results.get('message', 'Analysis error occurred')}")
        else:
            # Success message
            st.markdown('<div class="success-box">✅ <strong>Analysis Complete</strong><br>Comprehensive ECG analysis based on standard criteria</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Basic metrics
            if 'rhythmAnalysis' in results or 'qrsDuration' in results or 'heartRate' in results:
                st.subheader("📈 Basic Measurements")
                
                metric_cols = st.columns(3)
                
                if 'heartRate' in results:
                    with metric_cols[0]:
                        st.markdown(f'<div class="metric-box"><h3>{results["heartRate"]}</h3><p>Heart Rate (bpm)</p></div>', unsafe_allow_html=True)
                
                if 'qrsDuration' in results:
                    with metric_cols[1]:
                        st.markdown(f'<div class="metric-box"><h3>{results["qrsDuration"]}</h3><p>QRS Duration (ms)</p></div>', unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
            
            if 'rhythmAnalysis' in results:
                st.markdown(f'<div class="info-box"><strong>Rhythm Analysis:</strong><br>{results["rhythmAnalysis"]}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

# Display findings in tabs
if st.session_state.analysis_results and not st.session_state.analysis_results.get('error'):
    results = st.session_state.analysis_results
    
    if 'findings' in results:
        findings = results['findings']
        
        tabs = st.tabs([
            "🔴 LBBB",
            "💙 LVH", 
            "🟣 RBBB",
            "🟠 RVH",
            "🟢 Atrial Enlargement",
            "📋 Summary"
        ])
        
        with tabs[0]:
            if 'lbbb' in findings:
                display_finding_card("Left Bundle Branch Block Analysis", findings['lbbb'], "🔴")
            if 'lvhWithLbbb' in findings:
                st.markdown("<br>", unsafe_allow_html=True)
                display_finding_card("LVH with LBBB Assessment", findings['lvhWithLbbb'], "⚠️")
        
        with tabs[1]:
            if 'lvh' in findings:
                display_finding_card("Left Ventricular Hypertrophy Analysis", findings['lvh'], "💙")
        
        with tabs[2]:
            if 'rbbb' in findings:
                display_finding_card("Right Bundle Branch Block Analysis", findings['rbbb'], "🟣")
        
        with tabs[3]:
            if 'rvh' in findings:
                display_finding_card("Right Ventricular Hypertrophy Analysis", findings['rvh'], "🟠")
            if 'rvhWithRbbb' in findings:
                st.markdown("<br>", unsafe_allow_html=True)
                display_finding_card("RVH with RBBB Assessment", findings['rvhWithRbbb'], "⚠️")
        
        with tabs[4]:
            if 'atrialEnlargement' in findings:
                display_finding_card("Atrial Enlargement Analysis", findings['atrialEnlargement'], "🟢")
        
        with tabs[5]:
            if 'clinicalSignificance' in results:
                st.markdown(f'<div class="warning-box"><strong>⚕️ Clinical Significance:</strong><br>{results["clinicalSignificance"]}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
            
            if 'recommendations' in results and results['recommendations']:
                st.subheader("💊 Recommendations")
                for i, rec in enumerate(results['recommendations'], 1):
                    st.markdown(f"{i}. {rec}")
            
            if 'rawAnalysis' in results:
                with st.expander("📄 View Detailed Analysis"):
                    st.text(results['rawAnalysis'])
    
    # Reset button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Analyze Another ECG", use_container_width=True):
        st.session_state.analysis_results = None
        st.session_state.uploaded_file = None
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 2rem;'>
    <p><strong>⚠️ Medical Disclaimer:</strong> This tool is for educational and research purposes only. 
    Always consult with qualified healthcare professionals for clinical decisions.</p>
    <p style='font-size: 0.9em; margin-top: 1rem;'>Powered by Claude AI | Standard ECG Grid: 0.04s × 0.1mV</p>
</div>
""", unsafe_allow_html=True)
