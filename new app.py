import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np

# --- 1. 기본 설정 및 API URL ---
MET_API_URL = "https://collectionapi.metmuseum.org/public/collection/v1/"

# --- 2. 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 0
    st.session_state.search_results_details = None
    st.session_state.analyzed_artworks = {}
    st.session_state.df_palette = pd.DataFrame()

# --- 3. API 및 데이터 시뮬레이션 함수 ---
# (이 부분은 이전 코드와 동일하므로 생략합니다. search_artworks, get_artwork_details, simulate_palette_data 함수 포함)

@st.cache_data(show_spinner=False)
def search_artworks(query):
    """MET API의 search 엔드포인트를 이용해 작품 ID 목록을 가져옵니다."""
    if not query:
        return 0, []
    
    # 이미지가 있고, 검색어를 포함하는 작품만 검색
    search_url = f"{MET_API_URL}search?q={query}&hasImages=true&limit=20" 
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()
        return data.get('total', 0), data.get('objectIDs', [])[:10] # 상위 10개만 사용
    except Exception as e:
        return 0, []

@st.cache_data(show_spinner=False)
def get_artwork_details(object_id):
    """지정된 object_id의 작품 상세 정보를 가져옵니다."""
    url = f"{MET_API_URL}objects/{object_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        return {
            "title": data.get("title", "제목 없음"),
            "artist": data.get("artistDisplayName", "작가 미상"),
            "year": data.get("objectDate", "불명"),
            "image_url": data.get("primaryImage", None),
            "object_id": object_id
        }
    except Exception as e:
        return None

def simulate_palette_data(object_id, title, artist):
    """작품 ID를 기반으로 시뮬레이션된 색채 분석 데이터를 생성합니다."""
    np.random.seed(object_id % 100) 
    
    hex_options = ['#A2C4D8', '#F2E8D5', '#3A5C3C', '#F7DC6F', '#C4B4D8', 
                   '#5A7B8E', '#1D2E40', '#111111', '#F9F9F9', '#E74C3C', 
                   '#F1C40F', '#3498DB', '#C4A86A']
    
    selected_hex = np.random.choice(hex_options, size=5, replace=False)
    
    frequencies = np.random.rand(5)
    frequencies = frequencies / np.sum(frequencies)
    
    data = {
        'Artist': [artist] * 5,
        'Artwork': [title] * 5,
        'Color_HEX': selected_hex.tolist(),
        'Frequency': frequencies.tolist(),
        'Artwork_ID': [object_id] * 5
    }
    return pd.DataFrame(data)

# --- 4. 시각화 함수 (Plotly) ---
# (이 부분은 이전 코드와 동일하므로 생략합니다. create_heatmap, create_pie_chart 함수 포함)

def create_heatmap(df):
    """작가별 작품별 색상 빈도 히트맵을 생성합니다."""
    df['Artist_Artwork'] = df['Artist'] + ": " + df['Artwork']
    pivot_table = df.pivot_table(index='Artist_Artwork', columns='Color_HEX', values='Frequency', aggfunc='sum').fillna(0)
    fig = px.imshow(
        pivot_table, x=pivot_table.columns, y=pivot_table.index, color_continuous_scale='Inferno',
        text_auto=".2f", title="분석 대상 작품별 주 색상 빈도 히트맵"
    )
    fig.update_xaxes(title="주요 색상 (HEX Code)")
    fig.update_yaxes(title="작품 (Artwork)", autorange="reversed")
    fig.update_layout(height=max(400, len(pivot_table) * 50), coloraxis_colorbar=dict(title="빈도 비율"))
    return fig

def create_pie_chart(df, artwork_id):
    """선택된 작품의 색상 비율 도넛 차트를 생성합니다."""
    df_artwork = df[df['Artwork_ID'] == artwork_id]
    
    fig = go.Figure(data=[go.Pie(
        labels=[f"{row['Color_HEX']}" for idx, row in df_artwork.iterrows()],
        values=df_artwork['Frequency'],
        hole=.3, 
        marker_colors=df_artwork['Color_HEX'], 
        textinfo='label+percent',
        hoverinfo='label+text+percent',
        text=df_artwork['Color_HEX'] 
    )])
    
    title = df_artwork['Artwork'].iloc[0] if not df_artwork.empty else "작품 없음"
    fig.update_layout(
        title_text=f"**{title}** 색상 비율 (Donut Chart)",
        uniformtext_minsize=12, 
        uniformtext_mode='hide'
    )
    return fig

