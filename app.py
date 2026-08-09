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
        header, footer, .stSidebar, .stButton, button, [data-testid="stHeader"] { display: none !important; }
        .main .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        body { zoom: 80%; }
    }
    
    .table-container {
        width: 100%;
        overflow-x: auto;
        margin-bottom: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    
    .unified-table {
        width: 100%;
        border-collapse: collapse;
        text-align: center;
        font-size: 13px;
        background-color: #ffffff !important;
        table-layout: fixed;
    }
    
    .unified-table th {
        background-color: #1e3a8a !important;
        color: #ffffff !important;
        padding: 10px 4px;
        font-weight: bold;
        font-size: 14px;
        border: 1px solid #1e3a8a;
        border-bottom: 3.5px solid #0f172a !important;
        border-right: 3.5px solid #0f172a !important;
    }
    
    .unified-table td {
        background-color: #ffffff !important;
        padding: 8px 2px;
        border-right: 3.5px solid #0f172a !important;
        border-left: 1px solid #cbd5e1;
        border-bottom: 1px solid #cbd5e1;
        vertical-align: middle;
        height: 60px;
        word-break: break-all;
    }
    
    td.day-col {
        background-color: #1e3a8a !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        width: 4% !important;
        vertical-align: middle !important;
        border-right: 3.5px solid #0f172a !important;
        border-bottom: 3.5px solid #0f172a !important;
        padding: 4px 2px !important;
    }
    
    .day-col b { color: #ffffff !important; font-size: 18px !important; display: block !important; }
    .day-col span { color: #f1f5f9 !important; font-size: 12px !important; font-weight: 700 !important; display: block !important; }
    .period-col { background-color: #f1f5f9 !important; font-weight: bold; color: #1e293b !important; width: 5% !important; font-size: 13px; border-right: 3.5px solid #0f172a !important; }
    .subject-name { font-size: 14px !important; font-weight: 800 !important; color: #0f172a !important; line-height: 1.2; }
    .teacher-name { font-size: 12px !important; font-weight: 700 !important; color: #334155 !important; margin-top: 2px; }
    .bg-swapped { background-color: #fef08a !important; border: 2px solid #eab308 !important; }
    .bg-substitute { background-color: #ffedd5 !important; border: 2px solid #f97316 !important; }
    .status-badge { font-size: 10px; padding: 2px 4px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 2px; }
    .badge-swap { background-color: #ca8a04 !important; color: white !important; }
    .badge-sub { background-color: #ea580c !important; color: white !important; }
    tr.day-border-bottom td { border-bottom: 3.5px solid #0f172a !important; }
</style>
""", unsafe_allow_html=True)

# 2. DB 함수
DB_FILE = "timemaster_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sub_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_date TEXT, s_day TEXT, s_period INTEGER, t_cls TEXT,
            o_teacher TEXT, s_teacher TEXT, reason TEXT, rate INTEGER, week_offset INTEGER
        )
    """)
    c.execute("PRAGMA table_info(swap_logs)")
    cols = [row[1] for row in c.fetchall()]
    if "date1" not in cols:
        c.execute("DROP TABLE IF EXISTS swap_logs")
        c.execute("""
            CREATE TABLE swap_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cls1 TEXT, date1 TEXT, period1 INTEGER, subj1 TEXT, teacher1 TEXT,
                cls2 TEXT, date2 TEXT, period2 INTEGER, subj2 TEXT, teacher2 TEXT,
                status TEXT
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
            "날짜": str(row["s_date"]), "요일": str(row["s_day"]), "교시": int(row["s_period"]),
            "학급": str(row["t_cls"]), "원교사": str(row["o_teacher"]), "대강교사": str(row["s_teacher"]),
            "대강사유": str(row["reason"]), "단가": int(row["rate"]), "주차": int(row["week_offset"])
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

def load_swap_logs(status_filter="APPROVED"):
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query("SELECT * FROM swap_logs WHERE status = ?", conn, params=(status_filter,))
        logs = df.to_dict('records')
    except Exception:
        logs = []
    finally:
        conn.close()
    return logs

def save_swap_request(log, auto_approve=True):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    status = 'APPROVED' if auto_approve else 'PENDING'
    c.execute("""
        INSERT INTO swap_logs (cls1, date1, period1, subj1, teacher1, cls2, date2, period2, subj2, teacher2, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (log["cls1"], log["date1"], log["period1"], log["subj1"], log["teacher1"],
          log["cls2"], log["date2"], log["period2"], log["subj2"], log["teacher2"], status))
    conn.commit()
    conn.close()

def approve_swap_request(req_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE swap_logs SET status = 'APPROVED' WHERE id = ?", (req_id,))
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
if "school_name" not in st.session_state: st.session_state.school_name = "경남해양고등학교"
if "hourly_rate" not in st.session_state: st.session_state.hourly_rate = 13000
if "week_offset" not in st.session_state: st.session_state.week_offset = 0
if "raw_df" not in st.session_state: st.session_state.raw_df = None
if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False
if "copied_cell" not in st.session_state: st.session_state.copied_cell = None

st.session_state.sub_logs = load_sub_logs()
st.session_state.swap_logs = load_swap_logs("APPROVED")

def get_week_dates(offset=0):
    base_date = date(2026, 8, 10)
    target_date = base_date + timedelta(weeks=offset)
    start_of_week = target_date - timedelta(days=target_date.weekday())
    return {
        "월": start_of_week, "화": start_of_week + timedelta(days=1),
        "수": start_of_week + timedelta(days=2), "목": start_of_week + timedelta(days=3),
        "금": start_of_week + timedelta(days=4)
    }

current_week_dates = get_week_dates(st.session_state.week_offset)
mon_str = current_week_dates["월"].strftime("%Y-%m-%d")
fri_str = current_week_dates["금"].strftime("%Y-%m-%d")

# 4. 사이드바
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

# 5. 기초 파일 로드
DEFAULT_EXCEL = "2026년 2학기 시간표.xlsx"
if st.session_state.raw_df is None and os.path.exists(DEFAULT_EXCEL):
    try: st.session_state.raw_df = pd.read_excel(DEFAULT_EXCEL)
    except Exception as e: st.error(f"기초 시간표 로드 오류: {e}")

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
            except Exception as e: st.error(f"파일 오류: {e}")

        st.markdown("---")
        if st.button("🚨 보존된 누적 기록 전체 초기화"):
            clear_all_db()
            st.session_state.sub_logs = []
            st.session_state.swap_logs = []
            st.session_state.copied_cell = None
            st.success("모든 변경 이력이 초기화되었습니다.")
            st.rerun()

st.title(f"📅 {st.session_state.school_name} 시간표 관리 시스템")

# 상단 주차 컨트롤
_, c_mid, _ = st.columns([2, 5, 2])
with c_mid:
    col_b1, col_b2, col_b3, col_b4 = st.columns([1, 2.8, 0.9, 1])
    with col_b1:
        if st.button("◀ 이전주", use_container_width=True):
            st.session_state.week_offset -= 1
            st.rerun()
    with col_b2:
        st.markdown(f"<h4 style='text-align: center; color: #1e3a8a; margin: 0; white-space: nowrap;'>📆 [{mon_str} ~ {fri_str}] 시간표</h4>", unsafe_allow_html=True)
    with col_b3:
        if st.button("이번주", use_container_width=True):
            st.session_state.week_offset = 0
            st.rerun()
    with col_b4:
        if st.button("다음주 ▶", use_container_width=True):
            st.session_state.week_offset += 1
            st.rerun()

def parse_excel_timetable(df_in):
    if df_in is None: return None, []
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
            class_names[col_idx] = f"{current_grade} {ban_name}" if current_grade else ban_name
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
        if pd.isna(period_val): continue
        try: period = int(period_val)
        except: continue

        for col_idx, c_name in class_names.items():
            if col_idx + 1 < len(df_proc.columns):
                subj = str(row.iloc[col_idx]).strip() if pd.notna(row.iloc[col_idx]) else ""
                teacher = str(row.iloc[col_idx+1]).strip() if pd.notna(row.iloc[col_idx+1]) else ""
                if subj and subj != "nan":
                    parsed_rows.append({"학급": c_name, "요일": current_day, "교시": period, "과목": subj, "교사": teacher if teacher != "nan" else ""})

    p_df = pd.DataFrame(parsed_rows)
    teachers = sorted(list(set(p_df["교사"].unique()) - {"", "nan"})) if not p_df.empty else []
    return p_df, teachers

p_df, t_list = parse_excel_timetable(st.session_state.raw_df)

def apply_swaps_and_subs(base_df, current_week_dates):
    if base_df is None or base_df.empty: return base_df
    df = base_df.copy()
    df["is_swapped"] = False
    
    date_to_day = {v.strftime("%Y-%m-%d"): k for k, v in current_week_dates.items()}
    
    for swap in st.session_state.swap_logs:
        d1_str, d2_str = swap["date1"], swap["date2"]
        if d1_str in date_to_day and d2_str in date_to_day:
            day1, day2 = date_to_day[d1_str], date_to_day[d2_str]
            m1 = (df["학급"] == swap["cls1"]) & (df["요일"] == day1) & (df["교시"] == swap["period1"])
            m2 = (df["학급"] == swap["cls2"]) & (df["요일"] == day2) & (df["교시"] == swap["period2"])
            
            if m1.any() and m2.any():
                idx1, idx2 = df[m1].index[0], df[m2].index[0]
                s1, t1 = df.loc[idx1, "과목"], df.loc[idx1, "교사"]
                s2, t2 = df.loc[idx2, "과목"], df.loc[idx2, "교사"]
                df.loc[idx1, "과목"], df.loc[idx1, "교사"] = s2, t2
                df.loc[idx2, "과목"], df.loc[idx2, "교사"] = s1, t1
                df.loc[idx1, "is_swapped"] = True
                df.loc[idx2, "is_swapped"] = True

    return df

parsed_df = apply_swaps_and_subs(p_df, current_week_dates)
teacher_list = t_list

# 주간 시간표 HTML
def build_weekly_html_table(all_parsed_df, title_name, filter_type="CLASS"):
    days = ["월", "화", "수", "목", "금"]
    periods = list(range(1, 8))
    html = f"<div style='text-align: center; margin-bottom: 12px;'><h3>🏫 {title_name} 주간 시간표 ({mon_str} ~ {fri_str})</h3></div>"
    html += "<div class='table-container'><table class='unified-table'><thead><tr><th style='width:8%; color:white !important;'>교시</th>"
    for d in days: html += f"<th style='color:white !important;'>{d} ({current_week_dates[d].strftime('%m/%d')})</th>"
    html += "</tr></thead><tbody>"
    
    sub_dict = { (log["날짜"], log["학급"], int(log["교시"])): log for log in st.session_state.sub_logs }
    
    for p in periods:
        html += f"<tr><td class='period-col'>{p}교시</td>"
        for d in days:
            date_str = current_week_dates[d].strftime("%Y-%m-%d")
            cell_data = pd.DataFrame()
            is_sub_entry = False
            sub_info = None
            
            if filter_type == "CLASS":
                cell_data = all_parsed_df[(all_parsed_df["학급"] == title_name) & (all_parsed_df["요일"] == d) & (all_parsed_df["교시"] == p)]
            else:
                cell_data = all_parsed_df[(all_parsed_df["교사"] == title_name) & (all_parsed_df["요일"] == d) & (all_parsed_df["교시"] == p)]
                for sub_key, sub_val in sub_dict.items():
                    if sub_key[0] == date_str and int(sub_key[2]) == p and sub_val["대강교사"] == title_name:
                        target_class = sub_key[1]
                        cls_cell = all_parsed_df[(all_parsed_df["학급"] == target_class) & (all_parsed_df["요일"] == d) & (all_parsed_df["교시"] == p)]
                        if not cls_cell.empty:
                            cell_data = cls_cell
                            is_sub_entry = True
                            sub_info = sub_val
                            break

            if not cell_data.empty:
                row = cell_data.iloc[0]
                subj, teacher, cls, is_swapped = row["과목"], row["교사"], row["학급"], row.get("is_swapped", False)
                sub_key = (date_str, cls, p)
                cell_class, badge_html = "", ""
                
                if is_sub_entry or sub_key in sub_dict:
                    cell_class = "bg-substitute"
                    if not sub_info: sub_info = sub_dict[sub_key]
                    if filter_type == "TEACHER" and sub_info["대강교사"] == title_name:
                        badge_html = f"<span class='status-badge badge-sub'>📝대강수업 [{cls}]</span><br>"
                        teacher = f"<b>{title_name} (대강)</b>"
                    else:
                        badge_html = f"<span class='status-badge badge-sub'>📝대강 ({sub_info['대강교사']})</span><br>"
                        teacher = f"<s>{teacher}</s> ➔ <b>{sub_info['대강교사']}</b>"
                elif is_swapped:
                    cell_class = "bg-swapped"
                    badge_html = "<span class='status-badge badge-swap'>🔄수업교체</span><br>"
                
                display_teacher = f"({teacher})" if filter_type == "CLASS" else f"[{cls}]"
                html += f"<td class='{cell_class}'>{badge_html}<div class='subject-name'>{subj}</div><div class='teacher-name'>{display_teacher}</div></td>"
            else: html += "<td>-</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# 전체 시간표 HTML
def build_merged_full_grid_html(df_in):
    days = ["월", "화", "수", "목", "금"]
    classes = sorted(df_in["학급"].unique())
    sub_dict = { (log["날짜"], log["학급"], int(log["교시"])): log for log in st.session_state.sub_logs }
    
    html = "<div class='table-container'><table class='unified-table'><thead><tr><th style='width: 4%; color:white !important;'>요일</th><th style='width: 5%; color:white !important;'>교시</th>"
    for c in classes: html += f"<th style='color:white !important;'>{c}</th>"
    html += "</tr></thead><tbody>"
    
    for d in days:
        date_str = current_week_dates[d].strftime("%Y-%m-%d")
        day_label = f"<b>{d}</b><span>({current_week_dates[d].strftime('%m/%d')})</span>"
        for p in range(1, 8):
            border_cls = "day-border-bottom" if p == 7 else ""
            html += f"<tr class='{border_cls}'>"
            if p == 1: html += f"<td rowspan='7' class='day-col'>{day_label}</td>"
            html += f"<td class='period-col'>{p}교시</td>"
            for c in classes:
                cell_data = df_in[(df_in["학급"] == c) & (df_in["요일"] == d) & (df_in["교시"] == p)]
                if not cell_data.empty:
                    row = cell_data.iloc[0]
                    subj, teacher, is_swapped = row["과목"], row["교사"], row.get("is_swapped", False)
                    sub_key = (date_str, c, p)
                    
                    if sub_key in sub_dict:
                        bg_class = "bg-substitute"
                        txt = f"<span class='badge-sub status-badge'>대강</span><br><div class='subject-name'>{subj}</div><div class='teacher-name'>({sub_dict[sub_key]['대강교사']})</div>"
                    elif is_swapped:
                        bg_class = "bg-swapped"
                        txt = f"<span class='badge-swap status-badge'>교체</span><br><div class='subject-name'>{subj}</div><div class='teacher-name'>({teacher})</div>"
                    else:
                        bg_class = ""
                        txt = f"<div class='subject-name'>{subj}</div><div class='teacher-name'>({teacher})</div>"
                    
                    html += f"<td class='{bg_class}'>{txt}</td>"
                else: html += "<td>-</td>"
            html += "</tr>"
    html += "</tbody></table></div>"
    return html

# 6. 메인 구동
if parsed_df is not None and not parsed_df.empty:
    is_admin = (mode == "관리자 모드 (수업교체/대강)") and st.session_state.admin_authenticated
    
    if is_admin:
        tab1, tab2, tab3, tab4 = st.tabs(["🗓️ 시간표 관리", "🔄 수업 위치 맞교환 신청", "📝 대강 지정 및 사유 (관리자 전용)", "📊 교사 시수 & 대강 수당 (관리자 전용)"])
    else:
        tab1, tab2 = st.tabs(["🗓️ 시간표 조회 (전체/반/교사)", "🔄 수업 위치 맞교환 신청"])

    with tab1:
        c_v1, c_v2 = st.columns([3, 1])
        with c_v1:
            view_mode = st.radio("조회 방식", ["전체 시간표 (가로: 학급 / 세로: 요일·교시)", "학급별 주간 시간표", "교사별 주간 시간표"], horizontal=True)
        with c_v2:
            st.write("")
            st.button("🖨️ 시간표 인쇄 / PDF 저장", on_click=lambda: st.components.v1.html("<script>window.print();</script>"))

        if is_admin and view_mode == "전체 시간표 (가로: 학급 / 세로: 요일·교시)":
            st.info("💡 **관리자 가이드**: 수정/삭제/복사할 셀을 선택하면 바로 아래 **스마트 컨트롤 바**에서 1초 만에 반영됩니다.")
            
            # 셀 선택 리스트
            cell_options = []
            cell_map = {}
            days = ["월", "화", "수", "목", "금"]
            classes = sorted(parsed_df["학급"].unique())
            sub_dict = { (log["날짜"], log["학급"], int(log["교시"])): log for log in st.session_state.sub_logs }

            for d in days:
                d_str = current_week_dates[d].strftime("%Y-%m-%d")
                for p in range(1, 8):
                    for c in classes:
                        c_df = parsed_df[(parsed_df["학급"] == c) & (parsed_df["요일"] == d) & (parsed_df["교시"] == p)]
                        if not c_df.empty:
                            row = c_df.iloc[0]
                            subj, teacher = row["과목"], row["교사"]
                            sub_key = (d_str, c, p)
                            if sub_key in sub_dict:
                                display_txt = f"[{c}] {d}요일 {p}교시: {subj} (대강: {sub_dict[sub_key]['대강교사']})"
                            else:
                                display_txt = f"[{c}] {d}요일 {p}교시: {subj} ({teacher})"
                            
                            label = f"{d_str}_{c}_{p}"
                            cell_options.append((label, display_txt))
                            cell_map[label] = {
                                "date": d_str, "day": d, "cls": c, "period": p,
                                "subj": subj, "teacher": teacher
                            }

            col_sel, col_act = st.columns([2, 3])
            with col_sel:
                selected_label = st.selectbox(
                    "🎯 편집/복사할 시간표 셀 선택",
                    options=[opt[0] for opt in cell_options],
                    format_func=lambda x: dict(cell_options)[x]
                )
                target_cell = cell_map[selected_label]

            with col_act:
                st.write(f"📍 선택된 수업: **[{target_cell['cls']}] {target_cell['day']}요일 {target_cell['period']}교시 - {target_cell['subj']} ({target_cell['teacher']})**")
                
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    if st.button("📋 수업 복사", use_container_width=True):
                        st.session_state.copied_cell = target_cell
                        st.toast(f"[{target_cell['subj']}] 수업이 복사되었습니다.")

                with b2:
                    if st.button("🗑️ 수업 삭제", use_container_width=True):
                        log_entry = {
                            "날짜": target_cell["date"], "요일": target_cell["day"], "교시": target_cell["period"],
                            "학급": target_cell["cls"], "원교사": target_cell["teacher"], "대강교사": "휴강",
                            "대강사유": "관리자 삭제", "단가": 0, "주차": st.session_state.week_offset
                        }
                        save_sub_log(log_entry)
                        st.session_state.sub_logs = load_sub_logs()
                        st.success("수업이 휴강 처리되었습니다.")
                        st.rerun()

                with b3:
                    if st.button("📥 덮어쓰기", use_container_width=True):
                        if st.session_state.copied_cell:
                            cp = st.session_state.copied_cell
                            log_entry = {
                                "날짜": target_cell["date"], "요일": target_cell["day"], "교시": target_cell["period"],
                                "학급": target_cell["cls"], "원교사": target_cell["teacher"], "대강교사": cp["teacher"],
                                "대강사유": f"복사 배치({cp['subj']})", "단가": st.session_state.hourly_rate, "주차": st.session_state.week_offset
                            }
                            save_sub_log(log_entry)
                            st.session_state.sub_logs = load_sub_logs()
                            st.success(f"[{cp['subj']}({cp['teacher']})] 수업이 배치되었습니다.")
                            st.rerun()
                        else: st.warning("복사된 수업이 없습니다.")

                with b4:
                    if st.button("🔀 위치 맞교환", use_container_width=True):
                        if st.session_state.copied_cell:
                            cp = st.session_state.copied_cell
                            swap_entry = {
                                "cls1": cp["cls"], "date1": cp["date"], "period1": cp["period"], "subj1": cp["subj"], "teacher1": cp["teacher"],
                                "cls2": target_cell["cls"], "date2": target_cell["date"], "period2": target_cell["period"], "subj2": target_cell["subj"], "teacher2": target_cell["teacher"]
                            }
                            save_swap_request(swap_entry, auto_approve=True)
                            st.session_state.swap_logs = load_swap_logs("APPROVED")
                            st.success("두 수업 위치가 서로 교체되었습니다.")
                            st.rerun()
                        else: st.warning("복사된 수업이 없습니다.")

            st.markdown("---")

        if view_mode == "전체 시간표 (가로: 학급 / 세로: 요일·교시)":
            st.markdown(build_merged_full_grid_html(parsed_df), unsafe_allow_html=True)
        elif view_mode == "학급별 주간 시간표":
            target_cls = st.selectbox("🎯 학급 선택", sorted(parsed_df["학급"].unique()))
            st.markdown(build_weekly_html_table(parsed_df, target_cls, filter_type="CLASS"), unsafe_allow_html=True)
        else:
            target_t = st.selectbox("👨‍🏫 교사 선택", teacher_list)
            st.markdown(build_weekly_html_table(parsed_df, target_t, filter_type="TEACHER"), unsafe_allow_html=True)

    with tab2:
        st.subheader("🔄 날짜 지정 기반 수업 맞교환 신청 (승인 요청제)")
        if is_admin:
            st.markdown("### 📥 [관리자] 대기 중인 수업 교체 요청 목록")
            conn = sqlite3.connect(DB_FILE)
            try: pending_df = pd.read_sql_query("SELECT * FROM swap_logs WHERE status = 'PENDING'", conn)
            except Exception: pending_df = pd.DataFrame()
            finally: conn.close()
            
            if not pending_df.empty:
                for _, p_row in pending_df.iterrows():
                    c_p1, c_p2 = st.columns([4, 1])
                    with c_p1: st.info(f"📌 [{p_row['cls1']}] {p_row['date1']} {p_row['period1']}교시 ({p_row['subj1']}/{p_row['teacher1']}) ↔ {p_row['date2']} {p_row['period2']}교시 ({p_row['subj2']}/{p_row['teacher2']})")
                    with c_p2:
                        if st.button("✅ 승인 실행", key=f"app_{p_row['id']}"):
                            approve_swap_request(p_row['id'])
                            st.success("승인되었습니다!")
                            st.rerun()
            else: st.success("현재 대기 중인 교체 요청이 없습니다.")
            st.markdown("---")

        selected_cls = st.selectbox("🎯 대상 학급 선택", sorted(parsed_df["학급"].unique()))
        sub_dict_swap = { (log["날짜"], log["학급"], int(log["교시"])): log["대강교사"] for log in st.session_state.sub_logs }
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("##### 📍 [수업 A] 첫 번째 수업 지정")
            date_a = st.date_input("수업 A 날짜 선택", date(2026, 8, 10), key="d_a")
            day_a_kr = ["월", "화", "수", "목", "금", "토", "일"][date_a.weekday()]
            cls_df_a = parsed_df[(parsed_df["학급"] == selected_cls) & (parsed_df["요일"] == day_a_kr)].copy()
            
            if not cls_df_a.empty:
                for idx in cls_df_a.index:
                    d_str = str(date_a)
                    p_num = int(cls_df_a.loc[idx, "교시"])
                    if (d_str, selected_cls, p_num) in sub_dict_swap:
                        cls_df_a.loc[idx, "교사"] = f"{sub_dict_swap[(d_str, selected_cls, p_num)]}(대강)"
                idx_a = st.selectbox("수업 A 선택", cls_df_a.index, format_func=lambda x: f"{cls_df_a.loc[x, '교시']}교시 - {cls_df_a.loc[x, '과목']}({cls_df_a.loc[x, '교사']})")
                r1 = cls_df_a.loc[idx_a]
            else:
                st.warning("선택한 날짜에 해당하는 수업이 없습니다.")
                r1 = None

        with col_b:
            st.markdown("##### 📍 [수업 B] 맞교환 가능한 수업 (충돌 검증 완료)")
            date_b = st.date_input("수업 B 날짜 선택", date(2026, 8, 10), key="d_b")
            day_b_kr = ["월", "화", "수", "목", "금", "토", "일"][date_b.weekday()]
            cls_df_b = parsed_df[(parsed_df["학급"] == selected_cls) & (parsed_df["요일"] == day_b_kr)].copy()
            
            if not cls_df_b.empty:
                for idx in cls_df_b.index:
                    d_str = str(date_b)
                    p_num = int(cls_df_b.loc[idx, "교시"])
                    if (d_str, selected_cls, p_num) in sub_dict_swap:
                        cls_df_b.loc[idx, "교사"] = f"{sub_dict_swap[(d_str, selected_cls, p_num)]}(대강)"

            valid_b_indices = []
            if r1 is not None and not cls_df_b.empty:
                t1_clean = str(r1["교사"]).replace("(대강)", "").strip()
                for b_idx in cls_df_b.index:
                    if day_a_kr == day_b_kr and b_idx == idx_a: continue
                    r2_candidate = cls_df_b.loc[b_idx]
                    t2_clean = str(r2_candidate["교사"]).replace("(대강)", "").strip()
                    c1_conflict = parsed_df[(parsed_df["교사"] == t1_clean) & (parsed_df["요일"] == day_b_kr) & (parsed_df["교시"] == r2_candidate["교시"]) & (parsed_df["학급"] != selected_cls)]
                    c2_conflict = parsed_df[(parsed_df["교사"] == t2_clean) & (parsed_df["요일"] == day_a_kr) & (parsed_df["교시"] == r1["교시"]) & (parsed_df["학급"] != selected_cls)]
                    if c1_conflict.empty and c2_conflict.empty: valid_b_indices.append(b_idx)

            if valid_b_indices:
                idx_b = st.selectbox("수업 B 선택 (시수 충돌 없는 수업 목록)", valid_b_indices, format_func=lambda x: f"{cls_df_b.loc[x, '교시']}교시 - {cls_df_b.loc[x, '과목']}({cls_df_b.loc[x, '교사']})")
                r2 = cls_df_b.loc[idx_b]
            else:
                st.warning("⚠️ 선택하신 조건에서 충돌 없는 수업 B 후보가 없습니다.")
                r2 = None

        if r1 is not None and r2 is not None:
            if st.button("📩 수업 교체 요청 등록", use_container_width=True):
                log_entry = {
                    "cls1": selected_cls, "date1": str(date_a), "period1": int(r1["교시"]), "subj1": r1["과목"], "teacher1": str(r1["교사"]),
                    "cls2": selected_cls, "date2": str(date_b), "period2": int(r2["교시"]), "subj2": r2["과목"], "teacher2": str(r2["교사"])
                }
                save_swap_request(log_entry, auto_approve=is_admin)
                st.success("📩 수업 교체 요청이 등록/승인되었습니다!")

    if is_admin:
        with tab3:
            st.subheader("📝 스마트 대강 지정 및 사유 기록 (관리자 전용)")
            c_sub1, c_sub2 = st.columns(2)
            with c_sub1:
                st.markdown("##### 1️⃣ 대강 처리할 수업 지정")
                sub_date = st.date_input("대강 날짜 선택", date(2026, 8, 10), key="s_date")
                sub_day_kr = ["월", "화", "수", "목", "금", "토", "일"][sub_date.weekday()]
                sub_period = st.selectbox("교시 선택", list(range(1, 8)))
                target_classes_df = parsed_df[(parsed_df["요일"] == sub_day_kr) & (parsed_df["교시"] == sub_period)]
                
                if not target_classes_df.empty:
                    target_cls_idx = st.selectbox(
                        "대상 학급 및 기존 수업 선택",
                        target_classes_df.index,
                        format_func=lambda x: f"[{target_classes_df.loc[x, '학급']}] {target_classes_df.loc[x, '과목']} - 담당: {target_classes_df.loc[x, '교사']} 선생님"
                    )
                    selected_target = target_classes_df.loc[target_cls_idx]
                    orig_teacher, orig_cls, orig_subj = selected_target["교사"], selected_target["학급"], selected_target["과목"]
                else:
                    st.warning("선택한 날짜/교시에 등록된 수업 데이터가 없습니다.")
                    selected_target = None

            with c_sub2:
                st.markdown("##### 2️⃣ 대강 교사 지정 (해당 교시 수업 없는 교사만 자동 선별)")
                if selected_target is not None:
                    busy_teachers = set(parsed_df[(parsed_df["요일"] == sub_day_kr) & (parsed_df["교시"] == sub_period)]["교사"].unique())
                    available_teachers = [t for t in teacher_list if t not in busy_teachers]
                    
                    if available_teachers:
                        sub_teacher = st.selectbox("대강 교사 선택 (중복 수업 없는 교사 목록)", available_teachers)
                        sub_reason = st.text_input("대강 사유 (필수)", placeholder="예: 출장, 병가, 공결, 연가")
                        st.markdown("---")
                        if st.button("📝 대강 저장 및 시간표 반영", use_container_width=True):
                            if not sub_reason:
                                st.error("대강 사유를 반드시 입력하셔야 합니다.")
                            else:
                                log_entry = {
                                    "날짜": str(sub_date), "요일": sub_day_kr, "교시": int(sub_period),
                                    "학급": orig_cls, "원교사": orig_teacher, "대강교사": sub_teacher,
                                    "대강사유": sub_reason, "단가": st.session_state.hourly_rate, "주차": st.session_state.week_offset
                                }
                                save_sub_log(log_entry)
                                st.session_state.sub_logs = load_sub_logs()
                                st.success(f"✅ [{orig_cls}] {sub_date} {sub_period}교시 ({orig_subj}) 대강 교사({sub_teacher}) 지정 완료!")
                                st.rerun()
                    else:
                        st.error("⚠️ 해당 날짜/교시에 대강이 가능한 빈 교사가 없습니다.")

        with tab4:
            st.subheader("📊 교사별 주당 시수 & 기간별 대강일지 인쇄/출력 (관리자 전용)")
            c_s1, c_s2 = st.columns([1, 1.8])
            with c_s1:
                st.markdown("##### 📌 교사별 기본 주당 수업 시수")
                tc = parsed_df["교사"].value_counts().reset_index()
                tc.columns = ["교사명", "주당 수업 시수"]
                st.dataframe(tc, use_container_width=True)

            with c_s2:
                st.markdown("##### 📑 기간별 대강일지 검색 및 엑셀 다운로드")
                col_d1, col_d2 = st.columns(2)
                with col_d1: start_filter = st.date_input("조회 시작일", date(2026, 8, 1))
                with col_d2: end_filter = st.date_input("조회 종료일", date(2026, 8, 31))
                    
                if len(st.session_state.sub_logs) > 0:
                    all_sub_df = pd.DataFrame(st.session_state.sub_logs)
                    all_sub_df["날짜_dt"] = pd.to_datetime(all_sub_df["날짜"]).dt.date
                    filtered_sub = all_sub_df[(all_sub_df["날짜_dt"] >= start_filter) & (all_sub_df["날짜_dt"] <= end_filter)].copy()
                    
                    if not filtered_sub.empty:
                        filtered_sub["지급액"] = filtered_sub["단가"]
                        export_df = filtered_sub[["날짜", "요일", "교시", "학급", "원교사", "대강교사", "대강사유", "단가"]].rename(
                            columns={"날짜": "일자", "요일": "요일", "교시": "교시", "학급": "대상학급", "원교사": "기존교사", "대강교사": "대강교사", "대강사유": "대강사유", "단가": "대강수당(원)"}
                        )
                        st.dataframe(export_df, use_container_width=True)
                        csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label=f"📥 대강일지 ({start_filter} ~ {end_filter}) 엑셀(CSV) 다운로드",
                            data=csv_data, file_name=f"{st.session_state.school_name}_대강일지_{start_filter}_~_{end_filter}.csv",
                            mime="text/csv", use_container_width=True
                        )
                    else: st.info("선택하신 기간 동안 지정된 대강 이력이 없습니다.")
                else: st.info("등록된 대강 기록이 존재하지 않습니다.")