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
        
        # 대강 내역이 반영된 현재 주/날짜 상태의 가공 데이터 준비
        sub_dict = { (log["날짜"], log["학급"], int(log["교시"])): log["대강교사"] for log in st.session_state.sub_logs }
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("##### 📍 [수업 A] 첫 번째 수업 지정")
            date_a = st.date_input("수업 A 날짜 선택", date(2026, 8, 10), key="d_a")
            day_a_kr = ["월", "화", "수", "목", "금", "토", "일"][date_a.weekday()]
            cls_df_a = parsed_df[(parsed_df["학급"] == selected_cls) & (parsed_df["요일"] == day_a_kr)].copy()
            
            # 대강 교사 이름 반영
            if not cls_df_a.empty:
                for idx in cls_df_a.index:
                    d_str = str(date_a)
                    p_num = int(cls_df_a.loc[idx, "교시"])
                    if (d_str, selected_cls, p_num) in sub_dict:
                        cls_df_a.loc[idx, "교사"] = f"{sub_dict[(d_str, selected_cls, p_num)]}(대강)"
                
                idx_a = st.selectbox("수업 A 선택", cls_df_a.index, format_func=lambda x: f"{cls_df_a.loc[x, '교시']}교시 - {cls_df_a.loc[x, '과목']}({cls_df_a.loc[x, '교사']})")
                r1 = cls_df_a.loc[idx_a]
            else:
                st.warning("선택한 날짜에 해당하는 수업이 없습니다.")
                r1 = None

        with col_b:
            st.markdown("##### 📍 [수업 B] 맞교환 가능한 수업 (대강 교사 스케줄 검증 완료)")
            date_b = st.date_input("수업 B 날짜 선택", date(2026, 8, 10), key="d_b")
            day_b_kr = ["월", "화", "수", "목", "금", "토", "일"][date_b.weekday()]
            cls_df_b = parsed_df[(parsed_df["학급"] == selected_cls) & (parsed_df["요일"] == day_b_kr)].copy()
            
            if not cls_df_b.empty:
                for idx in cls_df_b.index:
                    d_str = str(date_b)
                    p_num = int(cls_df_b.loc[idx, "교시"])
                    if (d_str, selected_cls, p_num) in sub_dict:
                        cls_df_b.loc[idx, "교사"] = f"{sub_dict[(d_str, selected_cls, p_num)]}(대강)"

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
                save_swap_request(log_entry)
                st.success("📩 수업 교체 요청이 등록되었습니다! (관리자가 승인하면 최종 반영됩니다)")