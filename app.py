import streamlit as st
import pandas as pd
import sqlite3
import os
import streamlit.components.v1 as components
from datetime import datetime, timedelta, date

# 1. 페이지 설정 및 세션 초기화
st.set_page_config(page_title="TimeMaster - 학교 시간표 시스템", layout="wide")

if "copied_data" not in st.session_state:
    st.session_state.copied_data = None
if "grid_key" not in st.session_state:
    st.session_state.grid_key = 0
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

# 2. 공식 Streamlit 양방향 Custom Component 생성 엔진 (핵심 해결책)
# URL 조작 우회를 막고 JS -> Python 다이렉트 통신을 위한 로컬 HTML 컴포넌트 자동 생성
def init_custom_component():
    comp_dir = "admin_grid_component"
    os.makedirs(comp_dir, exist_ok=True)
    html_path = os.path.join(comp_dir, "index.html")
    
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; background-color: white; }
        .admin-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; background-color: #ffffff; table-layout: fixed; user-select: none; }
        .admin-table th { background-color: #1e3a8a; color: #ffffff; padding: 10px 4px; font-weight: bold; border: 1px solid #1e3a8a; border-bottom: 3.5px solid #0f172a; border-right: 3.5px solid #0f172a; }
        .admin-table td { background-color: #ffffff; padding: 6px 2px; border-right: 3.5px solid #0f172a; border-bottom: 1px solid #cbd5e1; height: 60px; vertical-align: middle; cursor: pointer; position: relative; }
        .admin-table td:hover { filter: brightness(0.92); outline: 2px solid #2563eb; z-index: 10; }
        .admin-table td.selected { outline: 3.5px solid #ef4444 !important; background-color: #fef2f2 !important; z-index: 20; }
        .day-col-js { background-color: #1e3a8a !important; color: #ffffff !important; font-weight: 800; width: 4%; border-right: 3.5px solid #0f172a !important; border-bottom: 3.5px solid #0f172a !important; }
        .period-col-js { background-color: #f1f5f9 !important; font-weight: bold; color: #1e293b; width: 5%; border-right: 3.5px solid #0f172a !important; }
        .bg-sub { background-color: #ffedd5 !important; }
        .bg-swap { background-color: #fef08a !important; }
        .context-menu { display: none; position: fixed; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 220px; z-index: 10000; padding: 6px 0; text-align: left; }
        .context-menu-item { padding: 10px 16px; font-size: 13px; font-weight: 600; color: #1e293b; cursor: pointer; display: flex; align-items: center; justify-content: space-between; }
        .context-menu-item:hover { background-color: #f1f5f9; color: #2563eb; }
        .context-menu-divider { height: 1px; background-color: #e2e8f0; margin: 4px 0; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10001; justify-content: center; align-items: center; }
        .modal-content { background: white; padding: 20px; border-radius: 12px; width: 360px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); text-align: left; }
        .modal-btn { display: block; width: 100%; margin: 8px 0; padding: 10px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-align: center; }
        .btn-overwrite { background: #2563eb; color: white; }
        .btn-swap-paste { background: #eab308; color: white; }
        .btn-close { background: #94a3b8; color: white; margin-top: 15px; }
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

        let gridData = {};
        let classes = [];
        let copiedData = null;
        let selectedKey = null;
        const days = ["월", "화", "수", "목", "금"];

        window.addEventListener("message", function(event) {
            if (event.source !== window.parent) return;
            if (event.data.type === "streamlit:render") {
                gridData = event.data.args.grid_data;
                classes = event.data.args.classes;
                copiedData = event.data.args.copied_data;
                renderGrid();
                setTimeout(() => Streamlit.setFrameHeight(document.body.scrollHeight + 30), 100);
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
                        
                        if(!key || !gridData[key]) {
                            td.innerText = "-"; tr.appendChild(td); return;
                        }

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
                        td.oncontextmenu = (e) => { e.preventDefault(); selectCell(key, td); showContextMenu(e.clientX, e.clientY); };
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                }
            });
        }

        function selectCell(key, element) {
            document.querySelectorAll(".admin-table td").forEach(td => td.classList.remove("selected"));
            selectedKey = key;
            if(element) element.classList.add("selected");
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

        function openPasteModal() {
            if(!copiedData || !selectedKey) return;
            const target = gridData[selectedKey];
            document.getElementById("pasteModalInfo").innerHTML = `복사된 수업: <b>${copiedData.subj} (${copiedData.teacher})</b><br>붙여넣을 대상: <b>[${target.cls}] ${target.day}요일 ${target.period}교시</b>`;
            document.getElementById("pasteModal").style.display = "flex";
        }

        function closePasteModal() { document.getElementById("pasteModal").style.display = "none"; }

        function onMenuAction(actionType) {
            hideContextMenu();
            closePasteModal();
            if(!selectedKey || !gridData[selectedKey]) return;
            // 파이썬으로 다이렉트 데이터 전송!
            Streamlit.setComponentValue({ act: actionType, target: gridData[selectedKey] });
        }

        window.onclick = (e) => { if(!e.target.closest("#contextMenu")) hideContextMenu(); };

        window.addEventListener("keydown", (e) => {
            if(!selectedKey) return;
            if(e.key === "Delete" || e.key === "Backspace") { onMenuAction("DELETE"); }
            else if(e.ctrlKey && e.key === "c") { onMenuAction("COPY"); }
            else if(e.ctrlKey && e.key === "v") {
                if(copiedData) openPasteModal();
                else alert("⚠️ 복사된 데이터가 없습니다. 먼저 셀을 선택하고 Ctrl+C를 누르세요.");
            }
        });
    </script>
</head>
<body onload="Streamlit.setComponentReady()">
    <table class="admin-table">
        <thead><tr id="grid-head-tr"></tr></thead>
        <tbody id="grid-body"></tbody>
    </table>
    <div id="contextMenu" class="context-menu">
        <div class="context-menu-item" onclick="onMenuAction('DELETE')">🗑️ 수업 삭제 (휴강)</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" onclick="onMenuAction('COPY')">📋 수업 복사 (Ctrl+C)</div>
        <div id="pasteOverwriteItem" class="context-menu-item" style="display:none;" onclick="onMenuAction('PASTE_OVERWRITE')">📥 복사본 덮어쓰기</div>
        <div id="pasteSwapItem" class="context-menu-item" style="display:none;" onclick="onMenuAction('PASTE_SWAP')">🔀 복사본과 맞교환</div>
    </div>
    <div id="pasteModal" class="modal-overlay">
        <div class="modal-content">
            <h4 style="margin-top:0; color:#1e3a8a;">📋 붙여넣기 방식 선택</h4>
            <p id="pasteModalInfo" style="font-size:13px; color:#475569;"></p>
            <button class="modal-btn btn-overwrite" onclick="onMenuAction('PASTE_OVERWRITE')">1. 덮어쓰기 (기존 수업 제거 후 배치)</button>
            <button class="modal-btn btn-swap-paste" onclick="onMenuAction('PASTE_SWAP')">2. 교체하기 (원래 수업과 서로 교환)</button>
            <button class="modal-btn btn-close" onclick="closePasteModal()">취소</button>
        </div>
    </div>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return components.declare_component("AdminGrid", path=comp_dir)

AdminGrid = init_custom_component()

# 3. DB 초기화 및 관리
DB_FILE = "timemaster_data.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sub_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, s_date TEXT, s_day TEXT, s_period INTEGER, t_cls TEXT, o_teacher TEXT, s_teacher TEXT, reason TEXT, rate INTEGER, week_offset INTEGER)""")
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

# 5. 기초 데이터 로드 및 적용
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

def apply_swaps(df, current_week_dates):
    if df is None or df.empty: return df
    date_to_day = {v.strftime("%Y-%m-%d"): k for k, v in current_week_dates.items()}
    df["is_swapped"] = False
    for swap in st.session_state.swap_logs:
        d1, d2 = swap["date1"], swap["date2"]
        if d1 in date_to_day and d2 in date_to_day:
            day1, day2 = date_to_day[d1], date_to_day[d2]
            m1, m2 = (df["학급"] == swap["cls1"]) & (df["요일"] == day1) & (df["교시"] == swap["period1"]), (df["학급"] == swap["cls2"]) & (df["요일"] == day2) & (df["교시"] == swap["period2"])
            if m1.any() and m2.any():
                idx1, idx2 = df[m1].index[0], df[m2].index[0]
                df.loc[idx1, "과목"], df.loc[idx1, "교사"], df.loc[idx2, "과목"], df.loc[idx2, "교사"] = df.loc[idx2, "과목"], df.loc[idx2, "교사"], df.loc[idx1, "과목"], df.loc[idx1, "교사"]
                df.loc[idx1, "is_swapped"], df.loc[idx2, "is_swapped"] = True, True
    return df

parsed_df = apply_swaps(p_df, current_week_dates)

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

# 6. 메인 UI 및 양방향 통신 핸들러 (코드 하이라이트!)
if parsed_df is not None and not parsed_df.empty:
    is_admin = (mode == "관리자 모드 (수업교체/대강)") and st.session_state.admin_authenticated
    tab1, tab2 = st.tabs(["🗓️ 통합 시간표 관리", "🔄 교환/대강/통계"])

    with tab1:
        st.info("💡 **가이드**: 셀 클릭 후 Delete(삭제), Ctrl+C(복사), Ctrl+V(붙여넣기) 및 마우스 우클릭 스마트 메뉴 지원")
        
        # 데이터를 딕셔너리로 래핑해서 JS로 전송
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
                        grid_data[key] = {
                            "date": date_str, "day": d, "cls": c, "period": p, "subj": row["과목"], "teacher": row["교사"],
                            "sub_teacher": sub_dict[sub_key]['대강교사'] if is_sub else "", "is_swapped": bool(row.get("is_swapped", False)), "is_sub": is_sub
                        }
                    else:
                        grid_data[key] = {"date": date_str, "day": d, "cls": c, "period": p, "subj": "", "teacher": "", "sub_teacher": "", "is_swapped": False, "is_sub": False}

        # ⚡ 핵심: JS 컴포넌트 렌더링 및 데이터 수신 ⚡
        action_result = AdminGrid(grid_data=grid_data, classes=classes, copied_data=st.session_state.copied_data, key=f"grid_{st.session_state.grid_key}")

        if action_result:
            act = action_result.get("act")
            t_item = action_result.get("target")
            c_item = st.session_state.copied_data
            
            t_date = t_item.get("date")
            t_cls = t_item.get("cls")
            t_period = int(t_item.get("period"))
            t_subj = t_item.get("subj")
            t_teacher = t_item.get("teacher")

            if act == "COPY":
                st.session_state.copied_data = t_item
                st.session_state.grid_key += 1
                st.rerun()

            elif act == "DELETE":
                day_kr = ["월","화","수","목","금"][pd.to_datetime(t_date).weekday()]
                save_sub_log({"날짜": t_date, "요일": day_kr, "교시": t_period, "학급": t_cls, "원교사": t_teacher, "대강교사": "휴강", "대강사유": "관리자 삭제", "단가": 0, "주차": st.session_state.week_offset})
                st.session_state.sub_logs = load_sub_logs()
                st.session_state.grid_key += 1
                st.rerun()

            elif act == "PASTE_OVERWRITE" and c_item:
                day_kr = ["월","화","수","목","금"][pd.to_datetime(t_date).weekday()]
                save_sub_log({"날짜": t_date, "요일": day_kr, "교시": t_period, "학급": t_cls, "원교사": t_teacher, "대강교사": c_item["teacher"], "대강사유": f"복사({c_item['subj']})", "단가": st.session_state.hourly_rate, "주차": st.session_state.week_offset})
                st.session_state.sub_logs = load_sub_logs()
                st.session_state.grid_key += 1
                st.rerun()

            elif act == "PASTE_SWAP" and c_item:
                save_swap_request({"cls1": c_item["cls"], "date1": c_item["date"], "period1": c_item["period"], "subj1": c_item["subj"], "teacher1": c_item["teacher"], "cls2": t_cls, "date2": t_date, "period2": t_period, "subj2": t_subj, "teacher2": t_teacher}, auto_approve=True)
                st.session_state.swap_logs = load_swap_logs("APPROVED")
                st.session_state.grid_key += 1
                st.rerun()