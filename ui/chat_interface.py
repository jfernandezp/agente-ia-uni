import streamlit as st
import json
import logging
from typing import Dict, Any
import base64
from core.orchestrator import ConversationOrchestrator
from services.ip_utils import get_client_ip
from services.dynamodb import ImageUsageRepository

logger = logging.getLogger(__name__)

def render_tea_chat_interface(orchestrator: ConversationOrchestrator):
    """
    TEA-optimized chat interface:
    - High contrast
    - No animations
    - Readable font
    - Predictable structure
    """
    
    # TEA visual configuration
    st.markdown("""
    <style>
        /* High contrast */
        .stApp {
            background-color: #FFFFFF;
            color: #000000;
        }
        
        /* No animations */
        * {
            animation: none !important;
            transition: none !important;
        }
        
        /* Readable font */
        .stMarkdown, .stText, p, li {
            font-family: 'Arial', sans-serif;
            font-size: 18px;
            line-height: 1.6;
            color: #000000;
        }
        
        /* Clear buttons */
        .stButton button {
            background-color: #0066CC;
            color: white;
            font-weight: bold;
            border-radius: 4px;
            border: 2px solid #004999;
        }
        
        /* Chat area with clear border */
        .chat-message {
            border-left: 4px solid #0066CC;
            padding: 10px;
            margin: 10px 0;
            background-color: #F8F9FA;
        }
        
        /* Clear input */
        .stTextInput input, .stTextArea textarea {
            border: 2px solid #0066CC;
            border-radius: 4px;
            font-size: 18px;
        }
        
        /* Readable metrics */
        .stMetric {
            background-color: #F8F9FA;
            padding: 10px;
            border-radius: 4px;
            border: 1px solid #DDD;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Clear title
    #st.title("🎓 Ignatius Assistant")
    st.markdown("""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 15px; color: white; text-align: center; 
                    margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="margin:0; color:white;">🤖 Ignatius Assistant</h2>
            <h4 style="margin:0; color:white;">Clear, direct and predictable communication.</h4>
        </div>
        """, unsafe_allow_html=True)
    
    #st.caption("Clear, direct and predictable communication")
    
    # Get client IP
    client_ip = get_client_ip()
    st.session_state["client_ip"] = client_ip
    
    # TEA control panel (SIMPLE)
    with st.sidebar:
        
        #st.sidebar.image("images/image.png", width=150)
        # st.header("⚙️ Communication options")
        
        # # Verbosity selector - ONE option at a time
        # verbosity = st.radio(
        #     "How do you prefer your answers?",
        #     ["Brief (recommended)", "Detailed", "Step by step"],
        #     index=0
        # )
        
        #st.divider()
        # Image counter (query only, no modification)
        #st.header("🎨 Image generation")
        
        # try:
        #     repo = ImageUsageRepository()
        #     remaining = repo.get_remaining(client_ip)
            
        #     col1, col2 = st.columns(2)
        #     with col1:
        #         st.metric(
        #             "Available today",
        #             f"{remaining}/5",
        #             help="Maximum 5 images per day"
        #         )
        #     with col2:
        #         if remaining == 0:
        #             st.error("🚫 Limit reached")
        #         elif remaining < 3:
        #             st.warning("⚠️ Few available")
        #         else:
        #             st.success("✅ You can generate")
        # except Exception as e:
        #     st.caption("Image counter not available")
        #     logger.error(f"Error loading image counter: {e}")
        
        st.divider()
        
        # Session information
        st.header("📋 Current session")
        stats = orchestrator.get_session_stats(client_ip)
        #st.caption(f"Messages: {stats.get('message_count', 0)}")
        #st.caption(f"IP: {client_ip[:15]}..." if len(client_ip) > 15 else f"IP: {client_ip}")
        
        # Help button
        with st.expander("❓ How to use this assistant?"):
            st.markdown("""
            1. Write your question in the text field
            2. Press Enter or click send
            3. Wait for a clear and direct answer
            
            **You can ask about:**
            - Games, Toys
            - Planets
            - Pets
            
            **For images:**
            - "generate an image of..."
            - "draw..."
            - "create an image..."
            """)
    
    # Initialize history in RAM
    if "tea_messages" not in st.session_state:
        st.session_state.tea_messages = []
    
    # Show history (SIMPLE, no complex avatars)
    for msg in st.session_state.tea_messages:
        with st.chat_message(msg["role"]):
            if msg.get("type") == "image":
                # Show image
                if "image_data" in msg:
                    images_out = base64.b64decode(msg["image_data"])
                    st.image(images_out, width=200)
                if "prompt" in msg:
                    st.caption(f"📝 Prompt: {msg['prompt']}")
                if "content" in msg:
                    st.success(msg["content"])
            else:
                # Text message
                st.markdown(msg["content"])
    
    # User input (CLEAR)
    prompt = st.chat_input(
        "Write your message here...",
        max_chars=500,
        key="tea_chat_input"
    )
    
    if prompt:
        # Show user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Save to history
        st.session_state.tea_messages.append({
            "role": "user",
            "content": prompt,
            "type": "text"
        })
        
        # Process with orchestrator
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    # Execute agent
                    response = orchestrator.handle_message(prompt, client_ip)
                    
                    # Check if it's an image response
                    response_text = response.get("response", "")
                    
                    try:
                        # Try to parse as JSON (image)
                        img_data = json.loads(response_text)
                        if img_data.get("success"):
                            # Show image
                            images_out = base64.b64decode(img_data["image_data"])
                            st.image(images_out, use_container_width=True)
                            st.caption(f"📝 Enhanced prompt: {img_data.get('enhanced_prompt', '')}")
                            st.success(img_data.get("message", "✅ Image generated"))
                           
                            # Save to history
                            st.session_state.tea_messages.append({
                                "role": "assistant",
                                "type": "image",
                                "content": img_data.get("message", ""),
                                "image_data": img_data["image_data"],
                                "prompt": img_data.get("enhanced_prompt", "")
                            })
                        else:
                            # Generation error
                            error_msg = img_data.get("message", "Error generating image")
                            st.error(error_msg)
                            st.session_state.tea_messages.append({
                                "role": "assistant",
                                "content": error_msg,
                                "type": "error"
                            })
                    except json.JSONDecodeError:
                        # It's a normal text response
                        st.markdown(response_text)
                        st.session_state.tea_messages.append({
                            "role": "assistant",
                            "content": response_text,
                            "type": "text"
                        })
                        
                        # Show used tool if exists
                        if response.get("tool_used"):
                            st.caption(f"🔧 Using: {response['tool_used']}")
                            
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Error in chat interface: {e}", exc_info=True)
                    st.session_state.tea_messages.append({
                        "role": "assistant",
                        "content": "Sorry, an error occurred. Please try again.",
                        "type": "error"
                    })
    
    # NEW CONVERSATION button (clear)
    if st.session_state.tea_messages:
        st.divider()
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🗑️ New conversation", use_container_width=True, type="primary"):
                st.session_state.tea_messages = []
                orchestrator.reset_session(client_ip)
                st.rerun()