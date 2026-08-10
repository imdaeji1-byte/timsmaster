import streamlit as st
import pandas as pd
import sqlite3
import os
import streamlit.components.v1 as components
from datetime import datetime, timedelta, date

# 1. 페이지 기본 설정 및 세션 초기화
st.set_page_config(page_title="TimeMaster - 학교 시간표 시스템", layout="wide")

if "copied_data" not in st.session_state:
    st.session_state.copied_data = None
if "last_action_id" not in st.session_state:
    st.session_state.last_action_id = None  # 무한 반복(Stop 랙) 방지용 핵심 키
if "action_ui" not in st.session_state:
    st.session_state.action_ui = None       # 우클릭 네이티브 팝업 UI 상태
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

# Custom CSS
st.markdown("""
<style>
    @media print {
        header, footer, .stSidebar, .stButton, button, [data-testid="stHeader"] { display: none !important; }
        .main .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        body { zoom: 80%; }
    }
    .table-container { width: 100%; overflow-x: auto; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
    .unified-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; background-color: #ffffff !important; table-layout: fixed; }
    .unified-table th { background-color: #1e3a8a !important; color: #ffffff !important; padding: 10px 4px; font-weight: bold; font-size: 14px; border: 1px solid #1e3a8a; border-bottom: 3.5px solid #0f172a !important; border-right: 3.5px solid #0f172a !important; }
    .unified-table td { background-color: #ffffff !important; padding: 8px 2px; border-right: 3.5px solid #0f172a !important; border-left: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; vertical-align: middle; height: 60px; word-break: break-all; }
    td.day-col { background-color: #1e3a8a !important; color: #ffffff !important; font-weight: 800 !important; width: 4% !important; vertical-align: middle !important; border-right: 3.5px solid #0f172a !important; border-bottom: 3.5px solid #0f172a !important; padding: 4px 2px !important; }
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
    .action-panel { border: 2px solid #2563eb; border-radius: 8px; padding: 15px; background: #f8fafc; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# 2. 컴포넌트: JS 팝업 완전히 제거하고, 순수 우클릭 메뉴 + 무한반복 랙 차단 로직(action_id) 적용
def init_custom_component():
    comp_dir = "admin_grid_component"
    os.makedirs(comp_dir, exist_ok=True)
    html_path = os.path.join(comp_dir, "index.html")
    
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; background-color: white; overflow-x: auto; }
        .admin-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; background-color: #ffffff; table-layout: fixed; user-select: none; }
        .admin-table th { background-color: #1e3a8a; color: #ffffff; padding: 10px 4px; font-weight: bold; border: 1px solid #1e3a8a; border-bottom: 3.5px solid #0f172a; border-right: 3.5px solid #0f172a; }
        .admin-table td { background-color: #ffffff; padding: 6px 2px; border-right: 3.5px solid #0f172a; border-bottom: 1px solid #cbd5e1; height: 60px; vertical-align: middle; cursor: pointer; position: relative; }
        .admin-table td:hover { filter: brightness(0.92); outline: 2px solid #2563eb; }
        .admin-table td.selected { outline: 3.5px solid #ef4444 !important; background-color: #fef2f2 !important; }
        .day-col-js { background-color: #1e3a8a !important; color: #ffffff !important; font-weight: 800; width: 4%; border-right: 3.5px solid #0f172a !important; border-bottom: 3.5px solid #0f172a !important; }
        .period-col-js { background-color: #f1f5f9 !important; font-weight: bold; color: #1e293b; width: 5%; border-right: 3.5px solid #0f172a !important; }
        .bg-sub { background-color: #ffedd5 !important; }
        .bg-swap { background-color: #fef08a !important; }
        .context-menu { display: none; position: absolute; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 230px; z-index: 10000; padding: 6px 0; text-align: left; }
        .context-menu-item { padding: 10px 16px; font-size: 13px; font-weight: 600; color: #1e293b; cursor: pointer; display: flex; align-items: center; justify-content: space-between; }
        .context-menu-item:hover { background-color: #f1f5f9; color: #2563eb; }
        .context-menu-divider { height: 1px; background-color: #e2e8f0; margin: 4px 0; }
    </style>
    <script>
        function sendMessageToStreamlit(type, data) {
            const outData = Object.assign({isStreamlitMessage: true, type: type}, data);
            window.parent.postMessage(outData, "*");
        }
        const Streamlit = {
            setComponentReady: function() { sendMessageToStreamlit("streamlit:componentReady", {apiVersion: 1}); },
            setFrameHeight: function(height) { sendMessageToStreamlit("streamlit:setFrameHeight", {height: height}); },
            setComponentValue: function(value) { sendMessageToStreamlit("streamlit:setComponentValue", {value: value}); }
        };

        let gridData = {}; let classes = []; let copiedData = null;
        let selectedKey = null; const days = ["월", "화", "수", "목", "금"];

        window.addEventListener("message", function(event) {
            if (event.source !== window.parent) return;
            if (event.data.type === "streamlit:render") {
                gridData = event.data.args.grid_data;
                classes = event.data.args.classes;
                copiedData = event.data.args.copied_data;
                renderGrid();
                setTimeout(() => Streamlit.setFrameHeight(document.body.scrollHeight + 30), 50);
            }
        });

        function renderGrid() {
            const tbody = document.getElementById("grid-body");
            tbody.innerHTML = "";
            const thead_tr = document.getElementById("grid-head-tr");
            thead_tr.innerHTML = '<th style="width: 4%;">요일</th><th style="width: 5%;">교시</th>';
            classes.forEach(c => { const th = document.createElement("th"); th.innerText = c; thead_tr.appendChild(th); });

            days.forEach(d => {
                for(let p = 1; p <= 7; p++) {
                    const tr = document.createElement("tr");
                    if(p === 7) tr.style.borderBottom = "3.5px solid #0f172a";
                    if(p === 1) {
                        const tdDay = document.createElement("td");
                        tdDay.rowSpan = 7; tdDay.className = "day-col-js";
                        tdDay.innerHTML = `<b>${d}</b>`; tr.appendChild(tdDay);
                    }
                    const tdP = document.createElement("td");
                    tdP.className = "period-col-js"; tdP.innerText = `${p}교시`;
                    tr.appendChild(tdP);

                    classes.forEach(c => {
                        const td = document.createElement("td");
                        const key = Object.keys(gridData).find(k => String(gridData[k].day) === String(d) && String(gridData[k].period) === String(p) && String(gridData[k].cls) === String(c));
                        if(!key || !gridData[key]) { td.innerText = "-"; tr.appendChild(td); return; }

                        const item = gridData[key];
                        td.id = key;
                        if(item.is_sub) td.className = "bg-sub";
                        else if(item.is_swapped) td.className = "bg-swap";
                        
                        let txt = "-";
                        if(item.subj) {
                            if(item.is_sub) txt = `<span style="font-size:10px; background:#ea580c; color:white; padding:1px 3px; border-radius:3px;">대강</span><br><b>${item.subj}</b><br>(${item.sub_teacher})`;
                            else if(item.is_swapped) txt = `<span style="font-size:10px; background:#ca8a04; color:white; padding:1px 3px; border-radius:3px;">교체</span><br><b>${item.subj}</b><br>(${item.teacher})`;
                            else txt = `<b>${item.subj}</b><br><span style="color:#334155; font-size:12px;">(${item.teacher})</span>`;
                        }
                        td.innerHTML = txt;
                        td.onclick = (e) => selectCell(key, td);
                        td.oncontextmenu = (e) => { e.preventDefault(); selectCell(key, td); showContextMenu(e.pageX, e.pageY); };
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                }
            });
        }

        function selectCell(key, element) {
            document.querySelectorAll(".admin-table td").forEach(td => td.classList.remove("selected"));
            selectedKey = key; if(element) element.classList.add("selected");
            hideContextMenu();
        }

        function showContextMenu(x, y) {
            const menu = document.getElementById("contextMenu");
            const overItem = document.getElementById("pasteOverwriteItem");
            const swapItem = document.getElementById("pasteSwapItem");
            if(copiedData) { overItem.style.display = "flex"; swapItem.style.display = "flex"; } 
            else { overItem.style.display = "none"; swapItem.style.display = "none"; }
            menu.style.left = `${x}px`; menu.style.top = `${y}px`; menu.style.display = "block";
        }
        function hideContextMenu() { document.getElementById("contextMenu").style.display = "none"; }

        function onMenuAction(actionType) {
            hideContextMenu();
            if(!selectedKey || !gridData[selectedKey]) return;
            // 핵심: 매 액션마다 고유 ID(action_id)를 생성하여 무한반복 방지
            const actionPayload = {
                action_id: Date.now().toString() + Math.random().toString(),
                act: actionType,
                target: gridData[selectedKey]
            };
            if(actionType === 'COPY') {
                copiedData = gridData[selectedKey];
                actionPayload.target = copiedData;
            }
            Streamlit.setComponentValue(actionPayload);
        }

        window.onclick = (e) => { if(!e.target.closest("#contextMenu")) hideContextMenu(); };
        window.addEventListener("keydown", (e) => {
            if(!selectedKey) return;
            if(e.key === "Delete" || e.key === "Backspace") { onMenuAction("DELETE"); }
            else if(e.ctrlKey && e.key === "c") { onMenuAction("COPY"); }
            else if(e.ctrlKey && e.key === "v") {
                if(copiedData) onMenuAction("PASTE_OVERWRITE"); // 기본은 단순 이동
                else Streamlit.setComponentValue({action_id: Date.now().toString(), act: 'NO_COPY_DATA'});
            }
        });
    </script>
</head>
<body onload="Streamlit.setComponentReady()">
    <table class="admin-table">
        <thead><tr id="grid-head-tr"></tr></thead>
        <tbody id="grid-body"></tbody>
    </table>
    <!-- 우클릭 팝업 메뉴 (JS 팝업 대신 파이썬 네이티브 UI로 호출) -->
    <div id="contextMenu" class="context-menu">
        <div class="context-menu-item" onclick="onMenuAction('DELETE')">🗑️ 수업 삭제 (빈칸)</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" onclick="onMenuAction('COPY')">📋 수업 복사 (Ctrl+C)</div>
        <div id="pasteOverwriteItem" class="context-menu-item" style="display:none;" onclick="onMenuAction('PASTE_OVERWRITE')">📥 복사된 수업 이동(배치)</div>
        <div id="pasteSwapItem" class="context-menu-item" style="display:none;" onclick="onMenuAction('PASTE_SWAP')">🔀 복사된 수업과 교체</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" onclick="onMenuAction('REQ_SWAP')">🔄 날짜 지정 수업 교체</div>
        <div class="context-menu-item" onclick="onMenuAction('REQ_SUB')">📝 스마트 대강 지정</div>
    </div>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return components.declare_component("AdminGrid", path=comp_dir)

AdminGrid = init_custom_component()

# 3. DB 초기화 (수정 없음)
DB_FILE = "timemaster_data.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sub_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, s_date TEXT, s_day TEXT, s_period INTEGER, t_cls TEXT, o_teacher TEXT, s_teacher TEXT, reason TEXT, rate INTEGER, week_offset INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS cell_overrides (id INTEGER PRIMARY KEY AUTOINCREMENT, s_date TEXT, s_day TEXT, s_period INTEGER, t_cls TEXT, subj TEXT, teacher TEXT)""")
    c.execute("PRAGMA table_info(swap_logs)")
    cols = [row[1] for row in c.fetchall()]
    if "date1" not in cols:
        c.execute("DROP TABLE IF EXISTS swap_logs")
        c.execute("""CREATE TABLE swap_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, cls1 TEXT, date1 TEXT, period1 INTEGER, subj1 TEXT, teacher1 TEXT, cls2 TEXT, date2 TEXT, period2 INTEGER, subj2 TEXT, teacher2 TEXT, status TEXT)""")
    conn.commit()
    conn.close()

