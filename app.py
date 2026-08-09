import streamlit as st
import pandas as pd
from datetime import date

# 1. 페이지 설정
st.set_page_config(page_title="TimeMaster - 학교 시간표 시스템", layout="wide")

# Custom CSS: 디자인, 색상 하이라이트, 인쇄 스타일
st.markdown("""
<style>
    @media print {
        header, footer, .stSidebar, .stButton, button, [data-testid="stHeader"] {
            display: none !important;
        }
        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        body { zoom: 85%; }
    }
    .timetable-poster {
        width: 100%;
        border-collapse: collapse;
        text-align: center;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 20px;
    }
    .timetable-poster th {
        background-color: #1e3a8a;
        color: #ffffff;
        padding: 12px;
        font-size: 15px;
        font-weight: 600;
        border: 1px solid #1e3a8a;
    }
    .timetable-poster td {
        border: 1px solid #e2e8f0;
        padding: 10px;
        height: 65px;
        width: 18%;
        vertical-align: middle;
    }
    .period-col {
        background-color: #f8fafc;
        font-weight: bold;
        color: #334155;
        width: 8% !important;
    }
    .subject-name {
        font-size: 15px;
        font-weight: bold;
        color: #0f172a;
    }
    .teacher-name {
        font-size: 12px;
        color: #64748b;
        margin-top: 2px;
    }
    .bg-swapped {
        background-color: #fef08a !important; /* 노란색 하이라이트 */
        border: 2px solid #eab308 !important;
    }
    .bg-substitute {
        background-color: #ffedd5 !important; /* 주황색 하이라이트 */
        border: 2px solid #f97316 !important;
    }
    .status-badge {
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 2px;
    }
    .badge-swap { background-color: #ca8a04; color: white; }
    .badge-sub { background-color: #ea580c; color: white; }
</style>
""", unsafe_allow_html=True)

# 2. 세션 상태 초기화
if "school_name" not in st.session_state:
    st.session_state.school_name = "경남해양고등학교"
if "hourly_rate" not in st.session_state:
    st.session_state.hourly_rate = 13000
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "sub_logs" not in st.session_state:
    st.session_state.sub_logs = []
if "swapped_indices" not in st.session_state:
    st.session_state.swapped_indices = set()

# 3. 사이드바
st.sidebar.title(f"🏫 {st.session_state.school_name}")
mode = st.sidebar.radio("접속 모드", ["학생/교사 시간표 보기", "관리자 모드 (수업교체/대강)"])

if mode == "관리자 모드 (수업교체/대강)":
    pin = st.sidebar.text_input("관리자 비밀번호", type="password")
    if pin != "1234":
        st.sidebar.warning("비밀번호(1234)를 입력하셔야 합니다.")
        mode = "학생/교사 시간표 보기"

# 4. 헤더
st.title(f"📅 {st.session_state.school_name} 시간표 관리 시스템")

# 5. 엑셀 파싱
if mode == "관리자 모드 (수업교체/대강)":
    with st.expander("📁 엑셀 파일 업로드 및 기본 설정", expanded=(st.session_state.raw_df is None)):
        col_s, col_r = st.columns(2)
        with col_s:
            ns = st.text_input("학교명 변경", value=st.session_state.school_name)
            if ns != st.session_state.school_name:
                st.session_state.school_name = ns
                st.rerun()
        with col_r:
            st.session_state.hourly_rate = st.number_input("대강비 단가(원)", value=st.session_state.hourly_rate, step=1000)

        up_file = st.file_uploader("전체 시간표 엑셀 파일(.xlsx) 업로드", type=["xlsx"])
        if up_file is not None:
            try:
                st.session_state.raw_df = pd.read_excel(up_file)
                st.success("시간표 업로드 완료!")
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")

def parse_excel_timetable(df_in):
    if df_in is None:
        return None, []
    
    df_proc = df_in.copy()
    parsed_rows = []
    current_day = "월"
    
    for r_idx in range(4, len(df_proc)):
        row = df_proc.iloc[r_idx]
        if pd.notna(row.iloc[0]):
            current_day = str(row.iloc[0]).strip()
            
        period = row.iloc[1]
        if pd.isna(period):
            continue
            
        col_idx = 2
        class_id = 1
        while col_idx + 1 < len(df_proc.columns):
            subj = str(row.iloc[col_idx]).strip() if pd.notna(row.iloc[col_idx]) else ""
            teacher = str(row.iloc[col_idx+1]).strip() if pd.notna(row.iloc[col_idx+1]) else ""
            
            c_name = f"학급_{class_id}"
            h_grade = str(df_proc.iloc[1, col_idx]) if pd.notna(df_proc.iloc[1, col_idx]) else ""
            h_dept = str(df_proc.iloc[2, col_idx]) if pd.notna(df_proc.iloc[2, col_idx]) else ""
            if h_grade and h_dept:
                c_name = f"{h_grade} {h_dept}".replace("\n", " ").strip()
            elif h_grade:
                c_name = f"{h_grade}_{class_id}"
            
            if subj and subj != "nan":
                parsed_rows.append({
                    "idx": len(parsed_rows),
                    "학급": c_name,
                    "요일": current_day,
                    "교시": int(period) if str(period).isdigit() else period,
                    "과목": subj,
                    "교사": teacher
                })
            col_idx += 2
            class_id += 1
            
    p_df = pd.DataFrame(parsed_rows)
    teachers = sorted(list(set(p_df["교사"].unique()) - {"", "nan"}))
    return p_df, teachers

