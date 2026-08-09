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
        padding: 12px 6px;
        height: 70px;
        width: 18%;
        vertical-align: middle;
    }
    .period-col {
        background-color: #f1f5f9;
        font-weight: bold;
        color: #1e293b;
        width: 8% !important;
        font-size: 15px;
    }
    .subject-name {
        font-size: 16px;
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
</style>
""", unsafe_allow_html=True)

# 2. SQLite DB
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
            t_cls TEXT,
            s_day TEXT,
            s_period INTEGER,
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
            "학급": row["t_cls"],
            "요일": row["s_day"],
            "교시": row["s_period"],
            "주차": row["week_offset"]
        })
    return logs

def save_swap_log(log):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO swap_logs (t_cls, s_day, s_period, week_offset)
        VALUES (?, ?, ?, ?)
    """, (log["학급"], log["요일"], log["교시"], log["주차"]))
    conn.commit()
    conn.close()

def clear_all_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sub_logs")
    c.execute("DELETE FROM swap_logs")
    conn.commit()
    conn.close()

# 3. 세션 초기화
if "school_name" not in st.session_state:
    st.session_state.school_name = "경남해양고등학교"
if "hourly_rate" not in st.session_state:
    st.session_state.hourly_rate = 13000
if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None

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

# 4. 사이드바
st.sidebar.title(f"🏫 {st.session_state.school_name}")
mode = st.sidebar.radio("접속 모드", ["학생/교사 시간표 보기", "관리자 모드 (수업교체/대강)"])

if mode == "관리자 모드 (수업교체/대강)":
    pin = st.sidebar.text_input("관리자 비밀번호", type="password")
    if pin != "1234":
        st.sidebar.warning("비밀번호(1234)를 입력해야 관리 기능이 활성화됩니다.")
        mode = "학생/교사 시간표 보기"

# 5. 지정 엑셀 파일 로드
DEFAULT_EXCEL = "2026년 2학기 시간표.xlsx"

if st.session_state.raw_df is None:
    if os.path.exists(DEFAULT_EXCEL):
        try:
            st.session_state.raw_df = pd.read_excel(DEFAULT_EXCEL)
        except Exception as e:
            st.error(f"기초 시간표 파일 로드 오류: {e}")

if mode == "관리자 모드 (수업교체/대강)":
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

col_w1, col_w2, col_w3 = st.columns([1, 2, 1])
with col_w1:
    if st.button("◀ 이전주"):
        st.session_state.week_offset -= 1
        st.rerun()
with col_w2:
    st.markdown(f"<h4 style='text-align: center; color: #1e3a8a;'>📆 [{mon_str} ~ {fri_str}] 시간표</h4>", unsafe_allow_html=True)
with col_w3:
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("이번주"):
            st.session_state.week_offset = 0
            st.rerun()
    with col_b2:
        if st.button("다음주 ▶"):
            st.session_state.week_offset += 1
            st.rerun()

