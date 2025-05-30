import streamlit as st
import requests
import json

# 페이지 구성 및 API 설정
st.set_page_config(page_title="📄 Upstage Multi-Tool", layout="wide")
api_key = st.secrets["upstage_api_key"]
base_url = "https://api.upstage.ai/v1"

# 사이드바 네비게이션
st.sidebar.title("🔧 기능 선택")
page = st.sidebar.radio("페이지 선택", ["문서 파싱", "OCR", "정보 추출"])

# 공통 헤더
headers = {"Authorization": f"Bearer {api_key}"}

# ─── 정보 추출 페이지 ─────────────────────────────────────────────────────────────
if page == "정보 추출":
    st.header("🔎 정보 추출 (Information Extraction)")
    
    # 샘플 텍스트
    sample_text = """John Doe is a 35-year-old software engineer working at TechCorp Inc. 
He can be reached at john.doe@techcorp.com or +1-555-123-4567. 
His office is located at 123 Tech Street, San Francisco, CA 94105."""
    
    # 텍스트 입력
    text_input = st.text_area(
        "추출할 텍스트 입력", 
        value="",
        height=200,
        placeholder=sample_text,
        help="이름, 이메일, 전화번호, 주소 등의 정보가 포함된 텍스트를 입력하세요."
    )
    
    # 샘플 텍스트 사용 버튼
    if st.button("샘플 텍스트 사용"):
        text_input = sample_text
        st.rerun()
    
    # API 엔드포인트 선택 (테스트용)
    endpoint_option = st.selectbox(
        "API 엔드포인트 (디버깅용)",
        [
            "/information-extraction/universal",
            "/information-extraction",
            "/extraction/universal",
            "/universal-extraction"
        ]
    )
    
    # 모델 선택
    model_option = st.selectbox(
        "모델 선택",
        ["universal", "information-extraction", "universal-extraction"]
    )
    
    if st.button("정보 추출 실행", type="primary", disabled=not text_input):
        # 요청 데이터 준비
        payload = {
            "model": model_option,
            "text": text_input
        }
        
        # 현재 설정 표시
        with st.expander("📋 요청 정보"):
            st.write(f"**URL:** {base_url}{endpoint_option}")
            st.write("**Headers:**")
            st.json({**headers, "Content-Type": "application/json"})
            st.write("**Payload:**")
            st.json(payload)
        
        with st.spinner("정보 추출 중..."):
            try:
                # POST 요청
                resp = requests.post(
                    f"{base_url}{endpoint_option}",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30
                )
                
                # 응답 처리
                if resp.ok:
                    result = resp.json()
                    st.success("✅ 추출 완료!")
                    
                    # 결과 표시
                    if isinstance(result, dict):
                        # 추출된 엔티티 표시
                        if "entities" in result:
                            st.subheader("📊 추출된 정보")
                            entities = result["entities"]
                            
                            # 엔티티 타입별로 그룹화
                            entity_types = {}
                            for entity in entities:
                                etype = entity.get("type", "Unknown")
                                if etype not in entity_types:
                                    entity_types[etype] = []
                                entity_types[etype].append(entity)
                            
                            # 타입별로 표시
                            for etype, items in entity_types.items():
                                with st.expander(f"{etype} ({len(items)}개)"):
                                    for item in items:
                                        col1, col2 = st.columns([1, 3])
                                        with col1:
                                            st.write("**값:**")
                                        with col2:
                                            st.write(item.get("value", ""))
                                        if "confidence" in item:
                                            st.progress(item["confidence"])
                                            st.caption(f"신뢰도: {item['confidence']:.2%}")
                                        st.divider()
                        
                        # 전체 응답 표시
                        with st.expander("🔍 전체 응답 데이터"):
                            st.json(result)
                    else:
                        st.warning("예상과 다른 응답 형식입니다.")
                        st.json(result)
                        
                else:
                    st.error(f"❌ 추출 실패: {resp.status_code}")
                    
                    # 에러 상세 정보
                    try:
                        error_data = resp.json()
                        st.error(f"에러 메시지: {error_data}")
                        
                        # 에러 코드별 해결책
                        if resp.status_code == 404:
                            st.info("""
                            💡 **404 에러 해결 방법:**
                            1. 다른 API 엔드포인트를 선택해보세요
                            2. API 문서를 확인하여 정확한 엔드포인트를 확인하세요
                            3. 모델 이름이 올바른지 확인하세요
                            """)
                        elif resp.status_code == 400:
                            st.info("""
                            💡 **400 에러 해결 방법:**
                            1. 텍스트가 비어있지 않은지 확인하세요
                            2. 모델 이름이 올바른지 확인하세요
                            3. 텍스트에 특수문자가 있다면 제거해보세요
                            """)
                        elif resp.status_code == 401:
                            st.info("""
                            💡 **401 에러 해결 방법:**
                            1. API 키가 올바른지 확인하세요
                            2. API 키가 만료되지 않았는지 확인하세요
                            """)
                            
                    except:
                        st.error(f"에러 응답: {resp.text}")
                    
                    # 디버깅 정보
                    with st.expander("🐛 디버깅 정보"):
                        st.write("**요청 URL:**", f"{base_url}{endpoint_option}")
                        st.write("**요청 헤더:**")
                        st.code(json.dumps(dict(resp.request.headers), indent=2))
                        st.write("**요청 본문:**")
                        st.code(resp.request.body)
                        st.write("**응답 헤더:**")
                        st.code(json.dumps(dict(resp.headers), indent=2))
                        
            except requests.exceptions.Timeout:
                st.error("⏱️ 요청 시간이 초과되었습니다. 다시 시도해주세요.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 서버에 연결할 수 없습니다. 인터넷 연결을 확인해주세요.")
            except Exception as e:
                st.error(f"❌ 예상치 못한 오류: {str(e)}")
                st.exception(e)