if "parsed_df" not in st.session_state or st.session_state.raw_df is not None:
    p_df, t_list = parse_excel_timetable(st.session_state.raw_df)
    if p_df is not None:
        st.session_state.parsed_df = p_df
        st.session_state.t_list = t_list

parsed_df = st.session_state.get("parsed_df", None)
teacher_list = st.session_state.get("t_list", [])

def build_weekly_html_table(filtered_df, title_name):
    days = ["월", "화", "수", "목", "금"]
    periods = list(range(1, 8))
    
    html = f"<div style='text-align: center; margin-bottom: 10px;'><h2>🏫 {title_name} 주간 시간표</h2></div>"
    html += "<table class='timetable-poster'><thead><tr><th class='period-col'>교시</th>"
    for d in days:
        html += f"<th>{d}요일</th>"
    html += "</tr></thead><tbody>"
    
    sub_dict = {}
    for log in st.session_state.sub_logs:
        key = (log["학급"], log["요일"], int(str(log["교시"]).replace("교시","")))
        sub_dict[key] = log
    
    for p in periods:
        html += f"<tr><td class='period-col'>{p}교시</td>"
        for d in days:
            cell_data = filtered_df[(filtered_df["요일"] == d) & (filtered_df["교시"] == p)]
            if not cell_data.empty:
                row = cell_data.iloc[0]
                idx = row["idx"]
                subj = row["과목"]
                teacher = row["교사"]
                cls = row["학급"]
                
                cell_class = ""
                badge_html = ""
                
                sub_key = (cls, d, p)
                if sub_key in sub_dict:
                    cell_class = "bg-substitute"
                    badge_html = f"<span class='status-badge badge-sub'>대강 ({sub_dict[sub_key]['대강교사']})</span><br>"
                    teacher = f"<s>{teacher}</s> ➔ {sub_dict[sub_key]['대강교사']}"
                elif idx in st.session_state.swapped_indices:
                    cell_class = "bg-swapped"
                    badge_html = "<span class='status-badge badge-swap'>🔄 교체됨</span><br>"
                
                html += f"<td class='{cell_class}'>{badge_html}<div class='subject-name'>{subj}</div><div class='teacher-name'>{teacher}</div></td>"
            else:
                html += "<td>-</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