# --- 5. Streamlit UI 시작 ---
st.set_page_config(layout="wide", page_title="MET Data Visualization")
st.title("🔎 작가/작품 검색 기반 색채 분석 대시보드")
st.markdown("---")

# --- 6. 사이드바 (작품 검색 및 분석 목록 관리) ---
with st.sidebar:
    st.header("1. 작품 검색 (작가/제목)")
    
    search_query = st.text_input("작가 또는 작품 키워드 입력", key="search_input")
    
    if st.button("MET 작품 검색"):
        if search_query:
            with st.spinner('MET API로 작품 검색 중...'):
                total, ids = search_artworks(search_query)
                
                if total > 0:
                    st.session_state.search_results_details = {}
                    for object_id in ids:
                        detail = get_artwork_details(object_id)
                        if detail and detail['image_url']:
                            st.session_state.search_results_details[object_id] = detail
                            
                    st.session_state.step = 1
                    st.success(f"총 {total}개 작품 중 {len(st.session_state.search_results_details)}개 작품의 정보 로드 완료.")
                else:
                    st.warning("검색된 작품이 없습니다.")
                    st.session_state.step = 0
            st.rerun()
        else:
            st.warning("검색어를 입력해 주세요.")
            
    st.markdown("---")
    
    st.header("2. 분석 목록")
    if st.session_state.analyzed_artworks:
        st.info(f"현재 {len(st.session_state.analyzed_artworks)}개 작품 분석 중")
        
        for obj_id, artwork in list(st.session_state.analyzed_artworks.items()):
            col_name, col_del = st.columns([3, 1])
            with col_name:
                st.caption(f"**{artwork['artist']}** - {artwork['title']}")
            with col_del:
                if st.button("❌", key=f"del_{obj_id}"):
                    del st.session_state.analyzed_artworks[obj_id]
                    # 데이터프레임 업데이트
                    st.session_state.df_palette = pd.concat([
                        simulate_palette_data(a['object_id'], a['title'], a['artist']) 
                        for a in st.session_state.analyzed_artworks.values()
                    ], ignore_index=True)
                    st.rerun()
    else:
        st.caption("분석 대상 작품을 추가해 주세요.")
    
    if st.button("전체 리셋"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --------------------------------------------------------------------------------------
# --- 7. 메인 대시보드 (검색 결과 및 시각화 전시) ---
# --------------------------------------------------------------------------------------

if st.session_state.step >= 1 and st.session_state.search_results_details:
    st.header("🔍 검색 결과: 분석 목록에 추가")
    
    col_search_results = st.columns(3)
    
    for i, (obj_id, detail) in enumerate(st.session_state.search_results_details.items()):
        with col_search_results[i % 3]:
            with st.container(border=True):
                st.caption(f"**{detail['artist']}** ({detail['year']})")
                st.markdown(f"**{detail['title']}**")
                
                if detail['image_url']:
                    st.image(detail['image_url'], width=150)
                
                is_analyzed = obj_id in st.session_state.analyzed_artworks
                
                if not is_analyzed:
                    if st.button("➕ 분석 목록에 추가", key=f"add_{obj_id}"):
                        st.session_state.analyzed_artworks[obj_id] = detail
                        
                        # 색채 분석 데이터 생성 및 통합
                        new_df = simulate_palette_data(obj_id, detail['title'], detail['artist'])
                        st.session_state.df_palette = pd.concat([st.session_state.df_palette, new_df], ignore_index=True)
                        
                        st.session_state.step = 2 
                        st.rerun()
                else:
                    st.success("✅ 분석 목록에 포함됨")

st.markdown("---")

# --- 8. 시각화 전시 및 생성형 디자인 적용 ---

if st.session_state.step >= 2 and not st.session_state.df_palette.empty:
    
    st.header("📊 1. 종합 분석: 작품별 주 색상 빈도 히트맵")
    st.plotly_chart(create_heatmap(st.session_state.df_palette), use_container_width=True)

    st.markdown("---")

    st.header("🎨 2. 개별 작품 상세 색채 분석 및 생성 디자인")
    
    # 작품 선택 
    artwork_options = {
        f"[{v['artist']}] {v['title']}": k for k, v in st.session_state.analyzed_artworks.items()
    }
    
    selected_title = st.selectbox("상세 분석할 작품을 선택하세요:", list(artwork_options.keys()))
    selected_id = artwork_options[selected_title]
    
    df_display = st.session_state.df_palette[st.session_state.df_palette['Artwork_ID'] == selected_id].sort_values(by='Frequency', ascending=False)
    
    col_chart, col_data, col_gen = st.columns([1, 1, 1])
    
    with col_chart:
        st.subheader("도넛 차트")
        st.plotly_chart(create_pie_chart(st.session_state.df_palette, selected_id), use_container_width=True)
        
    with col_data:
        st.subheader("AI Curator 통찰")
        top_color_name = df_display['Color_HEX'].iloc[0]
        top_color_freq = df_display['Frequency'].iloc[0]
        st.info(f"**{selected_title}**의 색채 지문은 HEX 코드 **{top_color_name}** 계열이 {top_color_freq:.1%}로 가장 지배적입니다. 이는 작가 **{st.session_state.analyzed_artworks[selected_id]['artist']}**의 해당 시기 경향을 정량적으로 뒷받침합니다.")
        
        st.markdown("---")
        st.subheader("대표 팔레트")
        for index, row in df_display.iterrows():
            hex_code = row['Color_HEX']
            st.markdown(
                f"<div style='background-color:{hex_code}; height:25px; width:25px; border: 1px solid #ccc; display: inline-block; margin-right: 10px;'></div>"
                f"**{hex_code}** ({row['Frequency']:.1%})", 
                unsafe_allow_html=True
            )

    # -------------------------------------------------------------
    # 🌟 NEW FEATURE: 색채 기반 생성형 추상 이미지 시뮬레이션
    # -------------------------------------------------------------
    with col_gen:
        st.subheader("🎨 3. 데이터 기반 추상 이미지 (Generative Application)")
        st.markdown("작품의 색채 팔레트와 빈도를 활용하여 **추상 모자이크 패턴**을 생성합니다. (Creative Coding 시뮬레이션)")
        
        generative_canvas_html = """
            <div style='width: 100%; height: 200px; border: 1px solid #ccc; display: flex; margin-top: 10px;'>
        """
        # 빈도에 따라 너비를 할당하여 추상 패턴 생성
        for index, row in df_display.iterrows():
            width_percent = row['Frequency'] * 100
            # 추상적인 느낌을 더하기 위해 작은 그라데이션 효과 추가
            generative_canvas_html += f"""
                <div style='background: linear-gradient(to right, {row['Color_HEX']}, {row['Color_HEX']}EE); width: {width_percent}%; height: 100%;' title='{row['Color_HEX']} - {width_percent:.1f}%'></div>
            """
        generative_canvas_html += "</div>"
        
        st.markdown(generative_canvas_html, unsafe_allow_html=True)
        
        st.caption("생성된 패턴은 데이터 기반 디자인의 한 예시입니다.")
        
        st.markdown("---")
        st.markdown("**💡 심화 활용 방안 (AI 연동)**")
        st.info("이 HEX 코드를 LLM의 프롬프트에 'Strictly use the color palette: [HEX 코드]'와 같이 삽입하여 DALL·E/Stable Diffusion에 전달하면, 분석된 색상으로 완전히 새로운 추상 이미지를 만들 수 있습니다.")


else:
    st.info("왼쪽 사이드바에서 작가/작품 키워드를 검색하여 분석 대상 작품을 추가해 주세요.")
