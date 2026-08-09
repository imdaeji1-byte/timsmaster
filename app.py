import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta, date

# 1. 페이지 설정
st.set_page_config(page_title="TimeMaster - 학교 시간표 시스템", layout="wide")

# Custom CSS
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
        body { zoom: 80%; }
    }
    
    /* 포스터 및 카드형 시간표 스타일 */
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
        font-size: 16px;
        font-weight: bold;
        border: 1px solid #1e3a8a;
    }
    .timetable-poster td {
        border: 1px solid #cbd5e1;
        padding: 10px 6px;
        height: 65px;
        vertical-align: middle;
    }
    .period-col {
        background-color: #f1f5f9;
        font-weight: bold;
        color: #1e293b;
        width: 7% !important;
        font-size: 15px;
    }
    .day-col {
        background-color: #1e3a8a;
        color: #ffffff;
        font-weight: 800;
        font-size: 18px;
        width: 8% !important;
        vertical-align: middle;
        border-right: 2px solid #0f172a !important;
    }
    .subject-name {
        font-size: 15px;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.2;
    }
    .teacher-name {
        font-size: 13px;
        font-weight: 600;
        color: #475569;
        margin-top: 4px;
    }
    .bg-swapped {
        background-color: #fef08a !important; /* 노란색 */
        border: 2px solid #eab308 !important;
    }
    .bg-substitute {
        background-color: #ffedd5 !important; /* 주황색 */
        border: 2px solid #f97316 !important;
    }
    .status-badge {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 3px;
    }
    .badge-swap { background-color: #ca8a04; color: white; }
    .badge-sub { background-color: #ea580c; color: white; }
    
    /* 전체 시간표 가독성 대폭 향상 테이블 (구분선 굵기 차별화) */
    .grid-table {
        width: 100%;
        border-collapse: collapse;
        text-align: center;
        font-size: 14px;
    }
    .grid-table th {
        background-color: #1e3a8a;
        color: white;
        padding: 10px;
        font-weight: bold;
        border: 1px solid #1e3a8a;
    }
    .grid-table td {
        padding: 8px 4px;
        border-right: 1px solid #cbd5e1;
        border-left: 1px solid #cbd5e1;
        border-bottom: 1px solid #e2e8f0;
    }
    /* 요일별 경계선 굵게 (구분선 강화) */
    .day-border-bottom {
        border-bottom: 3.5px solid #1e3a8a !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. SQLite DB 연동
DB_FILE = "timemaster_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sub_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_date TEXT,
            s_day TEXT,
            s_period TEXT,
            t_cls TEXT,
            o_teacher TEXT,
            s_teacher TEXT,
            reason TEXT,
            rate INTEGER,
            week_offset INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS swap_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cls1 TEXT, day1 TEXT, period1 INTEGER, subj1 TEXT, teacher1 TEXT,
            cls2 TEXT, day2 TEXT, period2 INTEGER, subj2 TEXT, teacher2 TEXT,
            week_offset INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

def load_sub_logs():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM sub_logs", conn)
    conn.close()
    logs = []
    for _, row in df.iterrows():
        logs.append({
            "날짜": row["s_date"],
            "요일": row["s_day"],
            "교시": row["s_period"],
            "학급": row["t_cls"],
            "원교사": row["o_teacher"],
            "대강교사": row["s_teacher"],
            "대강사유": row["reason"],
            "단가": row["rate"],
            "주차": row["week_offset"]
        })
    return logs

def save_sub_log(log):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sub_logs (s_date, s_day, s_period, t_cls, o_teacher, s_teacher, reason, rate, week_offset)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (log["날짜"], log["요일"], log["교시"], log["학급"], log["원교사"], log["대강교사"], log["대강사유"], log["단가"], log["주차"]))
    conn.commit()
    conn.close()

def load_swap_logs():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM swap_logs", conn)
    conn.close()
    logs = []
    for _, row in df.iterrows():
        logs.append({
            "cls1": row["cls1"], "day1": row["day1"], "period1": row["period1"], "subj1": row["subj1"], "teacher1": row["teacher1"],
            "cls2": row["cls2"], "day2": row["day2"], "period2": row["period2"], "subj2": row["subj2"], "teacher2": row["teacher2"],
            "주차": row["week_offset"]
        })
    return logs

def save_swap_log(log):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO swap_logs (cls1, day1, period1, subj1, teacher1, cls2, day2, period2, subj2, teacher2, week_offset)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (log["cls1"], log["day1"], log["period1"], log["subj1"], log["teacher1"],
          log["cls2"], log["day2"], log["period2"], log["subj2"], log["teacher2"], log["주차"]))
    conn.commit()
    conn.close()

def clear_all_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sub_logs")
    c.execute("DELETE FROM swap_logs")
    conn.commit()
    conn.close()

# 3. 세션 초기화 및 로그인 상태 유지
if "school_name" not in st.session_state:
    st.session_state.school_name = "경남해양고등학교"
if "hourly_rate" not in st.session_state:
    st.session_state.hourly_rate = 13000
if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

st.session_state.sub_logs = load_sub_logs()
st.session_state.swap_logs = load_swap_logs()

def get_week_dates(offset=0):
    today = date.today() + timedelta(weeks=offset)
    start_of_week = today - timedelta(days=today.weekday())
    return {
        "월": start_of_week,
        "화": start_of_week + timedelta(days=1),
        "수": start_of_week + timedelta(days=2),
        "목": start_of_week + timedelta(days=3),
        "금": start_of_week + timedelta(days=4),
    }

current_week_dates = get_week_dates(st.session_state.week_offset)
mon_str = current_week_dates["월"].strftime("%Y-%m-%d")
fri_str = current_week_dates["금"].strftime("%Y-%m-%d")

# 4. 사이드바 로그인 관리
st.sidebar.title(f"🏫 {st.session_state.school_name}")
mode = st.sidebar.radio("접속 모드", ["학생/교사 시간표 보기", "관리자 모드 (수업교체/대강)"])

if mode == "관리자 모드 (수업교체/대강)":
    if not st.session_state.admin_authenticated:
        pin = st.sidebar.text_input("관리자 비밀번호 입력", type="password")
        if pin == "3060":
            st.session_state.admin_authenticated = True
            st.sidebar.success("관리자 로그인 완료!")
            st.rerun()
        elif pin != "":
            st.sidebar.error("비밀번호가 일치하지 않습니다.")
            mode = "학생/교사 시간표 보기"
        else:
            mode = "학생/교사 시간표 보기"

# 5. 지정 엑셀 파일 로드
DEFAULT_EXCEL = "2026년 2학기 시간표.xlsx"

if st.session_state.raw_df is None:
    if os.path.exists(DEFAULT_EXCEL):
        try:
            st.session_state.raw_df = pd.read_excel(DEFAULT_EXCEL)
        except Exception as e:
            st.error(f"기초 시간표 파일 로드 오류: {e}")

if mode == "관리자 모드 (수업교체/대강)" and st.session_state.admin_authenticated:
    with st.expander("⚙️ 시스템 설정 및 데이터 관리"):
        c_s, c_r = st.columns(2)
        with c_s:
            ns = st.text_input("학교명 변경", value=st.session_state.school_name)
            if ns != st.session_state.school_name:
                st.session_state.school_name = ns
                st.rerun()
        with c_r:
            st.session_state.hourly_rate = st.number_input("대강비 단가(원)", value=st.session_state.hourly_rate, step=1000)

        up_file = st.file_uploader("새 기초 시간표 엑셀 업로드 (.xlsx)", type=["xlsx"])
        if up_file is not None:
            try:
                st.session_state.raw_df = pd.read_excel(up_file)
                st.success("새 시간표로 업데이트되었습니다!")
            except Exception as e:
                st.error(f"파일 오류: {e}")

        st.markdown("---")
        if st.button("🚨 보존된 누적 교체/대강 기록 전체 초기화"):
            clear_all_db()
            st.session_state.sub_logs = []
            st.session_state.swap_logs = []
            st.success("모든 변경 이력이 초기화되었습니다.")
            st.rerun()

st.title(f"📅 {st.session_state.school_name} 시간표 관리 시스템")

# 주차 정렬 레이아웃 (상단 중앙 집중)
_, c_mid, _ = st.columns([1, 6, 1])
with c_mid:
    col_b1, col_b2, col_b3, col_b4 = st.columns([1.2, 4, 1, 1.2])
    with col_b1:
        if st.button("◀ 이전주", use_container_width=True):
            st.session_state.week_offset -= 1
            st.rerun()
    with col_b2:
        st.markdown(f"<h4 style='text-align: center; color: #1e3a8a; margin: 0;'>📆 [{mon_str} ~ {fri_str}] 시간표</h4>", unsafe_allow_html=True)
    with col_b3:
        if st.button("이번주", use_container_width=True):
            st.session_state.week_offset = 0
            st.rerun()
    with col_b4:
        if st.button("다음주 ▶", use_container_width=True):
            st.session_state.week_offset += 1
            st.rerun()

# 엑셀 정밀 파싱
def parse_excel_timetable(df_in):
    if df_in is None:
        return None, []
    
    df_proc = df_in.copy()
    cols = df_proc.columns
    row0 = df_proc.iloc[0]
    
    class_names = {}
    current_grade = ""
    for col_idx in range(2, len(cols), 2):
        col_name = str(cols[col_idx])
        if "Unnamed" not in col_name and pd.notna(col_name):
            current_grade = col_name.strip()
        
        ban_name = str(row0.iloc[col_idx]).strip() if pd.notna(row0.iloc[col_idx]) else ""
        if ban_name and ban_name != "nan":
            full_class = f"{current_grade} {ban_name}" if current_grade else ban_name
            class_names[col_idx] = full_class
        else:
            class_names[col_idx] = f"학급_{col_idx//2}"

    parsed_rows = []
    current_day = "월"
    
    for r_idx in range(2, len(df_proc)):
        row = df_proc.iloc[r_idx]
        day_val = row.iloc[0]
        if pd.notna(day_val) and str(day_val).strip() in ["월", "화", "수", "목", "금"]:
            current_day = str(day_val).strip()
            
        period_val = row.iloc[1]
        if pd.isna(period_val):
            continue
            
        try:
            period = int(period_val)
        except:
            continue

        for col_idx, c_name in class_names.items():
            if col_idx + 1 < len(df_proc.columns):
                subj = str(row.iloc[col_idx]).strip() if pd.notna(row.iloc[col_idx]) else ""
                teacher = str(row.iloc[col_idx+1]).strip() if pd.notna(row.iloc[col_idx+1]) else ""
                
                if subj and subj != "nan":
                    parsed_rows.append({
                        "학급": c_name,
                        "요일": current_day,
                        "교시": period,
                        "과목": subj,
                        "교사": teacher if teacher != "nan" else ""
                    })

    p_df = pd.DataFrame(parsed_rows)
    teachers = sorted(list(set(p_df["교사"].unique()) - {"", "nan"})) if not p_df.empty else []
    return p_df, teachers

p_df, t_list = parse_excel_timetable(st.session_state.raw_df)

# DB 내역 반영 함수
def apply_swaps_and_subs(base_df, week_offset):
    if base_df is None or base_df.empty:
        return base_df
    
    df = base_df.copy()
    df["is_swapped"] = False
    
    for swap in st.session_state.swap_logs:
        if swap["주차"] == week_offset:
            m1 = (df["학급"] == swap["cls1"]) & (df["요일"] == swap["day1"]) & (df["교시"] == swap["period1"])
            m2 = (df["학급"] == swap["cls2"]) & (df["요일"] == swap["day2"]) & (df["교시"] == swap["period2"])
            
            if m1.any() and m2.any():
                idx1 = df[m1].index[0]
                idx2 = df[m2].index[0]
                
                s1, t1 = df.loc[idx1, "과목"], df.loc[idx1, "교사"]
                s2, t2 = df.loc[idx2, "과목"], df.loc[idx2, "교사"]
                
                df.loc[idx1, "과목"], df.loc[idx1, "교사"] = s2, t2
                df.loc[idx2, "과목"], df.loc[idx2, "교사"] = s1, t1
                
                df.loc[idx1, "is_swapped"] = True
                df.loc[idx2, "is_swapped"] = True

    return df

parsed_df = apply_swaps_and_subs(p_df, st.session_state.week_offset)
teacher_list = t_list

# 개인별 주간 HTML 표 생성
def build_weekly_html_table(filtered_df, title_name):
    days = ["월", "화", "수", "목", "금"]
    periods = list(range(1, 8))
    
    html = f"<div style='text-align: center; margin-bottom: 12px;'><h3>🏫 {title_name} 주간 시간표 ({mon_str} ~ {fri_str})</h3></div>"
    html += "<table class='timetable-poster'><thead><tr><th class='period-col'>교시</th>"
    for d in days:
        d_str = current_week_dates[d].strftime("%m/%d")
        html += f"<th>{d} ({d_str})</th>"
    html += "</tr></thead><tbody>"
    
    sub_dict = { (log["학급"], log["요일"], int(str(log["교시"]).replace("교시","")), log["주차"]): log for log in st.session_state.sub_logs }
    
    for p in periods:
        html += f"<tr><td class='period-col'>{p}교시</td>"
        for d in days:
            cell_data = filtered_df[(filtered_df["요일"] == d) & (filtered_df["교시"] == p)]
            if not cell_data.empty:
                row = cell_data.iloc[0]
                subj = row["과목"]
                teacher = row["교사"]
                cls = row["학급"]
                is_swapped = row.get("is_swapped", False)
                
                cell_class = ""
                badge_html = ""
                sub_key = (cls, d, p, st.session_state.week_offset)
                
                if sub_key in sub_dict:
                    cell_class = "bg-substitute"
                    badge_html = f"<span class='status-badge badge-sub'>📝대강 ({sub_dict[sub_key]['대강교사']})</span><br>"
                    teacher = f"<s>{teacher}</s> ➔ <b>{sub_dict[sub_key]['대강교사']}</b>"
                elif is_swapped:
                    cell_class = "bg-swapped"
                    badge_html = "<span class='status-badge badge-swap'>🔄수업교체</span><br>"
                
                html += f"<td class='{cell_class}'>{badge_html}<div class='subject-name'>{subj}</div><div class='teacher-name'>{teacher}</div></td>"
            else:
                html += "<td>-</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

# 요일 병합형 가독성 극대화 전체 시간표 생성 함수
def build_merged_full_grid_html(df_in):
    days = ["월", "화", "수", "목", "금"]
    classes = sorted(df_in["학급"].unique())
    sub_dict = { (log["학급"], log["요일"], int(str(log["교시"]).replace("교시","")), log["주차"]): log for log in st.session_state.sub_logs }
    
    html = "<table class='grid-table'><thead><tr>"
    html += "<th style='width: 7%;'>요일</th><th style='width: 6%;'>교시</th>"
    for c in classes:
        html += f"<th>{c}</th>"
    html += "</tr></thead><tbody>"
    
    for d in days:
        d_str = current_week_dates[d].strftime("%m/%d")
        day_label = f"<b>{d}요일</b><br><span style='font-size:12px; font-weight:normal;'>({d_str})</span>"
        
        for p in range(1, 8):
            border_cls = "day-border-bottom" if p == 7 else ""
            html += f"<tr class='{border_cls}'>"
            
            # 요일 칼럼 1교시에만 병합 생성
            if p == 1:
                html += f"<td rowspan='7' class='day-col'>{day_label}</td>"
                
            html += f"<td class='period-col'>{p}교시</td>"
            
            for c in classes:
                cell_data = df_in[(df_in["학급"] == c) & (df_in["요일"] == d) & (df_in["교시"] == p)]
                if not cell_data.empty:
                    row = cell_data.iloc[0]
                    subj = row["과목"]
                    teacher = row["교사"]
                    is_swapped = row.get("is_swapped", False)
                    
                    sub_key = (c, d, p, st.session_state.week_offset)
                    
                    if sub_key in sub_dict:
                        bg_color = "#ffedd5"
                        txt = f"<span class='badge-sub status-badge'>대강</span><br><b>{subj}</b><br>({sub_dict[sub_key]['대강교사']})"
                    elif is_swapped:
                        bg_color = "#fef08a"
                        txt = f"<span class='badge-swap status-badge'>교체</span><br><b>{subj}</b><br>({teacher})"
                    else:
                        bg_color = "#ffffff"
                        txt = f"<b>{subj}</b><br><span style='color:#475569; font-size:12px;'>({teacher})</span>"
                        
                    html += f"<td style='background-color: {bg_color};'>{txt}</td>"
                else:
                    html += "<td>-</td>"
            html += "</tr>"
            
    html += "</tbody></table>"
    return html

# 6. 메인 탭 구동
if parsed_df is not None and not parsed_df.empty:
    
    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ 시간표 조회 (전체/반/교사)", "🔄 수업 위치 맞교환", "📝 대강 지정 및 사유", "📊 교사 시수 & 수당"])

    with tab1:
        c_v1, c_v2 = st.columns([3, 1])
        with c_v1:
            view_mode = st.radio("조회 방식", ["전체 시간표 (가로: 학급 / 세로: 요일·교시)", "학급별 주간 시간표", "교사별 주간 시간표"], horizontal=True)
        with c_v2:
            st.write("")
            st.button("🖨️ 시간표 인쇄 / PDF 저장", on_click=lambda: st.components.v1.html("<script>window.print();</script>"))

        if view_mode == "전체 시간표 (가로: 학급 / 세로: 요일·교시)":
            st.markdown(f"##### 📌 전체 학급 주간 시간표 (왼쪽: 요일/교시 병합 / 상단: 전체 학급)")
            st.markdown(build_merged_full_grid_html(parsed_df), unsafe_allow_html=True)

        elif view_mode == "학급별 주간 시간표":
            target_cls = st.selectbox("🎯 학급 선택", sorted(parsed_df["학급"].unique()))
            filtered = parsed_df[parsed_df["학급"] == target_cls]
            st.markdown(build_weekly_html_table(filtered, target_cls), unsafe_allow_html=True)

        else:
            target_t = st.selectbox("👨‍🏫 교사 선택", teacher_list)
            filtered = parsed_df[parsed_df["교사"] == target_t]
            st.markdown(build_weekly_html_table(filtered, f"{target_t} 선생님"), unsafe_allow_html=True)

    with tab2:
        st.subheader("🔄 특정 학급 전용 수업 맞교환 (스마트 중복 방지)")
        
        # 1. 학급 선택
        selected_cls = st.selectbox("🎯 대상 학급 선택", sorted(parsed_df["학급"].unique()))
        cls_df = parsed_df[parsed_df["학급"] == selected_cls]

        col_a, col_b = st.columns(2)
        
        # 2. 수업 A 선택
        with col_a:
            st.markdown(f"##### 📍 [수업 A] 교체할 첫 번째 수업")
            idx_a = st.selectbox(
                "수업 A 선택", 
                cls_df.index, 
                format_func=lambda x: f"{cls_df.loc[x, '요일']}요일 {cls_df.loc[x, '교시']}교시 - {cls_df.loc[x, '과목']}({cls_df.loc[x, '교사']})"
            )
            r1 = cls_df.loc[idx_a]

        # 3. 수업 B 스마트 필터링 (중복/충돌 없는 가능한 수업만 고르기)
        # 조건: r1["교사"]가 B시간에 다른 학급 수업이 없고, r2["교사"]가 A시간에 다른 학급 수업이 없는 경우만 필터링
        valid_b_indices = []
        for b_idx in cls_df.index:
            if b_idx == idx_a:
                continue
            r2 = cls_df.loc[b_idx]
            
            # 충돌 검사
            c1_conflict = parsed_df[(parsed_df["교사"] == r1["교사"]) & (parsed_df["요일"] == r2["요일"]) & (parsed_df["교시"] == r2["교시"]) & (parsed_df["학급"] != selected_cls)]
            c2_conflict = parsed_df[(parsed_df["교사"] == r2["교사"]) & (parsed_df["요일"] == r1["요일"]) & (parsed_df["교시"] == r1["교시"]) & (parsed_df["학급"] != selected_cls)]
            
            if c1_conflict.empty and c2_conflict.empty:
                valid_b_indices.append(b_idx)

        with col_b:
            st.markdown(f"##### 📍 [수업 B] 맞교환 가능한 수업 (자동 검증됨)")
            if valid_b_indices:
                idx_b = st.selectbox(
                    "수업 B 선택 (시수 충돌 없는 수업 목록)", 
                    valid_b_indices, 
                    format_func=lambda x: f"{cls_df.loc[x, '요일']}요일 {cls_df.loc[x, '교시']}교시 - {cls_df.loc[x, '과목']}({cls_df.loc[x, '교사']})"
                )
                r2 = cls_df.loc[idx_b]
            else:
                st.warning("⚠️ 선택하신 수업 A와 교체 시 충돌이 없는 수업 B 후보가 없습니다.")
                idx_b = None

        st.markdown("---")
        if idx_b is not None:
            if st.button("🔄 두 수업 맞교환 실행", use_container_width=True):
                log_entry = {
                    "cls1": selected_cls, "day1": r1["요일"], "period1": int(r1["교시"]), "subj1": r1["과목"], "teacher1": r1["교사"],
                    "cls2": selected_cls, "day2": r2["요일"], "period2": int(r2["교시"]), "subj2": r2["과목"], "teacher2": r2["교사"],
                    "주차": st.session_state.week_offset
                }
                save_swap_log(log_entry)
                st.session_state.swap_logs.append(log_entry)
                st.success(f"✅ [{selected_cls}] {r1['요일']} {r1['교시']}교시({r1['과목']}) ↔ {r2['요일']} {r2['교시']}교시({r2['과목']}) 수업이 교체되었습니다!")
                st.rerun()

    with tab3:
        st.subheader("📝 대강 지정 및 사유 기록 (DB 자동 보존)")
        ca, cb, cc = st.columns(3)
        with ca:
            s_day = st.selectbox("요일 선택", ["월", "화", "수", "목", "금"])
            s_date_val = current_week_dates[s_day]
            st.write(f"선택 날짜: **{s_date_val.strftime('%Y-%m-%d')}**")
            o_teacher = st.selectbox("원래 담당 교사", teacher_list)
        with cb:
            s_period = st.number_input("교시", 1, 7, 1)
            t_cls = st.selectbox("대상 학급", sorted(parsed_df["학급"].unique()))
        with cc:
            s_teacher = st.selectbox("대강 교사", teacher_list)
            reason = st.text_input("대강 사유 (필수)", placeholder="예: 출장, 병가, 공결")

        if st.button("📝 대강 저장 (DB 자동 보존)"):
            if not reason:
                st.error("대강 사유를 반드시 입력해야 합니다.")
            else:
                log_entry = {
                    "날짜": str(s_date_val),
                    "요일": s_day,
                    "교시": f"{s_period}교시",
                    "학급": t_cls,
                    "원교사": o_teacher,
                    "대강교사": s_teacher,
                    "대강사유": reason,
                    "단가": st.session_state.hourly_rate,
                    "주차": st.session_state.week_offset
                }
                save_sub_log(log_entry)
                st.session_state.sub_logs.append(log_entry)
                st.success("대강 저장이 완료되었으며 내역이 DB에 보존됩니다!")
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
                st.info("기록된 대강 내역이 없습니다.")

else:
    st.info("💡 Codespaces 폴더에 '2026년 2학기 시간표.xlsx' 파일을 위치시켜 주세요.")git add .