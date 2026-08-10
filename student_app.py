import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta, date

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="우리반 시간표 둥둥", 
    page_icon="🐥", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. 컴시간 감성 + 모바일 파스텔 귀요미 CSS
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    * { font-family: 'Pretendard', -apple-system, sans-serif !important; }
    
    header, footer, [data-testid="stHeader"] { display: none !important; }
    .main .block-container { padding: 0.8rem 0.6rem !important; max-width: 600px !important; margin: 0 auto; }

    /* 메인 타이틀 귀여운 카드 */
    .header-card {
        background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%);
        border-radius: 20px;
        padding: 14px 10px;
        text-align: center;
        margin-bottom: 12px;
        border: 2px solid #bae6fd;
    }
    .school-name {
        font-size: 13px;
        font-weight: 700;
        color: #0284c7;
        margin-bottom: 2px;
    }
    .main-title {
        font-size: 19px;
        font-weight: 800;
        color: #0f172a;
    }

    /* 컴시간 스타일 모던 그리드 카드 */
    .grid-container {
        background: #ffffff;
        border-radius: 22px;
        border: 2.5px solid #f1f5f9;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.04);
        padding: 8px;
        overflow: hidden;
    }

    .cute-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 4px;
        text-align: center;
        table-layout: fixed;
    }
    
    .cute-table th {
        background-color: #f8fafc;
        color: #475569;
        padding: 8px 2px;
        font-weight: 800;
        font-size: 13px;
        border-radius: 12px;
    }

    .cute-table td {
        background-color: #f8fafc;
        border-radius: 12px;
        padding: 6px 1px;
        height: 60px;
        vertical-align: middle;
        transition: transform 0.1s ease;
    }
    
    .cute-table td:active {
        transform: scale(0.95);
    }

    /* 교시 셀 (컴시간 감성) */
    .period-cell {
        background-color: #f1f5f9 !important;
        font-weight: 800 !important;
        color: #475569 !important;
        font-size: 12px;
        border-radius: 12px;
    }
    .period-time {
        font-size: 9px;
        color: #94a3b8;
        font-weight: 600;
        display: block;
        margin-top: 1px;
    }

    /* 수업 과목 파스텔 젤리 알약 디자인 */
    .subject-box {
        font-size: 13.5px !important;
        font-weight: 800 !important;
        color: #1e293b !important;
        line-height: 1.1;
        letter-spacing: -0.3px;
    }
    .teacher-box {
        font-size: 10.5px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        margin-top: 2px;
    }

    /* 파스텔 배지 스티커 */
    .cell-swapped {
        background-color: #fef9c3 !important;
        border: 2px solid #fde047 !important;
    }
    .cell-substitute {
        background-color: #ffedd5 !important;
        border: 2px solid #fdba74 !important;
    }
    
    .sticker-badge {
        font-size: 9px;
        padding: 1px 5px;
        border-radius: 8px;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 2px;
    }
    .badge-swap { background-color: #eab308; color: #ffffff; }
    .badge-sub { background-color: #f97316; color: #ffffff; }
    
    /* 드롭다운 스타일 귀엽게 */
    div[data-baseweb="select"] > div {
        border-radius: 14px !important;
        border: 2px solid #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 및 DB 세션
if "week_offset" not in st.session_state: st.session_state.week_offset = 0
DB_FILE = "timemaster_data.db"
DEFAULT_EXCEL = "2026년 2학기 시간표.xlsx"

PERIOD_TIMES = {
    1: "08:50", 2: "09:50", 3: "10:50", 4: "11:50",
    5: "13:40", 6: "14:40", 7: "15:40"
}

def load_sub_logs():
    if not os.path.exists(DB_FILE): return []
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query("SELECT * FROM sub_logs", conn)
        logs = [{"날짜": str(r["s_date"]), "요일": str(r["s_day"]), "교시": int(r["s_period"]), "학급": str(r["t_cls"]), "원교사": str(r["o_teacher"]), "대강교사": str(r["s_teacher"]), "대강사유": str(r["reason"])} for _, r in df.iterrows()]
    except Exception: logs = []
    finally: conn.close()
    return logs

def load_cell_overrides():
    if not os.path.exists(DB_FILE): return []
    conn = sqlite3.connect(DB_FILE)
    try: df = pd.read_sql_query("SELECT * FROM cell_overrides", conn).to_dict('records')
    except Exception: df = []
    finally: conn.close()
    return df

def load_swap_logs():
    if not os.path.exists(DB_FILE): return []
    conn = sqlite3.connect(DB_FILE)
    try: df = pd.read_sql_query("SELECT * FROM swap_logs WHERE status = 'APPROVED'", conn).to_dict('records')
    except Exception: df = []
    finally: conn.close()
    return df

def get_week_dates(offset=0):
    base_date = date(2026, 8, 10)
    target_date = base_date + timedelta(weeks=offset)
    start_of_week = target_date - timedelta(days=target_date.weekday())
    return {"월": start_of_week, "화": start_of_week + timedelta(days=1), "수": start_of_week + timedelta(days=2), "목": start_of_week + timedelta(days=3), "금": start_of_week + timedelta(days=4)}

current_week_dates = get_week_dates(st.session_state.week_offset)
mon_str, fri_str = current_week_dates["월"].strftime("%Y-%m-%d"), current_week_dates["금"].strftime("%Y-%m-%d")

def parse_excel_timetable():
    if not os.path.exists(DEFAULT_EXCEL): return pd.DataFrame()
    df_proc = pd.read_excel(DEFAULT_EXCEL)
    class_names, current_grade = {}, ""
    for col_idx in range(2, len(df_proc.columns), 2):
        if "Unnamed" not in str(df_proc.columns[col_idx]) and pd.notna(df_proc.columns[col_idx]): current_grade = str(df_proc.columns[col_idx]).strip()
        ban_name = str(df_proc.iloc[0, col_idx]).strip() if pd.notna(df_proc.iloc[0, col_idx]) else ""
        class_names[col_idx] = f"{current_grade} {ban_name}" if current_grade and ban_name and ban_name!="nan" else (ban_name if ban_name and ban_name!="nan" else f"학급_{col_idx//2}")
    
    parsed_rows, current_day = [], "월"
    for r_idx in range(2, len(df_proc)):
        row = df_proc.iloc[r_idx]
        if pd.notna(row.iloc[0]) and str(row.iloc[0]).strip() in ["월", "화", "수", "목", "금"]: current_day = str(row.iloc[0]).strip()
        if pd.isna(row.iloc[1]): continue
        try: period = int(row.iloc[1])
        except: continue
        for col_idx, c_name in class_names.items():
            if col_idx + 1 < len(df_proc.columns):
                subj, teacher = str(row.iloc[col_idx]).strip(), str(row.iloc[col_idx+1]).strip()
                if subj and subj != "nan": parsed_rows.append({"학급": c_name, "요일": current_day, "교시": period, "과목": subj, "교사": teacher if teacher != "nan" else ""})
    return pd.DataFrame(parsed_rows)

def get_updated_timetable(base_df, target_week_dates):
    if base_df.empty: return base_df
    df = base_df.copy()
    df["is_swapped"] = False
    date_to_day = {v.strftime("%Y-%m-%d"): k for k, v in target_week_dates.items()}

    for swap in load_swap_logs():
        if swap["date1"] in date_to_day:
            day1 = date_to_day[swap["date1"]]
            m1 = (df["학급"] == swap["cls1"]) & (df["요일"] == day1) & (df["교시"] == swap["period1"])
            if m1.any(): df.loc[df[m1].index[0], ["과목", "교사", "is_swapped"]] = [swap["subj2"], swap["teacher2"], True]
        if swap["date2"] in date_to_day:
            day2 = date_to_day[swap["date2"]]
            m2 = (df["학급"] == swap["cls2"]) & (df["요일"] == day2) & (df["교시"] == swap["period2"])
            if m2.any(): df.loc[df[m2].index[0], ["과목", "교사", "is_swapped"]] = [swap["subj1"], swap["teacher1"], True]

    for ov in load_cell_overrides():
        if ov["s_date"] in date_to_day:
            day_kr = date_to_day[ov["s_date"]]
            m = (df["학급"] == ov["t_cls"]) & (df["요일"] == day_kr) & (df["교시"] == int(ov["s_period"]))
            if m.any(): df.loc[df[m].index[0], ["과목", "교사", "is_swapped"]] = [ov["subj"], ov["teacher"], True]
    return df

parsed_df = get_updated_timetable(parse_excel_timetable(), current_week_dates)

# 4. 귀여운 헤더 뷰
st.markdown("""
<div class="header-card">
    <div class="school-name">🏫 경남해양고등학교</div>
    <div class="main-title">🐥 우리반 모바일 시간표</div>
</div>
""", unsafe_allow_html=True)

# 주차 이동 컨트롤
c_b1, c_b2, c_b3 = st.columns([1, 1.8, 1])
with c_b1:
    if st.button("◀ 저번주", use_container_width=True):
        st.session_state.week_offset -= 1
        st.rerun()
with c_b2:
    st.markdown(f"<div style='text-align: center; font-weight: 800; color: #0284c7; font-size: 13px; padding-top:8px;'>📅 {mon_str[5:]} ~ {fri_str[5:]}</div>", unsafe_allow_html=True)
with c_b3:
    if st.button("다음주 ▶", use_container_width=True):
        st.session_state.week_offset += 1
        st.rerun()

# 5. 학급 선택 및 시간표 출력
if not parsed_df.empty:
    class_list = sorted(parsed_df["학급"].unique())
    selected_cls = st.selectbox("🎈 우리 반을 고르세요", class_list)

    if selected_cls:
        days = ["월", "화", "수", "목", "금"]
        sub_dict = {(log["날짜"], log["학급"], int(log["교시"])): log for log in load_sub_logs()}

        html = "<div class='grid-container'><table class='cute-table'><thead><tr><th style='width:13%;'>교시</th>"
        for d in days: 
            html += f"<th>{d}<br><span style='font-size:10px; font-weight:600; color:#94a3b8;'>({current_week_dates[d].strftime('%m/%d')})</span></th>"
        html += "</tr></thead><tbody>"

        for p in range(1, 8):
            p_time = PERIOD_TIMES.get(p, "")
            html += f"<tr><td class='period-cell'>{p}<span class='period-time'>{p_time}</span></td>"
            
            for d in days:
                date_str = current_week_dates[d].strftime("%Y-%m-%d")
                cell = parsed_df[(parsed_df["학급"] == selected_cls) & (parsed_df["요일"] == d) & (parsed_df["교시"] == p)]
                
                if not cell.empty:
                    row = cell.iloc[0]
                    subj, teacher, is_swapped = row["과목"], row["교사"], row.get("is_swapped", False)
                    sub_key = (date_str, selected_cls, p)
                    bg_class, badge_html = "", ""

                    if sub_key in sub_dict:
                        sub_info = sub_dict[sub_key]
                        if sub_info["대강교사"] == "빈칸":
                            subj, teacher = "-", ""
                        else:
                            bg_class = "cell-substitute"
                            badge_html = "<span class='sticker-badge badge-sub'>대강</span><br>"
                            teacher = sub_info['대강교사']
                    elif is_swapped:
                        bg_class = "cell-swapped"
                        badge_html = "<span class='sticker-badge badge-swap'>변동</span><br>"

                    if subj in ["", "-"]:
                        html += "<td><span style='color:#cbd5e1; font-size:11px;'>-</span></td>"
                    else:
                        html += f"<td class='{bg_class}'>{badge_html}<div class='subject-box'>{subj}</div><div class='teacher-box'>{teacher}</div></td>"
                else:
                    html += "<td><span style='color:#cbd5e1; font-size:11px;'>-</span></td>"
            html += "</tr>"
        html += "</tbody></table></div>"

        st.markdown(html, unsafe_allow_html=True)