init_db()

def load_sub_logs():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM sub_logs", conn)
    conn.close()
    return [{"날짜": str(r["s_date"]), "요일": str(r["s_day"]), "교시": int(r["s_period"]), "학급": str(r["t_cls"]), "원교사": str(r["o_teacher"]), "대강교사": str(r["s_teacher"]), "대강사유": str(r["reason"]), "단가": int(r["rate"]), "주차": int(r["week_offset"])} for _, r in df.iterrows()]

def save_sub_log(log):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO sub_logs (s_date, s_day, s_period, t_cls, o_teacher, s_teacher, reason, rate, week_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (log["날짜"], log["요일"], log["교시"], log["학급"], log["원교사"], log["대강교사"], log["대강사유"], log["단가"], log["주차"]))
    conn.commit()
    conn.close()

def load_cell_overrides():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM cell_overrides", conn)
    conn.close()
    return df.to_dict('records')

def save_cell_override(date_str, day_str, period, cls, subj, teacher):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM cell_overrides WHERE s_date = ? AND t_cls = ? AND s_period = ?", (date_str, cls, period))
    c.execute("INSERT INTO cell_overrides (s_date, s_day, s_period, t_cls, subj, teacher) VALUES (?, ?, ?, ?, ?, ?)", (date_str, day_str, period, cls, subj, teacher))
    conn.commit()
    conn.close()

