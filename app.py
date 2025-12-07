import streamlit as st
from openai import OpenAI
import requests
from io import BytesIO

# --- 1. API 클라이언트 초기화 ---
# 🔑 Streamlit Cloud Secrets에서 API Key를 안전하게 불러옵니다.
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except KeyError:
    st.error("오류: OpenAI API Key가 Streamlit Secrets에 설정되지 않았습니다. 대시보드에서 설정해주세요.")
    st.stop()
except Exception:
    # 로컬 테스트 환경 등 예외 처리
    client = None

# --- 2. 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 0
    st.session_state.start_text = None
    st.session_state.image_url = None
    st.session_state.final_text = None
    st.session_state.user_topic = ""
    st.session_state.start_role = "AI 시인"


# --- 3. 핵심 변환 함수 ---

@st.cache_data(show_spinner="1단계: AI 시인 역할로 시작 텍스트 생성 중...")
def generate_start_text(topic, role):
    """LLM을 이용해 시적인 시작 텍스트를 생성합니다 (Step 1)."""
    system_prompt = f"당신은 '{role}' 역할입니다. 주어진 주제에 대해 50자 내외의 시적인 구절이나 짧은 스토리를 생성하세요. 창의적이고 감성적인 표현을 사용해야 합니다."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 비용 효율을 위해 mini 사용
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"주제: {topic}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"텍스트 생성 오류: {e}"

@st.cache_data(show_spinner="2단계: DALL·E 모델로 이미지 생성 중...")
def generate_image_from_text(prompt):
    """DALL·E 3를 이용해 텍스트 기반 이미지를 생성합니다 (Step 2)."""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        # 생성된 이미지 URL 반환 (임시 URL)
        return response.data[0].url
    except Exception as e:
        return f"이미지 생성 오류: {e}"

@st.cache_data(show_spinner="3단계: 최종 텍스트(묘사) 역변환 중...")
def analyze_image_to_text(image_url):
    """멀티모달 LLM을 이용해 이미지를 분석하고 묘사 텍스트를 생성합니다 (Step 3)."""
    # Vision 기능을 활용하여 이미지 URL을 직접 입력합니다.
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "당신은 전문 예술 비평가입니다. 이 이미지를 보고 느낀 것을 100자 이내로 자세하게 묘사하고 분석해 주세요. 색상, 구도, 분위기를 명확히 언급해야 합니다."},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"이미지 분석 오류: {e}"

# --- 4. Streamlit UI 시작 ---
st.set_page_config(layout="wide", page_title="AI 변환 사슬")
st.title("🔗 AI 변환 사슬: 전달 왜곡 분석")
st.markdown("텍스트 $\\rightarrow$ 이미지 $\\rightarrow$ 텍스트 변환 사슬을 통해 AI 모델 간의 **정보 전달 왜곡**을 탐구합니다.")
st.markdown("---")

# --- 5. 사이드바: 입력 및 설정 ---
with st.sidebar:
    st.header("입력 및 설정")
    
    st.session_state.user_topic = st.text_input("주제 키워드 입력", "미래 도시의 고독", key="topic_input")
    st.session_state.start_role = st.selectbox("LLM 역할 부여", ["AI 시인", "AI 스토리텔러", "AI 철학자"], key="role_select")

    if st.button("워크플로우 시작 (Step 1부터 실행)"):
        # 상태 리셋 및 1단계 시작
        st.session_state.step = 1
        st.session_state.start_text = None
        st.session_state.image_url = None
        st.session_state.final_text = None
        
    if st.session_state.step > 0 and st.button("전체 리셋"):
        for key in list(st.session_state.keys()):
            if key not in ['user_topic', 'start_role']: # 입력값은 유지
                del st.session_state[key]
        st.rerun() # 👈 st.experimental_rerun() -> st.rerun() 수정 완료

# --------------------------------------------------------------------------------------
# --- 6. 단계별 워크플로우 실행 ---
# --------------------------------------------------------------------------------------
# 3단 구성 준비
col1, col2, col3 = st.columns(3)

# Step 1: 시작 텍스트 생성
with col1:
    st.header("1. 시작 텍스트")
    if st.session_state.step == 1:
        st.session_state.start_text = generate_start_text(st.session_state.user_topic, st.session_state.start_role)
        st.session_state.step = 2
        st.rerun() # 👈 st.experimental_rerun() -> st.rerun() 수정 완료
        
    if st.session_state.start_text:
        st.markdown(f"**역할:** {st.session_state.start_role}")
        st.info(st.session_state.start_text)
        if st.session_state.step == 2 and st.button("Step 2 실행: 이미지 생성", key="btn_step2"):
            st.session_state.step = 3
            st.rerun() # 👈 st.experimental_rerun() -> st.rerun() 수정 완료

# Step 2: 이미지 생성 및 전시
with col2:
    st.header("2. 중간 이미지")
    if st.session_state.step == 3:
        st.session_state.image_url = generate_image_from_text(st.session_state.start_text)
        if st.session_state.image_url and not st.session_state.image_url.startswith("이미지 생성 오류"):
            st.session_state.step = 4
        else:
             st.session_state.step = 99 # 오류 상태
        st.rerun() # 👈 st.experimental_rerun() -> st.rerun() 수정 완료
        
    if st.session_state.image_url:
        st.markdown(f"**프롬프트:** `{st.session_state.start_text}`")
        if st.session_state.image_url.startswith("이미지 생성 오류"):
             st.error(st.session_state.image_url)
        else:
            # 외부 URL 이미지 로드 (DALL·E는 URL 반환)
            try:
                st.image(st.session_state.image_url, caption="DALL·E 3 생성 이미지", use_column_width=True)
                if st.session_state.step == 4 and st.button("Step 3 실행: 역변환 텍스트 분석", key="btn_step3"):
                    st.session_state.step = 5
                    st.rerun() # 👈 st.experimental_rerun() -> st.rerun() 수정 완료
            except Exception as e:
                st.error(f"이미지 표시 오류: {e}")

# Step 3 & 4: 최종 텍스트 생성 및 비교
with col3:
    st.header("3. 최종 텍스트 (역변환)")
    if st.session_state.step == 5:
        st.session_state.final_text = analyze_image_to_text(st.session_state.image_url)
        st.session_state.step = 6
        st.rerun() # 👈 st.experimental_rerun() -> st.rerun() 수정 완료
        
    if st.session_state.final_text:
        st.info(st.session_state.final_text)
        st.markdown("---")
        st.header("4. 결과 분석 및 왜곡 시각화")
        
        # 간단한 길이 비교 시각화 (왜곡 시각화 예시)
        len_start = len(st.session_state.start_text)
        len_final = len(st.session_state.final_text)
        
        st.markdown(f"**시작 텍스트 길이:** {len_start}자")
        st.markdown(f"**최종 텍스트 길이:** {len_final}자")
        st.warning("*(LLM이 시각 정보를 묘사하며 원본 정보가 손실되거나 새로운 정보가 추가되는 '전달 왜곡' 현상 발생)*")
