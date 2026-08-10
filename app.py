import streamlit as st
import pandas as pd
import sqlite3
import os
import streamlit.components.v1 as components
from datetime import datetime, timedelta, date

# 1. 페이지 기본 설정 및 세션 초기화
st.set_page_config(page_title="TimeMaster - 모던 시간표 시스템", layout="wide")

if "copied_data" not in st.session_state: st.session_state.copied_data = None
if "last_action_id" not in st.session_state: st.session_state.last_action_id = None
if "school_name" not in st.session_state: st.session_state.school_name = "경남해양고등학교"
if "hourly_rate" not in st.session_state: st.session_state.hourly_rate = 13000
if "week_offset" not in st.session_state: st.session_state.week_offset = 0
if "raw_df" not in st.session_state: st.session_state.raw_df = None
if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False

if "view_mode_val" not in st.session_state: st.session_state.view_mode_val = "전체 시간표"
if "sel_cls_val" not in st.session_state: st.session_state.sel_cls_val = None
if "sel_t_val" not in st.session_state: st.session_state.sel_t_val = None

# 2. 🖨️ A4 1페이지 출력 보정 & 🚫 visibility 텍스트 완벽 제거 CSS
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', -apple-system, sans-serif !important; }
    
    /* 🚫 visibility / keyboard_double 텍스트 노출 완벽 박멸 패치 */
    div[data-testid="stInputVisibilityButton"],
    div[data-testid="stInputVisibilityButton"] *,
    button[aria-label="Visibility"],
    [data-testid="stSidebarCollapseButton"] {
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
        display: none !important;
    }

    /* 🖨️ 인쇄 전용 스타일 */
    @media print {
        @page { size: A4 landscape; margin: 8mm; }
        html, body { background-color: white !important; zoom: 92%; margin: 0 !important; padding: 0 !important; height: auto !important; overflow: visible !important; }
        header, footer, [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"], 
        [data-testid="stDecoration"], div[role="tablist"], [data-testid="stRadio"], [data-testid="stSelectbox"], 
        [data-testid="stAlert"], [data-testid="stToastContainer"], iframe, .stButton, .print-hide, h1.print-hide { 
            display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; border: none !important;
        }
        .main, .main .block-container, [data-testid="stVerticalBlock"] { padding: 0 !important; margin: 0 !important; max-width: 100% !important; width: 100% !important; gap: 0 !important; }
        .print-title { display: block !important; margin-top: 0 !important; margin-bottom: 10px !important; padding: 0 !important; }
        .print-title h3 { font-size: 20px !important; margin: 0 !important; color: #000 !important; }
        .table-container { display: block !important; box-shadow: none !important; border: 2px solid #000 !important; margin: 0 !important; padding: 2px !important; page-break-before: avoid !important; page-break-inside: avoid !important; }
        .unified-table { width: 100% !important; border-collapse: separate !important; border-spacing: 2px !important; }
        .unified-table th { background-color: #f1f5f9 !important; color: #000 !important; border: 1px solid #000 !important; -webkit-print-color-adjust: exact; }
        .unified-table td { border: 1px solid #64748b !important; height: 50px !important; }
        .day-col { background-color: #e0f2fe !important; color: #000 !important; -webkit-print-color-adjust: exact; }
        .period-col { background-color: #f1f5f9 !important; color: #000 !important; -webkit-print-color-adjust: exact; }
        .bg-substitute { background-color: #ffedd5 !important; -webkit-print-color-adjust: exact; }
        .bg-swapped { background-color: #fef9c3 !important; -webkit-print-color-adjust: exact; }
        .badge-sub { background-color: #f97316 !important; color: white !important; -webkit-print-color-adjust: exact; }
        .badge-swap { background-color: #eab308 !important; color: white !important; -webkit-print-color-adjust: exact; }
    }
    
    /* 웹 화면 전용 모던 CSS */
    .table-container { width: 100%; overflow-x: auto; margin-bottom: 20px; border-radius: 18px; border: 2px solid #f1f5f9; box-shadow: 0 8px 20px rgba(0,0,0,0.03); background: white; padding: 6px; }
    .unified-table { width: 100%; border-collapse: separate; border-spacing: 4px; text-align: center; font-size: 13px; table-layout: fixed; }
    .unified-table th { background-color: #f8fafc !important; color: #475569 !important; padding: 10px 4px; font-weight: 800; font-size: 13px; border-radius: 10px; }
    .unified-table td { background-color: #f8fafc; padding: 6px 1px; border-radius: 10px; vertical-align: middle; height: 58px; word-break: break-all; transition: transform 0.1s ease; }
    
    td.day-col { background-color: #e0f2fe !important; color: #0369a1 !important; font-weight: 800 !important; width: 4% !important; vertical-align: middle !important; border-radius: 10px; padding: 4px 2px !important; }
    .day-col b { font-size: 16px !important; display: block !important; color: #0284c7 !important; }
    .day-col span { font-size: 10px !important; font-weight: 700 !important; display: block !important; color: #38bdf8 !important; }
    .period-col { background-color: #f1f5f9 !important; font-weight: 800; color: #475569 !important; width: 5% !important; font-size: 12px; border-radius: 10px; }
    
    .subject-name { font-size: 13.5px !important; font-weight: 800 !important; color: #0f172a !important; line-height: 1.1; letter-spacing: -0.3px; }
    .teacher-name { font-size: 10.5px !important; font-weight: 700 !important; color: #64748b !important; margin-top: 2px; }
    
    .bg-swapped { background-color: #fef9c3 !important; }
    .bg-substitute { background-color: #ffedd5 !important; }
    
    .status-badge { font-size: 9px; padding: 1px 5px; border-radius: 8px; font-weight: 800; display: inline-block; margin-bottom: 2px; }
    .badge-swap { background-color: #eab308 !important; color: white !important; }
    .badge-sub { background-color: #f97316 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# 3. ⚡ 우클릭 팝업 일체형 UI 컴포넌트
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
        .admin-table { width: 100%; border-collapse: separate; border-spacing: 4px; text-align: center; font-size: 13px; background-color: #ffffff; table-layout: fixed; user-select: none; }
        .admin-table th { background-color: #f8fafc; color: #475569; padding: 10px 4px; font-weight: 800; border-radius: 10px; }
        .admin-table td { background-color: #f8fafc; padding: 6px 2px; border-radius: 10px; height: 58px; vertical-align: middle; cursor: pointer; position: relative; }
        .admin-table td:hover { filter: brightness(0.95); outline: 2px solid #3b82f6; }
        .admin-table td.selected { outline: 3px solid #ef4444 !important; background-color: #fef2f2 !important; }
        .day-col-js { background-color: #e0f2fe !important; color: #0284c7 !important; font-weight: 800; width: 4%; border-radius: 10px; }
        .period-col-js { background-color: #f1f5f9 !important; font-weight: 800; color: #475569; width: 5%; border-radius: 10px; }
        .bg-sub { background-color: #ffedd5 !important; }
        .bg-swap { background-color: #fef9c3 !important; }
        
        .context-menu { display: none; position: absolute; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.12); width: 200px; z-index: 10000; padding: 6px 0; text-align: left; }
        .context-menu-item { padding: 10px 16px; font-size: 13px; font-weight: 700; color: #1e293b; cursor: pointer; display: flex; align-items: center; justify-content: space-between; }
        .context-menu-item:hover { background-color: #f1f5f9; color: #2563eb; }
        .context-menu-divider { height: 1px; background-color: #e2e8f0; margin: 4px 0; }
        
        /* 팝업 일체형 디자인 */
        .popover { display: none; position: absolute; background: white; border: 2.5px solid #0284c7; border-radius: 16px; padding: 14px; width: 280px; box-shadow: 0 12px 30px rgba(0,0,0,0.18); z-index: 10001; text-align: left; }
        .pop-btn { display: block; width: 100%; margin: 6px 0; padding: 9px; border: none; border-radius: 10px; font-weight: bold; font-size: 12.5px; cursor: pointer; text-align: center; }
        .btn-primary { background: #0284c7; color: white; }
        .btn-swap { background: #eab308; color: white; }
        .btn-close { background: #94a3b8; color: white; margin-top: 6px; }
        .pop-input { width: 95%; padding: 7px; margin: 5px 0 10px 0; border: 1.5px solid #cbd5e1; border-radius: 8px; font-size: 12px; font-weight: 600; }
        
        #jsToast { position: fixed; bottom: 20px; right: 20px; background: #1e293b; color: white; padding: 12px 20px; border-radius: 10px; font-weight: bold; font-size: 13px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); display: none; z-index: 100000; transition: opacity 0.3s; }
    </style>
    <script>
        function sendMessageToStreamlit(data) {
            window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: "streamlit:setComponentValue"}, {value: data}), "*");
        }
        const Streamlit = {
            setComponentReady: function() { window.parent.postMessage({isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1}, "*"); },
            setFrameHeight: function(h) { window.parent.postMessage({isStreamlitMessage: true, type: "streamlit:setFrameHeight", height: h}, "*"); }
        };

        let gridData = {}; let classes = []; let teacherList = []; let copiedData = null;
        let selectedKey = null; let selectedTdElement = null; const days = ["월", "화", "수", "목", "금"];

        window.addEventListener("message", function(event) {
            if (event.source !== window.parent) return;
            if (event.data.type === "streamlit:render") {
                gridData = event.data.args.grid_data;
                classes = event.data.args.classes;
                teacherList = event.data.args.teacher_list || [];
                copiedData = event.data.args.copied_data || null;
                renderGrid();
                setTimeout(() => Streamlit.setFrameHeight(document.body.scrollHeight + 80), 50);
            }
        });

        function showToast(msg) {
            const toast = document.getElementById("jsToast");
            toast.innerText = msg; toast.style.display = "block"; toast.style.opacity = "1";
            setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.style.display="none", 300); }, 2000);
        }

        function renderGrid() {
            const tbody = document.getElementById("grid-body"); tbody.innerHTML = "";
            const thead_tr = document.getElementById("grid-head-tr");
            thead_tr.innerHTML = '<th style="width: 4%;">요일</th><th style="width: 5%;">교시</th>';
            classes.forEach(c => { const th = document.createElement("th"); th.innerText = c; thead_tr.appendChild(th); });

            days.forEach(d => {
                for(let p = 1; p <= 7; p++) {
                    const tr = document.createElement("tr");
                    if(p === 1) { const tdDay = document.createElement("td"); tdDay.rowSpan = 7; tdDay.className = "day-col-js"; tdDay.innerHTML = `<b>${d}</b>`; tr.appendChild(tdDay); }
                    const tdP = document.createElement("td"); tdP.className = "period-col-js"; tdP.innerText = `${p}`; tr.appendChild(tdP);

                    classes.forEach(c => {
                        const td = document.createElement("td");
                        const key = Object.keys(gridData).find(k => String(gridData[k].day) === String(d) && String(gridData[k].period) === String(p) && String(gridData[k].cls) === String(c));
                        if(!key || !gridData[key]) { td.innerText = "-"; tr.appendChild(td); return; }

                        const item = gridData[key]; td.id = key;
                        if(item.is_sub) td.className = "bg-sub"; else if(item.is_swapped) td.className = "bg-swap";
                        
                        let txt = "-";
                        if(item.subj) {
                            if(item.is_sub) txt = `<span style="font-size:9px; background:#f97316; color:white; padding:1px 4px; border-radius:6px; font-weight:800;">대강</span><br><b style="font-size:13px;">${item.subj}</b><br><span style="font-size:10px; color:#64748b;">(${item.sub_teacher})</span>`;
                            else if(item.is_swapped) txt = `<span style="font-size:9px; background:#eab308; color:white; padding:1px 4px; border-radius:6px; font-weight:800;">변동</span><br><b style="font-size:13px;">${item.subj}</b><br><span style="font-size:10px; color:#64748b;">(${item.teacher})</span>`;
                            else txt = `<b style="font-size:13.5px; color:#0f172a;">${item.subj}</b><br><span style="color:#64748b; font-size:10.5px; font-weight:600;">(${item.teacher})</span>`;
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
            selectedKey = key; selectedTdElement = element; if(element) element.classList.add("selected");
            hideAllPopups();
        }

        function positionPopup(popId) {
            const pop = document.getElementById(popId);
            const rect = selectedTdElement.getBoundingClientRect();
            let popLeft = rect.left + window.pageXOffset;
            let popTop = rect.bottom + window.pageYOffset + 5;
            if(popLeft + 290 > window.innerWidth) popLeft = window.innerWidth - 300;
            pop.style.left = `${popLeft}px`; pop.style.top = `${popTop}px`; pop.style.display = "block";
        }

        function showContextMenu(x, y) {
            const menu = document.getElementById("contextMenu");
            document.getElementById("pasteMenuBtn").style.display = copiedData ? "flex" : "none";
            menu.style.left = `${x}px`; menu.style.top = `${y}px`; menu.style.display = "block";
        }

        function hideAllPopups() {
            document.getElementById("contextMenu").style.display = "none";
            document.getElementById("pastePopover").style.display = "none";
            document.getElementById("crossSwapPopover").style.display = "none";
            document.getElementById("subPopover").style.display = "none";
        }

        function openPastePopover() {
            hideAllPopups();
            if(!copiedData || !selectedKey) return;
            document.getElementById("pastePopInfo").innerHTML = `복사: <b>${copiedData.subj}(${copiedData.teacher})</b><br>대상: <b>[${gridData[selectedKey].cls}] ${gridData[selectedKey].day} ${gridData[selectedKey].period}교시</b>`;
            positionPopup("pastePopover");
        }

        /* 📍 팝업 내부 스마트 날짜 기반 후보 자동 추출 */
        function openCrossSwapPopover() {
            hideAllPopups();
            if(!selectedKey) return;
            const t = gridData[selectedKey];
            if(!t.subj) { showToast("⚠️ 빈 셀은 교체할 수 없습니다."); return; }
            document.getElementById("crossSwapPopInfo").innerHTML = `교체 기준: <b>[${t.cls}] ${t.subj}(${t.teacher})</b>`;
            const dInput = document.getElementById("crossSwapDateInput");
            dInput.value = t.date;
            updateSwapCandidates();
            positionPopup("crossSwapPopover");
        }

        function updateSwapCandidates() {
            const t = gridData[selectedKey];
            const selDate = document.getElementById("crossSwapDateInput").value;
            const candSelect = document.getElementById("swapCandidateSelect");
            candSelect.innerHTML = "";
            
            if(!selDate) return;
            
            const targetDayNum = new Date(selDate).getDay(); // 0:일, 6:토
            if(targetDayNum === 0 || targetDayNum === 6) {
                candSelect.innerHTML = '<option value="">주말은 선택 불가</option>';
                return;
            }
            
            const dayNames = ["일", "월", "화", "수", "목", "금", "토"];
            const targetDayKr = dayNames[targetDayNum];
            
            // 해당 날짜 동일 학급 수업 검색
            const candidates = Object.values(gridData).filter(item => 
                String(item.cls) === String(t.cls) && 
                String(item.day) === String(targetDayKr) && 
                item.subj !== "" && item.subj !== "-"
            );
            
            if(candidates.length === 0) {
                candSelect.innerHTML = '<option value="">교체 가능한 수업 없음</option>';
            } else {
                candidates.forEach(c => {
                    if(c.date === t.date && c.period === t.period) return; // 자기 자신 제외
                    const opt = document.createElement("option");
                    opt.value = JSON.stringify({period2: c.period, subj2: c.subj, teacher2: c.teacher});
                    opt.innerText = `${c.period}교시 - ${c.subj} (${c.teacher})`;
                    candSelect.appendChild(opt);
                });
            }
        }

        function submitSmartSwap() {
            const dateVal = document.getElementById("crossSwapDateInput").value;
            const candVal = document.getElementById("swapCandidateSelect").value;
            if(!candVal) { showToast("⚠️ 교체할 수업을 선택하세요."); return; }
            
            const target2 = JSON.parse(candVal);
            dispatchAction('EXECUTE_CROSS_SWAP', {
                s_date2: dateVal,
                period2: target2.period2,
                subj2: target2.subj2,
                teacher2: target2.teacher2
            });
        }

        function openSubPopover() {
            hideAllPopups();
            if(!selectedKey) return;
            const t = gridData[selectedKey];
            if(!t.subj) { showToast("⚠️ 빈 셀에는 대강을 지정할 수 없습니다."); return; }
            document.getElementById("subPopInfo").innerHTML = `대강 대상: <b>[${t.cls}] ${t.subj} (${t.teacher})</b>`;
            
            const busyTeachers = Object.values(gridData).filter(i => String(i.day) === String(t.day) && Number(i.period) === Number(t.period) && i.teacher).map(i => i.teacher);
            const avail = teacherList.filter(tea => !busyTeachers.includes(tea) && tea !== t.teacher);
            const sel = document.getElementById("subTeacherSelect"); sel.innerHTML = "";
            if(avail.length === 0) { sel.innerHTML = '<option value="">가능한 교사 없음</option>'; } 
            else { avail.forEach(tea => { const opt = document.createElement("option"); opt.value = tea; opt.innerText = tea; sel.appendChild(opt); }); }
            positionPopup("subPopover");
        }

        function copyCurrentCell() {
            const t = gridData[selectedKey];
            if(t && t.subj) {
                copiedData = t; 
                showToast(`📋 복사 완료: ${t.subj}(${t.teacher})`);
                dispatchAction("COPY"); 
            } else { showToast("⚠️ 빈 셀은 복사 불가"); hideAllPopups(); }
        }

        function dispatchAction(act, extraData = {}) {
            hideAllPopups();
            const payload = Object.assign({ action_id: Date.now().toString(), act: act, target: gridData[selectedKey], copiedData: copiedData }, extraData);
            sendMessageToStreamlit(payload);
        }

        window.onclick = (e) => { if(!e.target.closest(".context-menu") && !e.target.closest(".popover")) hideAllPopups(); };

        window.addEventListener("keydown", (e) => {
            if(!selectedKey) return;
            if(e.key === "Delete" || e.key === "Backspace") {
                selectedTdElement.innerHTML = "-"; selectedTdElement.className = ""; 
                showToast("🗑️ 삭제 완료");
                dispatchAction("DELETE");
            }
            else if(e.ctrlKey && e.key === "c") { copyCurrentCell(); }
            else if(e.ctrlKey && e.key === "v") {
                if(copiedData) openPastePopover();
                else showToast("⚠️ 복사된 데이터가 없습니다.");
            }
        });
    </script>
</head>
<body onload="Streamlit.setComponentReady()">
    <div id="jsToast"></div>
    <table class="admin-table">
        <thead><tr id="grid-head-tr"></tr></thead><tbody id="grid-body"></tbody>
    </table>
    
    <div id="contextMenu" class="context-menu">
        <div class="context-menu-item" onclick="dispatchAction('DELETE')">🗑️ 수업 삭제 (빈칸)</div>
        <div class="context-menu-item" onclick="copyCurrentCell()">📋 수업 복사 (Ctrl+C)</div>
        <div id="pasteMenuBtn" class="context-menu-item" style="display:none;" onclick="openPastePopover()">📥 붙여넣기 (이동/교체)</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" onclick="openCrossSwapPopover()">🔄 팝업 일체형 수업 교체</div>
        <div class="context-menu-item" onclick="openSubPopover()">📝 스마트 대강 지정</div>
    </div>
    
    <div id="pastePopover" class="popover">
        <div style="font-weight:bold; color:#0284c7; margin-bottom:4px;">📋 붙여넣기 방식 선택</div>
        <div id="pastePopInfo" style="font-size:12px; color:#475569; margin-bottom:8px;"></div>
        <button class="pop-btn btn-primary" onclick="dispatchAction('PASTE_OVERWRITE')">1. 수업 이동 (덮어쓰기)</button>
        <button class="pop-btn btn-swap" onclick="dispatchAction('PASTE_SWAP')">2. 맞교환 (서로 교체)</button>
        <button class="pop-btn btn-close" onclick="hideAllPopups()">취소</button>
    </div>

    <!-- 📍 팝업 내부 통합 수업 교체 창 -->
    <div id="crossSwapPopover" class="popover">
        <div style="font-weight:bold; color:#0284c7; margin-bottom:4px;">🔄 스마트 수업 교체</div>
        <div id="crossSwapPopInfo" style="font-size:12px; color:#475569; margin-bottom:8px;"></div>
        
        <label style="font-size:11px; font-weight:bold; color:#334155;">1. 교체할 날짜 선택:</label>
        <input type="date" id="crossSwapDateInput" class="pop-input" onchange="updateSwapCandidates()">
        
        <label style="font-size:11px; font-weight:bold; color:#334155;">2. 교체 대상 수업 선택:</label>
        <select id="swapCandidateSelect" class="pop-input"></select>
        
        <button class="pop-btn btn-swap" onclick="submitSmartSwap()">✅ 맞교환 즉시 확정</button>
        <button class="pop-btn btn-close" onclick="hideAllPopups()">취소</button>
    </div>

    <div id="subPopover" class="popover">
        <div style="font-weight:bold; color:#0284c7; margin-bottom:4px;">📝 스마트 대강 지정</div>
        <div id="subPopInfo" style="font-size:12px; color:#475569; margin-bottom:6px;"></div>
        <label style="font-size:11px; font-weight:bold;">대강 사유:</label>
        <input type="text" id="subReasonInput" class="pop-input" placeholder="출장, 공결 등">
        <label style="font-size:11px; font-weight:bold;">가능한 교사:</label>
        <select id="subTeacherSelect" class="pop-input"></select>
        <button class="pop-btn btn-primary" onclick="dispatchAction('SUB_DIRECT', {sub_t: document.getElementById('subTeacherSelect').value, sub_r: document.getElementById('subReasonInput').value})">대강 저장 적용</button>
        <button class="pop-btn btn-close" onclick="hideAllPopups()">취소</button>
    </div>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return components.declare_component("AdminGrid", path=comp_dir)

AdminGrid = init_custom_component()

# 4. DB 및 상태 관리
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

def approve_swap_request(req_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE swap_logs SET status = 'APPROVED' WHERE id = ?", (req_id,))
    conn.commit()
    conn.close()

def clear_all_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sub_logs"); c.execute("DELETE FROM swap_logs"); c.execute("DELETE FROM cell_overrides")
    conn.commit()
    conn.close()

def reset_date_range(start_date, end_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sub_logs WHERE s_date BETWEEN ? AND ?", (start_date, end_date))
    c.execute("DELETE FROM cell_overrides WHERE s_date BETWEEN ? AND ?", (start_date, end_date))
    c.execute("DELETE FROM swap_logs WHERE (date1 BETWEEN ? AND ?) OR (date2 BETWEEN ? AND ?)", (start_date, end_date, start_date, end_date))
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

# 5. 사이드바
st.sidebar.title(f"🏫 {st.session_state.school_name}")
mode = st.sidebar.radio("접속 모드", ["학생/교사 시간표 보기", "관리자 모드 (수업교체/대강)"])
if mode == "관리자 모드 (수업교체/대강)":
    if not st.session_state.admin_authenticated:
        pin = st.sidebar.text_input("관리자 비밀번호 입력", type="password")
        if pin == "3060": st.session_state.admin_authenticated = True; st.sidebar.success("관리자 로그인 완료!"); st.rerun()
        elif pin != "": st.sidebar.error("비밀번호가 일치하지 않습니다."); mode = "학생/교사 시간표 보기"

# 6. 파싱 및 병합
DEFAULT_EXCEL = "2026년 2학기 시간표.xlsx"
if st.session_state.raw_df is None and os.path.exists(DEFAULT_EXCEL): st.session_state.raw_df = pd.read_excel(DEFAULT_EXCEL)

if mode == "관리자 모드 (수업교체/대강)" and st.session_state.admin_authenticated:
    with st.expander("⚙️ 시스템 설정 및 데이터 관리"):
        c_s, c_r = st.columns(2)
        with c_s:
            ns = st.text_input("학교명 변경", value=st.session_state.school_name)
            if ns != st.session_state.school_name: st.session_state.school_name = ns; st.rerun()
        with c_r:
            st.session_state.hourly_rate = st.number_input("대강비 단가(원)", value=st.session_state.hourly_rate, step=1000)

        up_file = st.file_uploader("새 기초 시간표 엑셀 업로드 (.xlsx)", type=["xlsx"])
        if up_file is not None:
            try: st.session_state.raw_df = pd.read_excel(up_file); st.success("업데이트 완료!")
            except Exception as e: st.error(f"파일 오류: {e}")

        st.markdown("---")
        st.markdown("##### 🧹 특정 기간 변경사항 초기화 (기초 시간표로 복구)")
        c_r1, c_r2, c_r3 = st.columns([1, 1, 1.5])
        with c_r1: reset_start = st.date_input("초기화 시작일", current_week_dates["월"])
        with c_r2: reset_end = st.date_input("초기화 종료일", current_week_dates["금"])
        with c_r3:
            st.write("")
            st.write("")
            if st.button("🔥 선택 기간만 초기화", use_container_width=True):
                reset_date_range(str(reset_start), str(reset_end))
                st.session_state.sub_logs = load_sub_logs()
                st.session_state.swap_logs = load_swap_logs("APPROVED")
                st.success(f"{reset_start} ~ {reset_end} 기간이 초기화되었습니다.")
                st.rerun()
                
        st.markdown("---")
        if st.button("🚨 데이터 완전 전체 초기화"):
            clear_all_db()
            st.session_state.sub_logs = []
            st.session_state.swap_logs = []
            st.success("모든 내역이 초기화되었습니다.")
            st.rerun()

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

def get_latest_updated_timetable(base_df, target_week_dates_dict):
    if base_df is None or base_df.empty: return base_df
    df = base_df.copy()
    df["is_swapped"] = False
    date_to_day = {v.strftime("%Y-%m-%d"): k for k, v in target_week_dates_dict.items()}

    for swap in st.session_state.swap_logs:
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

parsed_df = get_latest_updated_timetable(p_df, current_week_dates)

def build_weekly_html_table(all_parsed_df, title_name, filter_type="CLASS"):
    days = ["월", "화", "수", "목", "금"]; periods = list(range(1, 8))
    html = f"<div class='print-title'><h3 style='text-align: center; margin-bottom: 12px;'>🏫 {title_name} 주간 시간표 ({mon_str} ~ {fri_str})</h3></div><div class='table-container'><table class='unified-table'><thead><tr><th style='width:8%;'>교시</th>"
    for d in days: html += f"<th>{d}<br><span style='font-size:10px; font-weight:normal; color:#94a3b8;'>({current_week_dates[d].strftime('%m/%d')})</span></th>"
    html += "</tr></thead><tbody>"
    sub_dict = { (log["날짜"], log["학급"], int(log["교시"])): log for log in st.session_state.sub_logs }
    for p in periods:
        html += f"<tr><td class='period-col'>{p}교시</td>"
        for d in days:
            date_str = current_week_dates[d].strftime("%Y-%m-%d"); cell_data = pd.DataFrame(); is_sub_entry, sub_info = False, None
            if filter_type == "CLASS": cell_data = all_parsed_df[(all_parsed_df["학급"] == title_name) & (all_parsed_df["요일"] == d) & (all_parsed_df["교시"] == p)]
            else:
                cell_data = all_parsed_df[(all_parsed_df["교사"] == title_name) & (all_parsed_df["요일"] == d) & (all_parsed_df["교시"] == p)]
                for sub_key, sub_val in sub_dict.items():
                    if sub_key[0] == date_str and int(sub_key[2]) == p and sub_val["대강교사"] == title_name:
                        cls_cell = all_parsed_df[(all_parsed_df["학급"] == sub_key[1]) & (all_parsed_df["요일"] == d) & (all_parsed_df["교시"] == p)]
                        if not cls_cell.empty: cell_data, is_sub_entry, sub_info = cls_cell, True, sub_val; break

            if not cell_data.empty:
                row = cell_data.iloc[0]
                subj, teacher, cls, is_swapped = row["과목"], row["교사"], row["학급"], row.get("is_swapped", False)
                sub_key = (date_str, cls, p); cell_class, badge_html = "", ""
                if is_sub_entry or sub_key in sub_dict:
                    if not sub_info: sub_info = sub_dict[sub_key]
                    if sub_info["대강교사"] == "빈칸": subj, teacher = "-", ""
                    else:
                        cell_class = "bg-substitute"
                        if filter_type == "TEACHER" and sub_info["대강교사"] == title_name: badge_html, teacher = f"<span class='status-badge badge-sub'>📝대강수업 [{cls}]</span><br>", f"<b>{title_name} (대강)</b>"
                        else: badge_html, teacher = f"<span class='status-badge badge-sub'>📝대강 ({sub_info['대강교사']})</span><br>", f"<s>{teacher}</s> ➔ <b>{sub_info['대강교사']}</b>"
                elif is_swapped: cell_class, badge_html = "bg-swapped", "<span class='status-badge badge-swap'>🔄교체됨</span><br>"
                display_teacher = f"({teacher})" if filter_type == "CLASS" and teacher else f"[{cls}]"
                html += "<td>-</td>" if subj in ["", "-"] else f"<td class='{cell_class}'>{badge_html}<div class='subject-name'>{subj}</div><div class='teacher-name'>{display_teacher}</div></td>"
            else: html += "<td>-</td>"
        html += "</tr>"
    return html + "</tbody></table></div>"

def build_merged_full_grid_html(df_in):
    days = ["월", "화", "수", "목", "금"]; classes = sorted(df_in["학급"].unique())
    sub_dict = { (log["날짜"], log["학급"], int(log["교시"])): log for log in st.session_state.sub_logs }
    html = "<div class='table-container'><table class='unified-table'><thead><tr><th style='width: 4%;'>요일</th><th style='width: 5%;'>교시</th>"
    for c in classes: html += f"<th>{c}</th>"
    html += "</tr></thead><tbody>"
    for d in days:
        date_str = current_week_dates[d].strftime("%Y-%m-%d")
        for p in range(1, 8):
            html += f"<tr>"
            if p == 1: html += f"<td rowspan='7' class='day-col'><b>{d}</b><span>({current_week_dates[d].strftime('%m/%d')})</span></td>"
            html += f"<td class='period-col'>{p}교시</td>"
            for c in classes:
                cell_data = df_in[(df_in["학급"] == c) & (df_in["요일"] == d) & (df_in["교시"] == p)]
                if not cell_data.empty:
                    row = cell_data.iloc[0]
                    subj, teacher, is_swapped = row["과목"], row["교사"], row.get("is_swapped", False)
                    sub_key = (date_str, c, p)
                    if sub_key in sub_dict:
                        if sub_dict[sub_key]['대강교사'] == "빈칸": bg_class, txt = "", "-"
                        else: bg_class, txt = "bg-substitute", f"<span class='badge-sub status-badge'>대강</span><br><div class='subject-name'>{subj}</div><div class='teacher-name'>({sub_dict[sub_key]['대강교사']})</div>"
                    elif is_swapped: bg_class, txt = "bg-swapped", f"<span class='badge-swap status-badge'>변동</span><br><div class='subject-name'>{subj}</div><div class='teacher-name'>({teacher})</div>"
                    else: bg_class, txt = "", f"<div class='subject-name'>{subj}</div><div class='teacher-name'>({teacher})</div>" if subj else "-"
                    html += f"<td class='{bg_class}'>{txt}</td>"
                else: html += "<td>-</td>"
            html += "</tr>"
    return html + "</tbody></table></div>"

# 7. 상단 UI
st.markdown(f"<h1 class='print-hide'>📅 {st.session_state.school_name} 시간표 관리 시스템</h1>", unsafe_allow_html=True)
c_nav1, c_nav2, c_nav3 = st.columns([2, 5, 2])
with c_nav2:
    col_b1, col_b2, col_b3, col_b4 = st.columns([1, 2.8, 0.9, 1])
    with col_b1: 
        if st.button("◀ 이전주", use_container_width=True): st.session_state.week_offset -= 1; st.rerun()
    with col_b2: st.markdown(f"<h4 class='print-hide' style='text-align: center; color: #0284c7; margin: 0;'>📆 [{mon_str} ~ {fri_str}]</h4>", unsafe_allow_html=True)
    with col_b3: 
        if st.button("이번주", use_container_width=True): st.session_state.week_offset = 0; st.rerun()
    with col_b4: 
        if st.button("다음주 ▶", use_container_width=True): st.session_state.week_offset += 1; st.rerun()

# 8. 메인 화면 렌더링
if parsed_df is not None and not parsed_df.empty:
    is_admin = (mode == "관리자 모드 (수업교체/대강)") and st.session_state.admin_authenticated
    if is_admin: tab1, tab2, tab3 = st.tabs(["🗓️ 시간표 스마트 통합 관리", "🔄 교체 요청 대기(승인)", "📊 대강일지 및 통계"])
    else: tab1, tab2 = st.tabs(["🗓️ 시간표 조회", "🔄 날짜 지정 기반 수업 맞교환 신청"])

    with tab1:
        c_v1, c_v2 = st.columns([3, 1])
        with c_v1:
            view_opts = ["전체 시간표", "학급별 주간 시간표", "교사별 주간 시간표"]
            view_idx = view_opts.index(st.session_state.view_mode_val) if st.session_state.view_mode_val in view_opts else 0
            view_mode = st.radio("조회 방식", view_opts, index=view_idx, horizontal=True)
            st.session_state.view_mode_val = view_mode
        with c_v2: 
            st.write("")
            components.html(
                """
                <style>
                    button { width: 100%; padding: 8px 14px; background-color: #0284c7; color: white; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; font-family: sans-serif; font-size: 13.5px; }
                    button:hover { background-color: #0369a1; }
                </style>
                <button onclick="window.parent.print()">🖨️ 시간표 인쇄 / PDF 저장</button>
                """, height=45
            )

        if view_mode == "전체 시간표":
            if is_admin:
                st.info("💡 **스마트 사용법**: **우클릭**(자동 필터링 교체/대강 팝업창), **Ctrl+C/V**(다주차 간 복사/붙여넣기), **Delete**(즉시 빈칸 삭제)", icon="🖱️")
                days = ["월", "화", "수", "목", "금"]; classes = sorted(parsed_df["학급"].unique())
                sub_dict = {(log["날짜"], log["학급"], int(log["교시"])): log for log in st.session_state.sub_logs}
                grid_data = {}
                for d in days:
                    date_str = current_week_dates[d].strftime("%Y-%m-%d")
                    for p in range(1, 8):
                        for c in classes:
                            cell = parsed_df[(parsed_df["학급"] == c) & (parsed_df["요일"] == d) & (parsed_df["교시"] == p)]
                            key = f"{date_str}_{c}_{p}"
                            if not cell.empty:
                                row = cell.iloc[0]; sub_key = (date_str, c, p); is_sub = sub_key in sub_dict
                                sub_teacher_val = sub_dict[sub_key]['대강교사'] if is_sub else ""
                                subj_val, teacher_val = row["과목"], row["교사"]
                                if is_sub and sub_teacher_val == "빈칸": subj_val, teacher_val = "", ""
                                grid_data[key] = {"date": date_str, "day": d, "cls": c, "period": p, "subj": subj_val, "teacher": teacher_val, "sub_teacher": sub_teacher_val, "is_swapped": bool(row.get("is_swapped", False)), "is_sub": is_sub}
                            else: grid_data[key] = {"date": date_str, "day": d, "cls": c, "period": p, "subj": "", "teacher": "", "sub_teacher": "", "is_swapped": False, "is_sub": False}

                action_result = AdminGrid(grid_data=grid_data, classes=classes, teacher_list=teacher_list, copied_data=st.session_state.copied_data, key="admin_grid_fast")

                if action_result:
                    act_id = action_result.get("action_id")
                    if act_id and act_id != st.session_state.last_action_id:
                        st.session_state.last_action_id = act_id
                        act = action_result.get("act")
                        t_item = action_result.get("target")
                        c_item = action_result.get("copiedData")
                        
                        if act == "COPY" and t_item:
                            st.session_state.copied_data = t_item
                            
                        elif act == "DELETE" and t_item:
                            t_date, t_cls, t_period = t_item["date"], t_item["cls"], int(t_item["period"])
                            day_kr = ["월","화","수","목","금"][pd.to_datetime(t_date).weekday()]
                            save_sub_log({"날짜": t_date, "요일": day_kr, "교시": t_period, "학급": t_cls, "원교사": t_item["teacher"], "대강교사": "빈칸", "대강사유": "관리자 삭제", "단가": 0, "주차": st.session_state.week_offset})
                            save_cell_override(t_date, day_kr, t_period, t_cls, "", "")
                            st.session_state.sub_logs = load_sub_logs()
                            st.rerun()

                        elif act == "SUB_DIRECT" and t_item:
                            sub_t, sub_r = action_result.get("sub_t"), action_result.get("sub_r")
                            if sub_t and sub_r:
                                save_sub_log({"날짜": t_item["date"], "요일": t_item["day"], "교시": int(t_item["period"]), "학급": t_cls, "원교사": t_item["teacher"], "대강교사": sub_t, "대강사유": sub_r, "단가": st.session_state.hourly_rate, "주차": st.session_state.week_offset})
                                st.session_state.sub_logs = load_sub_logs()
                                st.rerun()

                        # 📍 팝업 내부 교체 실행 액션 처리
                        elif act == "EXECUTE_CROSS_SWAP" and t_item:
                            s_date2 = action_result.get("s_date2")
                            period2 = int(action_result.get("period2"))
                            subj2 = action_result.get("subj2")
                            teacher2 = action_result.get("teacher2")
                            
                            save_swap_request({
                                "cls1": t_item["cls"], "date1": t_item["date"], "period1": int(t_item["period"]), "subj1": t_item["subj"], "teacher1": t_item["teacher"],
                                "cls2": t_item["cls"], "date2": s_date2, "period2": period2, "subj2": subj2, "teacher2": teacher2
                            }, auto_approve=True)
                            st.session_state.swap_logs = load_swap_logs("APPROVED")
                            st.toast("🔀 팝업 일체형 수업 맞교환 완료!")
                            st.rerun()

                        elif act in ["PASTE_OVERWRITE", "PASTE_SWAP"] and c_item and t_item:
                            t_date, t_cls, t_period = t_item["date"], t_item["cls"], int(t_item["period"])
                            day_kr = ["월","화","수","목","금"][pd.to_datetime(t_date).weekday()]
                            c_teacher, c_subj = c_item["teacher"], c_item["subj"]
                            conflict = parsed_df[(parsed_df["교사"] == c_teacher) & (parsed_df["요일"] == day_kr) & (parsed_df["교시"] == t_period) & (parsed_df["학급"] != t_cls)]
                            
                            if not conflict.empty: st.toast(f"⚠️ 중복! {c_teacher} 선생님은 해당 시간에 이미 수업이 있습니다.")
                            else:
                                if act == "PASTE_OVERWRITE":
                                    save_cell_override(t_date, day_kr, t_period, t_cls, c_subj, c_teacher)
                                elif act == "PASTE_SWAP":
                                    save_swap_request({"cls1": c_item["cls"], "date1": c_item["date"], "period1": c_item["period"], "subj1": c_item["subj"], "teacher1": c_teacher, "cls2": t_cls, "date2": t_date, "period2": t_period, "subj2": t_item["subj"], "teacher2": t_item["teacher"]}, auto_approve=True)
                                    st.session_state.swap_logs = load_swap_logs("APPROVED")
                                st.rerun()
            else:
                st.markdown(build_merged_full_grid_html(parsed_df), unsafe_allow_html=True)

        elif view_mode == "학급별 주간 시간표": 
            cls_opts = sorted(parsed_df["학급"].unique())
            idx = cls_opts.index(st.session_state.sel_cls_val) if st.session_state.sel_cls_val in cls_opts else 0
            target_cls = st.selectbox("🎯 학급 선택", cls_opts, index=idx)
            st.session_state.sel_cls_val = target_cls
            st.markdown(build_weekly_html_table(parsed_df, target_cls, "CLASS"), unsafe_allow_html=True)
        else: 
            t_opts = teacher_list
            idx = t_opts.index(st.session_state.sel_t_val) if st.session_state.sel_t_val in t_opts else 0
            target_t = st.selectbox("👨‍🏫 교사 선택", t_opts, index=idx)
            st.session_state.sel_t_val = target_t
            st.markdown(build_weekly_html_table(parsed_df, target_t, "TEACHER"), unsafe_allow_html=True)

    with tab2:
        if is_admin:
            st.subheader("📥 [관리자] 대기 중인 수업 교체 승인 대기열")
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
                            st.session_state.swap_logs = load_swap_logs("APPROVED")
                            st.success("승인되었습니다!")
                            st.rerun()
            else: st.success("현재 대기 중인 교체 요청이 없습니다.")
        else:
            st.subheader("🔄 날짜 지정 기반 수업 맞교환 신청 (승인 요청제)")
            selected_cls = st.selectbox("🎯 대상 학급 선택", sorted(parsed_df["학급"].unique()))
            sub_dict_swap = { (log["날짜"], log["학급"], int(log["교시"])): log["대강교사"] for log in st.session_state.sub_logs }
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("##### 📍 [수업 A] 첫 번째 수업 지정")
                date_a = st.date_input("수업 A 날짜 선택", date(2026, 8, 10), key="d_a")
                day_a_kr = ["월", "화", "수", "목", "금", "토", "일"][date_a.weekday()]
                t_week_dates_a = get_week_dates(st.session_state.week_offset)
                t_df_a = get_latest_updated_timetable(p_df, t_week_dates_a)
                cls_df_a = t_df_a[(t_df_a["학급"] == selected_cls) & (t_df_a["요일"] == day_a_kr)].copy()
                
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
                t_week_dates_b = get_week_dates(st.session_state.week_offset)
                t_df_b = get_latest_updated_timetable(p_df, t_week_dates_b)
                cls_df_b = t_df_b[(t_df_b["학급"] == selected_cls) & (t_df_b["요일"] == day_b_kr)].copy()
                
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
                        if date_a == date_b and b_idx == idx_a: continue
                        r2_candidate = cls_df_b.loc[b_idx]
                        if r2_candidate["과목"] == "" or r2_candidate["과목"] == "-": continue
                        t2_clean = str(r2_candidate["교사"]).replace("(대강)", "").strip()
                        c1_conflict = t_df_b[(t_df_b["교사"] == t1_clean) & (t_df_b["요일"] == day_b_kr) & (t_df_b["교시"] == r2_candidate["교시"]) & (t_df_b["학급"] != selected_cls)]
                        c2_conflict = t_df_a[(t_df_a["교사"] == t2_clean) & (t_df_a["요일"] == day_a_kr) & (t_df_a["교시"] == r1["교시"]) & (t_df_a["학급"] != selected_cls)]
                        if c1_conflict.empty and c2_conflict.empty: valid_b_indices.append(b_idx)

                if valid_b_indices:
                    idx_b = st.selectbox("수업 B 선택 (시수 충돌 없는 수업 목록)", valid_b_indices, format_func=lambda x: f"{cls_df_b.loc[x, '교시']}교시 - {cls_df_b.loc[x, '과목']}({cls_df_b.loc[x, '교사']})")
                    r2 = cls_df_b.loc[idx_b]
                else:
                    st.warning("⚠️ 선택하신 조건에서 충돌 없는 수업 B 후보가 없습니다.")
                    r2 = None

            if r1 is not None and r2 is not None:
                st.write("")
                if st.button("📩 수업 맞교환 승인 요청하기", use_container_width=True, type="primary"):
                    log_entry = {
                        "cls1": selected_cls, "date1": str(date_a), "period1": int(r1["교시"]), "subj1": r1["과목"], "teacher1": str(r1["교사"]),
                        "cls2": selected_cls, "date2": str(date_b), "period2": int(r2["교시"]), "subj2": r2["과목"], "teacher2": str(r2["교사"])
                    }
                    save_swap_request(log_entry, auto_approve=False)
                    st.success("📩 관리자에게 수업 교체 요청이 전달되었습니다!")

    if is_admin:
        with tab3:
            st.subheader("📊 교사별 주당 시수 & 기간별 대강일지 출력")
            c_s1, c_s2 = st.columns([1, 1.8])
            with c_s1:
                tc = parsed_df["교사"].value_counts().reset_index()
                tc.columns = ["교사명", "주당 시수"]; st.dataframe(tc, use_container_width=True)
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
                        st.download_button("📥 대강일지 엑셀 다운로드", export_df.to_csv(index=False).encode('utf-8-sig'), f"대강일지_{start_filter}.csv", "text/csv")
                    else: st.info("선택 기간의 대강 내역이 없습니다.")
                else: st.info("대강 기록이 존재하지 않습니다.")