def load_swap_logs(status_filter="APPROVED"):
    conn = sqlite3.connect(DB_FILE)
    try: logs = pd.read_sql_query("SELECT * FROM swap_logs WHERE status = ?", conn, params=(status_filter,)).to_dict('records')
    except: logs = []
    finally: conn.close()
    return logs

def save_swap_request(log, auto_approve=True):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    status = 'APPROVED' if auto_approve else 'PENDING'
    c.execute("INSERT INTO swap_logs (cls1, date1, period1, subj1, teacher1, cls2, date2, period2, subj2, teacher2, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (log["cls1"], log["date1"], log["period1"], log["subj1"], log["teacher1"], log["cls2"], log["date2"], log["period2"], log["subj2"], log["teacher2"], status))
    conn.commit()
    conn.close()

def clear_all_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sub_logs")
    c.execute("DELETE FROM swap_logs")
    c.execute("DELETE FROM cell_overrides")
    conn.commit()
    conn.close()

st.session_state.sub_logs = load_sub_logs()
st.session_state.swap_logs = load_swap_logs("APPROVED")

def get_week_dates(offset=0):
    base_date = date(2026, 8, 10)
    target_date = base_date + timedelta(weeks=offset)
    start_of_week = target_date - timedelta(days=target_date.weekday())
    return {"월": start_of_week, "화": start_of_week + timedelta(days=1), "수": start_of_week + timedelta(days=2), "목": start_of_week + timedelta(days=3), "금": start_of_week + timedelta(days=4)}

current_week_dates = get_week_dates(st.session_state.week_offset)
mon_str, fri_str = current_week_dates["월"].strftime("%Y-%m-%d"), current_week_dates["금"].strftime("%Y-%m-%d")

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

# 5. 파싱 및 모든 주차간 변동사항 통합 적용 (Cross-week 완벽 지원)
DEFAULT_EXCEL = "2026년 2학기 시간표.xlsx"
if st.session_state.raw_df is None and os.path.exists(DEFAULT_EXCEL):
    st.session_state.raw_df = pd.read_excel(DEFAULT_EXCEL)

def parse_excel_timetable(df_in):
    if df_in is None: return None, []
    df_proc = df_in.copy()
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
    p_df = pd.DataFrame(parsed_rows)
    return p_df, sorted(list(set(p_df["교사"].unique()) - {"", "nan"})) if not p_df.empty else []

p_df, teacher_list = parse_excel_timetable(st.session_state.raw_df)

def get_latest_updated_timetable(base_df, current_week_dates):
    if base_df is None or base_df.empty: return base_df
    df = base_df.copy()
    df["is_swapped"] = False
    date_to_day = {v.strftime("%Y-%m-%d"): k for k, v in current_week_dates.items()}

    # 주차 간섭 없이 현재 보고 있는 주차에 맞춰 독립적으로 교체 데이터 반영
    for swap in st.session_state.swap_logs:
        if swap["date1"] in date_to_day:
            day1 = date_to_day[swap["date1"]]
            m1 = (df["학급"] == swap["cls1"]) & (df["요일"] == day1) & (df["교시"] == swap["period1"])
            if m1.any():
                df.loc[df[m1].index[0], ["과목", "교사", "is_swapped"]] = [swap["subj2"], swap["teacher2"], True]
        if swap["date2"] in date_to_day:
            day2 = date_to_day[swap["date2"]]
            m2 = (df["학급"] == swap["cls2"]) & (df["요일"] == day2) & (df["교시"] == swap["period2"])
            if m2.any():
                df.loc[df[m2].index[0], ["과목", "교사", "is_swapped"]] = [swap["subj1"], swap["teacher1"], True]

    overrides = load_cell_overrides()
    for ov in overrides:
        if ov["s_date"] in date_to_day:
            day_kr = date_to_day[ov["s_date"]]
            m = (df["학급"] == ov["t_cls"]) & (df["요일"] == day_kr) & (df["교시"] == int(ov["s_period"]))
            if m.any():
                df.loc[df[m].index[0], ["과목", "교사", "is_swapped"]] = [ov["subj"], ov["teacher"], True]

    return df

parsed_df = get_latest_updated_timetable(p_df, current_week_dates)

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
                    if not sub_info: sub_info = sub_dict[sub_key]
                    if sub_info["대강교사"] == "빈칸":
                        subj, teacher = "-", ""
                    else:
                        cell_class = "bg-substitute"
                        if filter_type == "TEACHER" and sub_info["대강교사"] == title_name:
                            badge_html = f"<span class='status-badge badge-sub'>📝대강수업 [{cls}]</span><br>"
                            teacher = f"<b>{title_name} (대강)</b>"
                        else:
                            badge_html = f"<span class='status-badge badge-sub'>📝대강 ({sub_info['대강교사']})</span><br>"
                            teacher = f"<s>{teacher}</s> ➔ <b>{sub_info['대강교사']}</b>"
                elif is_swapped:
                    cell_class = "bg-swapped"
                    badge_html = "<span class='status-badge badge-swap'>🔄교체/이동</span><br>"
                
                display_teacher = f"({teacher})" if filter_type == "CLASS" and teacher else f"[{cls}]"
                if subj == "" or subj == "-": html += "<td>-</td>"
                else: html += f"<td class='{cell_class}'>{badge_html}<div class='subject-name'>{subj}</div><div class='teacher-name'>{display_teacher}</div></td>"
            else: html += "<td>-</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

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
                        if sub_dict[sub_key]['대강교사'] == "빈칸":
                            bg_class, txt = "", "-"
                        else:
                            bg_class, txt = "bg-substitute", f"<span class='badge-sub status-badge'>대강</span><br><div class='subject-name'>{subj}</div><div class='teacher-name'>({sub_dict[sub_key]['대강교사']})</div>"
                    elif is_swapped:
                        bg_class, txt = "bg-swapped", f"<span class='badge-swap status-badge'>이동</span><br><div class='subject-name'>{subj}</div><div class='teacher-name'>({teacher})</div>"
                    else:
                        bg_class, txt = "", f"<div class='subject-name'>{subj}</div><div class='teacher-name'>({teacher})</div>" if subj else "-"
                    html += f"<td class='{bg_class}'>{txt}</td>"
                else: html += "<td>-</td>"
            html += "</tr>"
    html += "</tbody></table></div>"
    return html

# 6. 상단 네비게이션
st.title(f"📅 {st.session_state.school_name} 시간표 관리 시스템")
_, c_mid, _ = st.columns([2, 5, 2])
with c_mid:
    col_b1, col_b2, col_b3, col_b4 = st.columns([1, 2.8, 0.9, 1])
    with col_b1:
        if st.button("◀ 이전주", use_container_width=True): st.session_state.week_offset -= 1; st.rerun()
    with col_b2: st.markdown(f"<h4 style='text-align: center; color: #1e3a8a; margin: 0;'>📆 [{mon_str} ~ {fri_str}]</h4>", unsafe_allow_html=True)
    with col_b3:
        if st.button("이번주", use_container_width=True): st.session_state.week_offset = 0; st.rerun()
    with col_b4:
        if st.button("다음주 ▶", use_container_width=True): st.session_state.week_offset += 1; st.rerun()

# 7. 네이티브 스트림릿 액션 UI 렌더링 (우클릭 메뉴 선택 시 상단에 등장)
if st.session_state.action_ui is not None:
    ui_type = st.session_state.action_ui["type"]
    t_item = st.session_state.action_ui["target"]
    
    st.markdown("<div class='action-panel'>", unsafe_allow_html=True)
    if ui_type == "SWAP":
        st.markdown(f"#### 🔄 날짜 지정 수업 맞교환 (대상: **{t_item['date']} {t_item['period']}교시 [{t_item['cls']}] {t_item['subj']}({t_item['teacher']})**)")
        c_s1, c_s2, c_s3 = st.columns([1, 2, 1])
        with c_s1:
            target_date = st.date_input("교체할 날짜 선택", pd.to_datetime(t_item['date']).date())
        with c_s2:
            target_day_kr = ["월","화","수","목","금","토","일"][target_date.weekday()]
            if target_day_kr in ["토", "일"]:
                st.error("주말은 교체할 수 없습니다.")
                valid_options = []
            else:
                # 엑셀 원본(p_df)이 아닌 최신 적용 상태에서 충돌 검증
                cls_df = p_df[(p_df["학급"] == t_item["cls"]) & (p_df["요일"] == target_day_kr)]
                valid_options = []
                for _, row in cls_df.iterrows():
                    r_period = row["교시"]
                    if t_item['date'] == str(target_date) and int(t_item['period']) == r_period: continue
                    # 충돌 확인
                    c1 = parsed_df[(parsed_df["교사"] == t_item['teacher']) & (parsed_df["요일"] == target_day_kr) & (parsed_df["교시"] == r_period) & (parsed_df["학급"] != t_item['cls'])]
                    c2 = parsed_df[(parsed_df["교사"] == row["교사"]) & (parsed_df["요일"] == t_item['day']) & (parsed_df["교시"] == int(t_item['period'])) & (parsed_df["학급"] != t_item['cls'])]
                    if c1.empty and c2.empty:
                        valid_options.append((r_period, row["과목"], row["교사"]))
                
                if valid_options:
                    selected_opt = st.selectbox("교체 가능한 수업 선택", valid_options, format_func=lambda x: f"{x[0]}교시 - {x[1]}({x[2]})")
                else:
                    st.warning("선택한 날짜에 충돌 없이 교체 가능한 수업이 없습니다.")
                    selected_opt = None
        with c_s3:
            st.write("")
            st.write("")
            if st.button("✅ 맞교환 확정", type="primary", use_container_width=True) and selected_opt:
                log_entry = {
                    "cls1": t_item["cls"], "date1": t_item["date"], "period1": int(t_item["period"]), "subj1": t_item["subj"], "teacher1": t_item["teacher"],
                    "cls2": t_item["cls"], "date2": str(target_date), "period2": int(selected_opt[0]), "subj2": selected_opt[1], "teacher2": selected_opt[2]
                }
                save_swap_request(log_entry, auto_approve=True)
                st.session_state.swap_logs = load_swap_logs("APPROVED")
                st.session_state.action_ui = None
                st.toast("🔀 맞교환이 성공적으로 완료되었습니다!")
                st.rerun()
            if st.button("❌ 취소", use_container_width=True):
                st.session_state.action_ui = None
                st.rerun()
                
    elif ui_type == "SUB":
        st.markdown(f"#### 📝 스마트 대강 지정 (대상: **{t_item['date']} {t_item['period']}교시 [{t_item['cls']}] {t_item['subj']}({t_item['teacher']})**)")
        c_sub1, c_sub2, c_sub3 = st.columns([1, 1.5, 1])
        with c_sub1:
            reason = st.text_input("대강 사유 입력", placeholder="예: 출장, 연가")
        with c_sub2:
            busy_t = set(parsed_df[(parsed_df["요일"] == t_item["day"]) & (parsed_df["교시"] == int(t_item["period"]))]["교사"].unique())
            avail_t = [t for t in teacher_list if t not in busy_t and t != t_item['teacher']]
            if avail_t:
                selected_sub_t = st.selectbox("가능한 빈 교사 선택", avail_t)
            else:
                st.error("해당 교시에 가능한 교사가 없습니다.")
                selected_sub_t = None
        with c_sub3:
            st.write("")
            st.write("")
            if st.button("✅ 대강 확정", type="primary", use_container_width=True) and selected_sub_t and reason:
                save_sub_log({"날짜": t_item["date"], "요일": t_item["day"], "교시": int(t_item["period"]), "학급": t_item["cls"], "원교사": t_item["teacher"], "대강교사": selected_sub_t, "대강사유": reason, "단가": st.session_state.hourly_rate, "주차": st.session_state.week_offset})
                st.session_state.sub_logs = load_sub_logs()
                st.session_state.action_ui = None
                st.toast(f"📝 {selected_sub_t} 선생님으로 대강 지정 완료!")
                st.rerun()
            if st.button("❌ 취소", use_container_width=True):
                st.session_state.action_ui = None
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# 8. 메인 UI 탭 
if parsed_df is not None and not parsed_df.empty:
    is_admin = (mode == "관리자 모드 (수업교체/대강)") and st.session_state.admin_authenticated
    
    if is_admin:
        tab1, tab2, tab3 = st.tabs(["🗓️ 시간표 스마트 통합 관리", "📝 일일 대강 지정(수동 탭)", "📊 교사 시수 & 대강 수당"])
    else:
        tab1, = st.tabs(["🗓️ 시간표 조회 (전체/반/교사)"])

    with tab1:
        c_v1, c_v2 = st.columns([3, 1])
        with c_v1:
            view_mode = st.radio("조회 방식", ["전체 시간표 (가로: 학급 / 세로: 요일·교시)", "학급별 주간 시간표", "교사별 주간 시간표"], horizontal=True)
        with c_v2:
            st.write("")
            st.button("🖨️ 시간표 인쇄 / PDF 저장", on_click=lambda: st.components.v1.html("<script>window.print();</script>"))

        if view_mode == "전체 시간표 (가로: 학급 / 세로: 요일·교시)":
            if is_admin:
                st.info("💡 **스마트 관리**: 빈 곳 우클릭 시 **[수업 교체]**, **[대강 지정]** 메뉴가 뜨며, `Ctrl+C/V` 및 `Delete` 단축키도 지연 없이 작동합니다.")
                days = ["월", "화", "수", "목", "금"]
                classes = sorted(parsed_df["학급"].unique())
                sub_dict = {(log["날짜"], log["학급"], int(log["교시"])): log for log in st.session_state.sub_logs}
                grid_data = {}
                
                for d in days:
                    date_str = current_week_dates[d].strftime("%Y-%m-%d")
                    for p in range(1, 8):
                        for c in classes:
                            cell = parsed_df[(parsed_df["학급"] == c) & (parsed_df["요일"] == d) & (parsed_df["교시"] == p)]
                            key = f"{date_str}_{c}_{p}"
                            if not cell.empty:
                                row = cell.iloc[0]
                                sub_key = (date_str, c, p)
                                is_sub = sub_key in sub_dict
                                sub_teacher_val = sub_dict[sub_key]['대강교사'] if is_sub else ""
                                subj_val, teacher_val = row["과목"], row["교사"]
                                if is_sub and sub_teacher_val == "빈칸": subj_val, teacher_val = "", ""
                                grid_data[key] = {"date": date_str, "day": d, "cls": c, "period": p, "subj": subj_val, "teacher": teacher_val, "sub_teacher": sub_teacher_val, "is_swapped": bool(row.get("is_swapped", False)), "is_sub": is_sub}
                            else:
                                grid_data[key] = {"date": date_str, "day": d, "cls": c, "period": p, "subj": "", "teacher": "", "sub_teacher": "", "is_swapped": False, "is_sub": False}

                action_result = AdminGrid(grid_data=grid_data, classes=classes, copied_data=st.session_state.copied_data)

                # 무한 랙을 완벽 차단하는 'action_id' 검증 로직
                if action_result:
                    act_id = action_result.get("action_id")
                    if act_id and act_id != st.session_state.last_action_id:
                        st.session_state.last_action_id = act_id
                        act = action_result.get("act")
                        t_item = action_result.get("target")
                        c_item = st.session_state.copied_data
                        
                        if act == "NO_COPY_DATA":
                            st.toast("⚠️ 복사된 데이터가 없습니다. 먼저 셀을 선택하고 Ctrl+C를 누르세요.")
                        elif act == "COPY" and t_item:
                            if t_item.get("subj"):
                                st.session_state.copied_data = t_item
                                st.toast(f"📋 [{t_item.get('subj')}({t_item.get('teacher')})] 복사됨!")
                            else:
                                st.toast("⚠️ 빈 셀은 복사할 수 없습니다.")
                        elif act == "DELETE" and t_item:
                            t_date, t_cls, t_period = t_item.get("date"), t_item.get("cls"), int(t_item.get("period"))
                            day_kr = ["월","화","수","목","금"][pd.to_datetime(t_date).weekday()]
                            save_sub_log({"날짜": t_date, "요일": day_kr, "교시": t_period, "학급": t_cls, "원교사": t_item.get("teacher"), "대강교사": "빈칸", "대강사유": "관리자 삭제", "단가": 0, "주차": st.session_state.week_offset})
                            save_cell_override(t_date, day_kr, t_period, t_cls, "", "")
                            st.session_state.sub_logs = load_sub_logs()
                            st.toast(f"🗑️ [{t_cls}] {t_period}교시 완전 삭제(빈칸)")
                            st.rerun()
                        elif act == "REQ_SWAP" and t_item:
                            if not t_item.get("subj"): st.toast("⚠️ 빈 셀은 교체할 수 없습니다.")
                            else:
                                st.session_state.action_ui = {"type": "SWAP", "target": t_item}
                                st.rerun()
                        elif act == "REQ_SUB" and t_item:
                            if not t_item.get("subj"): st.toast("⚠️ 빈 셀에는 대강을 지정할 수 없습니다.")
                            else:
                                st.session_state.action_ui = {"type": "SUB", "target": t_item}
                                st.rerun()
                        elif act in ["PASTE_OVERWRITE", "PASTE_SWAP"] and c_item and t_item:
                            t_date, t_cls, t_period = t_item.get("date"), t_item.get("cls"), int(t_item.get("period"))
                            day_kr = ["월","화","수","목","금"][pd.to_datetime(t_date).weekday()]
                            c_teacher, c_subj = c_item.get("teacher"), c_item.get("subj")
                            conflict = parsed_df[(parsed_df["교사"] == c_teacher) & (parsed_df["요일"] == day_kr) & (parsed_df["교시"] == t_period) & (parsed_df["학급"] != t_cls)]
                            
                            if not conflict.empty:
                                st.toast(f"⚠️ 중복! {c_teacher} 선생님은 {day_kr}요일 {t_period}교시에 이미 수업이 있습니다.")
                            else:
                                if act == "PASTE_OVERWRITE":
                                    save_cell_override(t_date, day_kr, t_period, t_cls, c_subj, c_teacher)
                                    st.toast(f"📥 [{t_cls}] {t_period}교시에 [{c_subj}({c_teacher})] 이동 완료")
                                elif act == "PASTE_SWAP":
                                    save_swap_request({"cls1": c_item["cls"], "date1": c_item["date"], "period1": c_item["period"], "subj1": c_item["subj"], "teacher1": c_teacher, "cls2": t_cls, "date2": t_date, "period2": t_period, "subj2": t_item.get("subj"), "teacher2": t_item.get("teacher")}, auto_approve=True)
                                    st.session_state.swap_logs = load_swap_logs("APPROVED")
                                    st.toast(f"🔀 [{c_item['cls']}] ↔ [{t_cls}] 교체 완료")
                                st.rerun()
            else:
                st.markdown(build_merged_full_grid_html(parsed_df), unsafe_allow_html=True)

        elif view_mode == "학급별 주간 시간표":
            target_cls = st.selectbox("🎯 학급 선택", sorted(parsed_df["학급"].unique()))
            st.markdown(build_weekly_html_table(parsed_df, target_cls, filter_type="CLASS"), unsafe_allow_html=True)
        else:
            target_t = st.selectbox("👨‍🏫 교사 선택", teacher_list)
            st.markdown(build_weekly_html_table(parsed_df, target_t, filter_type="TEACHER"), unsafe_allow_html=True)

    if is_admin:
        with tab2:
            st.subheader("📝 수동 대강 지정 (일괄/특수 상황)")
            c_sub1, c_sub2 = st.columns(2)
            with c_sub1:
                sub_date = st.date_input("대강 날짜", date(2026, 8, 10))
                sub_day_kr = ["월", "화", "수", "목", "금", "토", "일"][sub_date.weekday()]
                sub_period = st.selectbox("교시", list(range(1, 8)))
                
                target_classes_df = parsed_df[(parsed_df["요일"] == sub_day_kr) & (parsed_df["교시"] == sub_period)]
                if not target_classes_df.empty:
                    target_cls_idx = st.selectbox("기존 수업 선택", target_classes_df.index, format_func=lambda x: f"[{target_classes_df.loc[x, '학급']}] {target_classes_df.loc[x, '과목']}({target_classes_df.loc[x, '교사']})")
                    selected_target = target_classes_df.loc[target_cls_idx]
                    orig_teacher, orig_cls, orig_subj = selected_target["교사"], selected_target["학급"], selected_target["과목"]
                else:
                    st.warning("수업 없음")
                    selected_target = None
            with c_sub2:
                if selected_target is not None:
                    busy_t = set(parsed_df[(parsed_df["요일"] == sub_day_kr) & (parsed_df["교시"] == sub_period)]["교사"].unique())
                    avail_t = [t for t in teacher_list if t not in busy_t]
                    if avail_t:
                        sub_teacher = st.selectbox("빈 교사 선택", avail_t)
                        sub_reason = st.text_input("사유", placeholder="출장 등")
                        if st.button("📝 대강 저장", use_container_width=True):
                            if not sub_reason: st.error("사유 필수")
                            else:
                                save_sub_log({"날짜": str(sub_date), "요일": sub_day_kr, "교시": int(sub_period), "학급": orig_cls, "원교사": orig_teacher, "대강교사": sub_teacher, "대강사유": sub_reason, "단가": st.session_state.hourly_rate, "주차": st.session_state.week_offset})
                                st.session_state.sub_logs = load_sub_logs()
                                st.success("저장 완료!")
                                st.rerun()
                    else: st.error("가능 교사 없음")

        with tab3:
            st.subheader("📊 교사별 주당 시수 & 기간별 대강일지 엑셀 출력")
            c_s1, c_s2 = st.columns([1, 1.8])
            with c_s1:
                tc = parsed_df["교사"].value_counts().reset_index()
                tc.columns = ["교사명", "주당 시수"]
                st.dataframe(tc, use_container_width=True)
            with c_s2:
                col_d1, col_d2 = st.columns(2)
                with col_d1: start_filter = st.date_input("조회 시작일", date(2026, 8, 1))
                with col_d2: end_filter = st.date_input("조회 종료일", date(2026, 8, 31))
                if len(st.session_state.sub_logs) > 0:
                    all_sub_df = pd.DataFrame(st.session_state.sub_logs)
                    all_sub_df["날짜_dt"] = pd.to_datetime(all_sub_df["날짜"]).dt.date
                    filtered_sub = all_sub_df[(all_sub_df["날짜_dt"] >= start_filter) & (all_sub_df["날짜_dt"] <= end_filter) & (all_sub_df["대강교사"] != "빈칸")].copy()
                    if not filtered_sub.empty:
                        export_df = filtered_sub[["날짜", "요일", "교시", "학급", "원교사", "대강교사", "대강사유", "단가"]].rename(columns={"날짜": "일자", "단가": "대강수당(원)"})
                        st.dataframe(export_df, use_container_width=True)
                        st.download_button("📥 대강일지 다운로드", export_df.to_csv(index=False).encode('utf-8-sig'), f"대강일지_{start_filter}.csv", "text/csv")
                    else: st.info("내역 없음")
                else: st.info("기록 없음")