# 6. 메인 화면 탭
if parsed_df is not None and not parsed_df.empty:
    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ 시간표 조회 (반/교사/전체)", "🔄 수업 위치 맞교환", "📝 대강 지정 및 사유", "📊 교사 시수 & 수당"])

    with tab1:
        st.subheader("📌 주간 시간표 (교실/교무실 게시용)")
        c_v1, c_v2 = st.columns([3, 1])
        with c_v1:
            view_mode = st.radio("조회 모드", ["학급별 시간표 (가로:월~금 / 세로:1~7교시)", "교사별 시간표", "전체 시간표 (목록형)"], horizontal=True)
        with c_v2:
            st.write("")
            st.button("🖨️ 시간표 인쇄 / PDF 저장", on_click=lambda: st.components.v1.html("<script>window.print();</script>"))

        if view_mode == "학급별 시간표 (가로:월~금 / 세로:1~7교시)":
            target_cls = st.selectbox("🎯 학급 선택", sorted(parsed_df["학급"].unique()))
            filtered = parsed_df[parsed_df["학급"] == target_cls]
            st.markdown(build_weekly_html_table(filtered, target_cls), unsafe_allow_html=True)

        elif view_mode == "교사별 시간표":
            target_t = st.selectbox("👨‍🏫 교사 선택", teacher_list)
            filtered = parsed_df[parsed_df["교사"] == target_t]
            st.markdown(build_weekly_html_table(filtered, f"{target_t} 선생님"), unsafe_allow_html=True)

        else:
            st.markdown("##### [ 전체 학급 피벗 시간표 ]")
            parsed_df["과목교사"] = parsed_df["과목"] + " (" + parsed_df["교사"] + ")"
            pivot_all = parsed_df.pivot(index=["요일", "교시"], columns="학급", values="과목교사")
            st.dataframe(pivot_all, use_container_width=True, height=600)

    with tab2:
        st.subheader("🔄 수업 위치 맞교환 (1:1 교체)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 📍 첫 번째 수업 선택")
            cls1 = st.selectbox("학급 A", sorted(parsed_df["학급"].unique()), key="sw_c1")
            df1 = parsed_df[parsed_df["학급"] == cls1]
            idx1 = st.selectbox("수업 A 선택", df1.index, format_func=lambda x: f"{df1.loc[x, '요일']}요일 {df1.loc[x, '교시']}교시 - {df1.loc[x, '과목']}({df1.loc[x, '교사']})")

        with col2:
            st.markdown("##### 📍 두 번째 수업 선택")
            cls2 = st.selectbox("학급 B", sorted(parsed_df["학급"].unique()), key="sw_c2")
            df2 = parsed_df[parsed_df["학급"] == cls2]
            idx2 = st.selectbox("수업 B 선택", df2.index, format_func=lambda x: f"{df2.loc[x, '요일']}요일 {df2.loc[x, '교시']}교시 - {df2.loc[x, '과목']}({df2.loc[x, '교사']})")

        if st.button("🔄 두 수업 맞교환 및 노란색 하이라이트 적용"):
            s1, t1 = parsed_df.loc[idx1, "과목"], parsed_df.loc[idx1, "교사"]
            parsed_df.loc[idx1, "과목"], parsed_df.loc[idx1, "교사"] = parsed_df.loc[idx2, "과목"], parsed_df.loc[idx2, "교사"]
            parsed_df.loc[idx2, "과목"], parsed_df.loc[idx2, "교사"] = s1, t1
            
            st.session_state.swapped_indices.add(parsed_df.loc[idx1, "idx"])
            st.session_state.swapped_indices.add(parsed_df.loc[idx2, "idx"])
            st.session_state.parsed_df = parsed_df
            st.success("수업이 교체되었습니다!")
            st.rerun()

    with tab3:
        st.subheader("📝 대강 지정 및 주황색 하이라이트 적용")
        ca, cb, cc = st.columns(3)
        with ca:
            s_date = st.date_input("대강 날짜", date.today())
            s_day = st.selectbox("요일", ["월", "화", "수", "목", "금"])
            o_teacher = st.selectbox("원래 담당 교사", teacher_list)
        with cb:
            s_period = st.number_input("교시", 1, 7, 1)
            t_cls = st.selectbox("대상 학급", sorted(parsed_df["학급"].unique()))
        with cc:
            s_teacher = st.selectbox("대강 교사", teacher_list)
            reason = st.text_input("대강 사유 (필수)", placeholder="예: 출장, 병가, 공결")

        if st.button("📝 대강 저장 및 주황색 하이라이트 적용"):
            if not reason:
                st.error("대강 사유를 반드시 입력해야 합니다.")
            else:
                st.session_state.sub_logs.append({
                    "날짜": str(s_date),
                    "요일": s_day,
                    "교시": f"{s_period}교시",
                    "학급": t_cls,
                    "원교사": o_teacher,
                    "대강교사": s_teacher,
                    "대강사유": reason,
                    "단가": st.session_state.hourly_rate
                })
                st.success("대강 저장이 완료되었습니다.")
                st.rerun()

    with tab4:
        st.subheader("📊 교사별 주당 시수 & 대강 수당 집계")
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            st.markdown("##### [ 교사별 주당 수업 시수 ]")
            tc = parsed_df["교사"].value_counts().reset_index()
            tc.columns = ["교사명", "주당 수업 시수"]
            st.dataframe(tc, use_container_width=True)

        with c_s2:
            st.markdown("##### [ 대강 수당 집계표 ]")
            if len(st.session_state.sub_logs) > 0:
                l_df = pd.DataFrame(st.session_state.sub_logs)
                sum_df = l_df.groupby("대강교사").agg(총시수=("교시", "count"), 사유=("대강사유", lambda x: ", ".join(x.unique()))).reset_index()
                sum_df["단가"] = st.session_state.hourly_rate
                sum_df["총지급액"] = sum_df["총시수"] * sum_df["단가"]
                st.dataframe(sum_df, use_container_width=True)
                
                csv_data = l_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 대강일지 엑셀 다운로드", data=csv_data, file_name=f"{st.session_state.school_name}_대강일지_{date.today()}.csv")
            else:
                st.info("대강 기록이 아직 없습니다.")

else:
    st.info("💡 사이드바의 '관리자 모드'로 진입 후 전체 시간표 엑셀 파일(.xlsx)을 업로드해 주세요.")