# 엑셀 정밀 파싱 함수 (업로드된 엑셀 구조 맞춤)
def parse_excel_timetable(df_in):
    if df_in is None:
        return None, []
    
    df_proc = df_in.copy()
    
    # 1. 학년 & 반 정보 헤더 구축
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

    # 2. 요일 및 교시별 데이터 추출 (Row 2부터 시작)
    parsed_rows = []
    current_day = "월"
    
    for r_idx in range(2, len(df_proc)):
        row = df_proc.iloc[r_idx]
        
        # 요일 갱신
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

        # 각 반별 과목, 교사 추출
        for col_idx, c_name in class_names.items():
            if col_idx + 1 < len(df_proc.columns):
                subj = str(row.iloc[col_idx]).strip() if pd.notna(row.iloc[col_idx]) else ""
                teacher = str(row.iloc[col_idx+1]).strip() if pd.notna(row.iloc[col_idx+1]) else ""
                
                if subj and subj != "nan":
                    parsed_rows.append({
                        "idx": len(parsed_rows),
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
if p_df is not None:
    st.session_state.parsed_df = p_df
    st.session_state.t_list = t_list

parsed_df = st.session_state.get("parsed_df", None)
teacher_list = st.session_state.get("t_list", [])

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
    swap_set = { (s["학급"], s["요일"], s["교시"], s["주차"]) for s in st.session_state.swap_logs }
    
    for p in periods:
        html += f"<tr><td class='period-col'>{p}교시</td>"
        for d in days:
            cell_data = filtered_df[(filtered_df["요일"] == d) & (filtered_df["교시"] == p)]
            if not cell_data.empty:
                row = cell_data.iloc[0]
                subj = row["과목"]
                teacher = row["교사"]
                cls = row["학급"]
                
                cell_class = ""
                badge_html = ""
                
                sub_key = (cls, d, p, st.session_state.week_offset)
                swap_key = (cls, d, p, st.session_state.week_offset)
                
                if sub_key in sub_dict:
                    cell_class = "bg-substitute"
                    badge_html = f"<span class='status-badge badge-sub'>📝대강 ({sub_dict[sub_key]['대강교사']})</span><br>"
                    teacher = f"<s>{teacher}</s> ➔ <b>{sub_dict[sub_key]['대강교사']}</b>"
                elif swap_key in swap_set:
                    cell_class = "bg-swapped"
                    badge_html = "<span class='status-badge badge-swap'>🔄교체됨</span><br>"
                
                html += f"<td class='{cell_class}'>{badge_html}<div class='subject-name'>{subj}</div><div class='teacher-name'>{teacher}</div></td>"
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
            view_mode = st.radio("조회 방식", ["전체 시간표 (가로: 학급 / 세로: 월1~금7교시)", "학급별 주간 시간표", "교사별 주간 시간표"], horizontal=True)
        with c_v2:
            st.write("")
            st.button("🖨️ 시간표 인쇄 / PDF 저장", on_click=lambda: st.components.v1.html("<script>window.print();</script>"))

        if view_mode == "전체 시간표 (가로: 학급 / 세로: 월1~금7교시)":
            st.markdown(f"##### 📌 전체 학급 주간 시간표 (세로: 월1~금7교시 / 가로: 전체 학급)")
            
            pivot_df = parsed_df.copy()
            pivot_df["일시"] = pivot_df["요일"] + pivot_df["교시"].astype(str) + "교시"
            pivot_df["과목교사"] = pivot_df["과목"] + " (" + pivot_df["교사"] + ")"
            
            sub_dict = { (log["학급"], log["요일"], int(str(log["교시"]).replace("교시","")), log["주차"]): log for log in st.session_state.sub_logs }
            swap_set = { (s["학급"], s["요일"], s["교시"], s["주차"]) for s in st.session_state.swap_logs }
            
            for idx, row in pivot_df.iterrows():
                key = (row["학급"], row["요일"], row["교시"], st.session_state.week_offset)
                if key in sub_dict:
                    pivot_df.loc[idx, "과목교사"] = f"📝[대강] {row['과목']}({sub_dict[key]['대강교사']})"
                elif key in swap_set:
                    pivot_df.loc[idx, "과목교사"] = f"🔄[교체] {row['과목']}({row['교사']})"

            days = ["월", "화", "수", "목", "금"]
            time_order = [f"{d}{p}교시" for d in days for p in range(1, 8)]
            
            grid_all = pivot_df.pivot(index="일시", columns="학급", values="과목교사").reindex(time_order)
            st.dataframe(grid_all, use_container_width=True, height=650)

        elif view_mode == "학급별 주간 시간표":
            target_cls = st.selectbox("🎯 학급 선택", sorted(parsed_df["학급"].unique()))
            filtered = parsed_df[parsed_df["학급"] == target_cls]
            st.markdown(build_weekly_html_table(filtered, target_cls), unsafe_allow_html=True)

        else:
            target_t = st.selectbox("👨‍🏫 교사 선택", teacher_list)
            filtered = parsed_df[parsed_df["교사"] == target_t]
            st.markdown(build_weekly_html_table(filtered, f"{target_t} 선생님"), unsafe_allow_html=True)

    with tab2:
        st.subheader("🔄 수업 위치 맞교환 (자동 보존)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 📍 첫 번째 수업 선택")
            cls1 = st.selectbox("학급 A", sorted(parsed_df["학급"].unique()), key="sw_c1")
            df1 = parsed_df[parsed_df["학급"] == cls1]
            idx1 = st.selectbox("수업 A", df1.index, format_func=lambda x: f"{df1.loc[x, '요일']}요일 {df1.loc[x, '교시']}교시 - {df1.loc[x, '과목']}({df1.loc[x, '교사']})")

        with col2:
            st.markdown("##### 📍 두 번째 수업 선택")
            cls2 = st.selectbox("학급 B", sorted(parsed_df["학급"].unique()), key="sw_c2")
            df2 = parsed_df[parsed_df["학급"] == cls2]
            idx2 = st.selectbox("수업 B", df2.index, format_func=lambda x: f"{df2.loc[x, '요일']}요일 {df2.loc[x, '교시']}교시 - {df2.loc[x, '과목']}({df2.loc[x, '교사']})")

        if st.button("🔄 두 수업 맞교환 실행 (DB 자동 보존)"):
            s1, t1 = parsed_df.loc[idx1, "과목"], parsed_df.loc[idx1, "교사"]
            parsed_df.loc[idx1, "과목"], parsed_df.loc[idx1, "교사"] = parsed_df.loc[idx2, "과목"], parsed_df.loc[idx2, "교사"]
            parsed_df.loc[idx2, "과목"], parsed_df.loc[idx2, "교사"] = s1, t1
            
            l1 = {"학급": parsed_df.loc[idx1, "학급"], "요일": parsed_df.loc[idx1, "요일"], "교시": int(parsed_df.loc[idx1, "교시"]), "주차": st.session_state.week_offset}
            l2 = {"학급": parsed_df.loc[idx2, "학급"], "요일": parsed_df.loc[idx2, "요일"], "교시": int(parsed_df.loc[idx2, "교시"]), "주차": st.session_state.week_offset}
            
            save_swap_log(l1)
            save_swap_log(l2)
            st.session_state.swap_logs.extend([l1, l2])
            st.session_state.parsed_df = parsed_df
            st.success("수업이 맞교환되었으며 내역이 DB에 보존됩니다!")
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
    st.info("💡 Codespaces 폴더에 '2026년 2학기 시간표.xlsx' 파일을 위치시켜 주세요.")