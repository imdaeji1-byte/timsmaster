import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. 기본 페이지 설정
st.set_page_config(page_title="TimeMaster - 학교 시간표 및 결보강 관리", layout="wide")

# 2. 세션 상태(데이터) 초기화
if "school_name" not in st.session_state:
    st.session_state.school_name = "OO고등학교"
if "hourly_rate" not in st.session_state:
    st.session_state.hourly_rate = 13000
if "schedule_df" not in st.session_state:
    st.session_state.schedule_df = None
if "sub_logs" not in st.session_state:
    st.session_state.sub_logs = []  # 대강 이력 데이터

# 3. 사이드바 - 학교 설정 및 뷰 선택
st.sidebar.title(f"🏫 {st.session_state.school_name}")

# 비밀번호 기반 모드 전환
mode = st.sidebar.radio("접속 모드 선택", ["학생 전용 (읽기 전용)", "교사/관리자 모드"])

if mode == "교사/관리자 모드":
    pin = st.sidebar.text_input("관리자 비밀번호 입력", type="password")
    if pin != "1234":  # 초기 기본 비밀번호
        st.sidebar.warning("비밀번호(1234)를 입력해야 관리 기능이 활성화됩니다.")
        mode = "학생 전용 (읽기 전용)"

# 4. 헤더
st.title(f"📅 {st.session_state.school_name} 시간표 & 결보강 관리 시스템")

# 5. 기초 엑셀 파일 업로드 (관리자 전용)
if mode == "교사/관리자 모드":
    with st.expander("📁 기초 시간표 엑셀 업로드 및 설정", expanded=(st.session_state.schedule_df is None)):
        col_school, col_rate = st.columns(2)
        with col_school:
            new_school = st.text_input("학교명 설정", value=st.session_state.school_name)
            if new_school != st.session_state.school_name:
                st.session_state.school_name = new_school
                st.rerun()
        with col_rate:
            new_rate = st.number_input("시간당 대강비 단가(원)", value=st.session_state.hourly_rate, step=1000)
            st.session_state.hourly_rate = new_rate

        uploaded_file = st.file_uploader("기초 시간표 엑셀/CSV 파일 선택", type=["xlsx", "csv"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.session_state.schedule_df = df
                st.success("시간표 데이터가 성공적으로 로드되었습니다!")
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

# 6. 샘플 데이터 세팅 (업로드된 파일이 없을 경우 테스트용)
if st.session_state.schedule_df is None:
    st.info("💡 업로드된 파일이 없어 샘플 시간표 데이터로 구동 중입니다.")
    sample_data = {
        "학급": ["1-1", "1-1", "1-2", "1-2"],
        "요일": ["월", "월", "월", "월"],
        "교시": [1, 2, 1, 2],
        "과목": ["수학", "영어", "국어", "수학"],
        "교사": ["김철수", "이영희", "박민수", "김철수"]
    }
    st.session_state.schedule_df = pd.DataFrame(sample_data)

df = st.session_state.schedule_df

# 7. 화면 메인 탭 구동
if mode == "학생 전용 (읽기 전용)":
    st.subheader("🎓 학생용 학급별 시간표 조회")
    classes = sorted(df["학급"].unique().tolist())
    selected_class = st.selectbox("반을 선택하세요", classes)
    
    class_df = df[df["학급"] == selected_class]
    st.dataframe(class_df[["요일", "교시", "과목", "교사"]], use_container_width=True)

else:
    # 관리자/교사 모드 탭
    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ 전체/반/교사 시간표", "✏️ 대강 지정 및 사유 기록", "📊 교사별 주당 시수", "💰 대강일지 & 수당 집계"])

    with tab1:
        view_type = st.radio("보기 방식", ["전체 시간표", "학급별 조회", "교사별 조회"], horizontal=True)
        if view_type == "전체 시간표":
            st.dataframe(df, use_container_width=True)
        elif view_type == "학급별 조회":
            c_target = st.selectbox("학급 선택", sorted(df["학급"].unique()))
            st.dataframe(df[df["학급"] == c_target], use_container_width=True)
        elif view_type == "교사별 조회":
            t_target = st.selectbox("교사 선택", sorted(df["교사"].unique()))
            st.dataframe(df[df["교사"] == t_target], use_container_width=True)

    with tab2:
        st.subheader("📝 대강 처리 (원교사 ➔ 대강교사)")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            sub_date = st.date_input("대강 날짜", date.today())
            orig_teacher = st.selectbox("원래 담당 교사", sorted(df["교사"].unique()))
        with col_b:
            sub_period = st.number_input("교시", min_value=1, max_value=7, value=1)
            target_class = st.selectbox("대상 학급", sorted(df["학급"].unique()))
        with col_c:
            sub_teacher = st.selectbox("대강 교사", sorted(df["교사"].unique()))
            reason = st.text_input("대강 사유 (필수)", placeholder="예: 출장, 병가, 공결 등")

        if st.button("대강 내역 저장"):
            if not reason:
                st.error("대강 사유를 반드시 입력해야 합니다.")
            else:
                log_entry = {
                    "날짜": str(sub_date),
                    "교시": f"{sub_period}교시",
                    "학급": target_class,
                    "원교사": orig_teacher,
                    "대강교사": sub_teacher,
                    "대강사유": reason,
                    "단가": st.session_state.hourly_rate
                }
                st.session_state.sub_logs.append(log_entry)
                st.success(f"{orig_teacher} ➔ {sub_teacher} 대강 처리가 완료되었습니다.")

    with tab3:
        st.subheader("📈 교사별 주당 수업 시수 통계")
        teacher_counts = df["교사"].value_counts().reset_index()
        teacher_counts.columns = ["교사명", "주당 수업 시수"]
        st.dataframe(teacher_counts, use_container_width=True)

    with tab4:
        st.subheader("📋 대강일지 및 수당 집계표 (기안 결재용)")
        if len(st.session_state.sub_logs) == 0:
            st.info("기록된 대강 내역이 없습니다.")
        else:
            log_df = pd.DataFrame(st.session_state.sub_logs)
            st.markdown("##### [ 대강 상세 일지 ]")
            st.dataframe(log_df, use_container_width=True)

            # 교사별 수당 집계
            summary = log_df.groupby("대강교사").agg(
                총시수=("교시", "count"),
                사유요약=("대강사유", lambda x: ", ".join(x.unique()))
            ).reset_index()
            summary["시간당단가"] = st.session_state.hourly_rate
            summary["총지급금액"] = summary["총시수"] * summary["시간당단가"]

            st.markdown("##### [ 교사별 대강 수당 집계표 ]")
            st.dataframe(summary, use_container_width=True)

            # 엑셀 다운로드 버튼
            @st.cache_data
            def convert_df(df_to_export):
                return df_to_export.to_csv(index=False).encode('utf-8-sig')

            csv_data = convert_df(log_df)
            st.download_button(
                label="📥 대강일지 엑셀(CSV) 다운로드",
                data=csv_data,
                file_name=f"{st.session_state.school_name}_대강일지_{date.today()}.csv",
                mime="text/csv",
            )