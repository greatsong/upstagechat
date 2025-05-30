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

# ─── 문서 파싱 페이지 ───────────────────────────────────────────────────────────
if page == "문서 파싱":
    st.header("📄 문서 파싱 (Document Parsing)")
    uploaded = st.file_uploader("PDF/이미지 파일 업로드", type=["pdf","png","jpg","jpeg"])
    if uploaded:
        st.write(f"파일명: {uploaded.name}")
        
        # base64_encoding 테스트 옵션
        st.subheader("🧪 base64_encoding 형식 테스트")
        test_option = st.selectbox(
            "테스트할 형식 선택",
            [
                "형식1: API 문서 예제와 동일 (작은따옴표)",
                "형식2: 빈 배열",
                "형식3: 파라미터 제외",
                "형식4: JSON dumps 사용",
                "형식5: 단일 값 (배열 아님)",
                "형식6: 쉼표 구분 문자열"
            ]
        )
        
        # 파일 읽기
        file_bytes = uploaded.read()
        uploaded.seek(0)  # 파일 포인터 리셋
        
        # 기본 데이터
        base_data = {
            "ocr": "auto",
            "model": "document-parse"
        }
        
        # 테스트별 설정
        if test_option == "형식1: API 문서 예제와 동일 (작은따옴표)":
            base_data["base64_encoding"] = "['table']"  # API 문서 예제와 정확히 동일
            
        elif test_option == "형식2: 빈 배열":
            base_data["base64_encoding"] = "[]"
            
        elif test_option == "형식3: 파라미터 제외":
            # base64_encoding을 아예 포함하지 않음
            pass
            
        elif test_option == "형식4: JSON dumps 사용":
            base_data["base64_encoding"] = json.dumps(["table"])
            
        elif test_option == "형식5: 단일 값 (배열 아님)":
            base_data["base64_encoding"] = "table"
            
        elif test_option == "형식6: 쉼표 구분 문자열":
            base_data["base64_encoding"] = "text,table"
        
        # 현재 설정 표시
        st.info(f"현재 data 파라미터: {base_data}")
        
        if st.button("파싱 실행"):
            with st.spinner("파싱 중..."):
                files = {"document": (uploaded.name, file_bytes, uploaded.type)}
                resp = requests.post(
                    f"{base_url}/document-digitization", 
                    headers=headers, 
                    files=files, 
                    data=base_data
                )
            
            if resp.ok:
                result = resp.json()
                st.success("✅ 파싱 성공!")
                
                # 결과 요약
                if "elements" in result:
                    st.metric("추출된 요소 수", len(result["elements"]))
                
                # base64 인코딩된 데이터 확인
                has_base64 = False
                for elem in result.get("elements", []):
                    if elem.get("base64_encoding"):
                        has_base64 = True
                        break
                
                if has_base64:
                    st.info("✅ base64_encoding 데이터가 포함되어 있습니다.")
                else:
                    st.warning("⚠️ base64_encoding 데이터가 없습니다.")
                
                # 전체 결과 표시
                st.json(result)
            else:
                st.error(f"❌ 파싱 실패: {resp.status_code}")
                st.error(f"오류 메시지: {resp.text}")
                
                # 디버깅 정보
                with st.expander("🐛 디버깅 정보"):
                    st.write("**요청 정보:**")
                    st.write(f"- URL: {base_url}/document-digitization")
                    st.write(f"- Headers: {headers}")
                    st.write(f"- Data: {base_data}")
                    st.write(f"- File: {uploaded.name} ({uploaded.type})")

# ─── OCR 페이지는 그대로 유지 ─────────────────────────────────────────────────
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
                
                # HTML 콘텐츠에서 텍스트 추출
                html_content = result.get("content", {}).get("html", "")
                text_content = result.get("content", {}).get("text", "")
                
                # text가 비어있으면 HTML에서 추출
                if not text_content and html_content:
                    import re
                    text_content = html_content.replace('<br>', '\n').replace('<br/>', '\n')
                    text_content = re.sub('<[^<]+?>', '', text_content)
                    text_content = re.sub(r'[ \t]+', ' ', text_content).strip()
                
                # 코드 블록으로 표시 (복사 버튼 자동 제공)
                st.code(text_content, language=None)
                
                # 텍스트 파일로 다운로드
                st.download_button(
                    label="💾 텍스트 파일로 다운로드",
                    data=text_content,
                    file_name=f"{uploaded.name.split('.')[0]}_ocr.txt",
                    mime="text/plain"
                )
            else:
                st.error(f"OCR 실패: {resp.status_code} - {resp.text}")