# ─── 문서 파싱 페이지 (기존 코드) ─────────────────────────────────────────────
elif page == "문서 파싱":
    st.header("📄 문서 파싱 (Document Parsing)")
    uploaded = st.file_uploader("PDF/이미지 파일 업로드", type=["pdf","png","jpg","jpeg"])
    
    if uploaded:
        st.write(f"파일명: {uploaded.name}")
        
        # base64_encoding 옵션
        encode_option = st.selectbox(
            "Base64 인코딩 옵션",
            ["없음", "테이블만", "텍스트만", "텍스트와 테이블"]
        )
        
        data = {
            "ocr": "auto",
            "model": "document-parse"
        }
        
        # base64_encoding 설정
        if encode_option == "텍스트만":
            data["base64_encoding"] = '["text"]'
        elif encode_option == "테이블만":
            data["base64_encoding"] = '["table"]'
        elif encode_option == "텍스트와 테이블":
            data["base64_encoding"] = '["text","table"]'
        
        if st.button("파싱 실행"):
            with st.spinner("파싱 중..."):
                files = {"document": (uploaded.name, uploaded.read(), uploaded.type)}
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            
            if resp.ok:
                result = resp.json()
                st.success("✅ 파싱 성공!")
                st.json(result)
            else:
                st.error(f"파싱 실패: {resp.status_code} - {resp.text}")

# ─── OCR 페이지 (기존 코드) ─────────────────────────────────────────────────────
elif page == "OCR":
    st.header("🔍 OCR (Document OCR)")
    uploaded = st.file_uploader("PDF/이미지 파일 업로드", type=["pdf","png","jpg","jpeg"])
    if uploaded:
        st.write(f"파일명: {uploaded.name}")
        files = {"document": (uploaded.name, uploaded.read(), uploaded.type)}
        
        data = {
            "ocr": "force",
            "model": "document-parse"
        }
        
        if st.button("OCR 실행"):
            with st.spinner("OCR 처리 중..."):
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            if resp.ok:
                result = resp.json()
                st.success("OCR 완료!")
                
                html_content = result.get("content", {}).get("html", "")
                text_content = result.get("content", {}).get("text", "")
                
                if not text_content and html_content:
                    import re
                    text_content = html_content.replace('<br>', '\n').replace('<br/>', '\n')
                    text_content = re.sub('<[^<]+?>', '', text_content)
                    text_content = re.sub(r'[ \t]+', ' ', text_content).strip()
                
                st.code(text_content, language=None)
                
                st.download_button(
                    label="💾 텍스트 파일로 다운로드",
                    data=text_content,
                    file_name=f"{uploaded.name.split('.')[0]}_ocr.txt",
                    mime="text/plain"
                )
            else:
                st.error(f"OCR 실패: {resp.status_code} - {resp.text}")
