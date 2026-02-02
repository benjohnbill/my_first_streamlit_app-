 import streamlit as st
 from openai import OpenAI
 
-st.title("🤖 나의 AI 챗봇")
-
-# 사이드바에서 API Key 입력
-api_key = st.sidebar.text_input("OpenAI API Key", type="password")
+st.title("🎬 나와 어울리는 영화는?")
+
+# 사이드바에서 API Key 입력
+api_key = st.sidebar.text_input("OpenAI API Key", type="password")
+
+st.subheader("심리테스트")
+st.write("아래 질문 5개에 답하고, 당신에게 어울리는 영화 장르를 찾아보세요.")
+
+questions = [
+    {
+        "question": "주말에 시간이 생기면 가장 먼저 하고 싶은 일은?",
+        "options": [
+            "연인이나 친구와 감성적인 카페 데이트",
+            "즉흥 여행으로 새로운 장소 탐험",
+            "집에서 새로운 세계관의 작품 몰아보기",
+            "웃긴 영상 보며 스트레스 풀기",
+        ],
+    },
+    {
+        "question": "스토리에서 가장 끌리는 요소는?",
+        "options": [
+            "인물 간의 감정선과 관계 변화",
+            "손에 땀을 쥐게 하는 위기와 도전",
+            "상상력을 자극하는 설정과 세계관",
+            "센스 있는 대사와 유쾌한 전개",
+        ],
+    },
+    {
+        "question": "여행을 떠난다면 어떤 분위기를 선호하나요?",
+        "options": [
+            "아름다운 풍경 속에서의 힐링",
+            "익스트림 스포츠나 액티비티",
+            "미지의 장소나 신비로운 공간",
+            "즐거운 사람들과의 유쾌한 시간",
+        ],
+    },
+    {
+        "question": "당신이 좋아하는 주인공 유형은?",
+        "options": [
+            "섬세하고 감정 표현이 풍부한 인물",
+            "위기에 강하고 결단력 있는 인물",
+            "호기심 많고 새로운 것에 도전하는 인물",
+            "재치 있고 분위기를 밝히는 인물",
+        ],
+    },
+    {
+        "question": "영화를 보고 난 뒤 남는 감상은?",
+        "options": [
+            "여운이 길게 남는 감동",
+            "짜릿한 긴장감과 카타르시스",
+            "새로운 세계에 대한 상상",
+            "웃음과 가벼운 행복감",
+        ],
+    },
+]
+
+for idx, item in enumerate(questions, start=1):
+    st.radio(
+        f"Q{idx}. {item['question']}",
+        item["options"],
+        key=f"question_{idx}",
+    )
 
 # 대화 기록 초기화
 if "messages" not in st.session_state:
     st.session_state.messages = []
 
 # 이전 대화 표시
 for message in st.session_state.messages:
     with st.chat_message(message["role"]):
         st.markdown(message["content"])
 
 # 사용자 입력 처리
 if prompt := st.chat_input("메시지를 입력하세요"):
     if not api_key:
         st.error("⚠️ 사이드바에서 API Key를 입력해주세요!")
     else:
         # 사용자 메시지 저장 및 표시
         st.session_state.messages.append({"role": "user", "content": prompt})
         with st.chat_message("user"):
             st.markdown(prompt)
         
         # AI 응답 생성
-        with st.chat_message("assistant"):
-            client = OpenAI(api_key=api_key)
-            response = client.chat.completions.create(
-                model="gpt-4o-mini",
-                messages=st.session_state.messages
-            )
+        with st.chat_message("assistant"):
+            client = OpenAI(api_key=api_key)
+            response = client.chat.completions.create(
+                model="gpt-4o-mini",
+                messages=st.session_state.messages,
+            )
             reply = response.choices[0].message.content
             st.markdown(reply)
-            st.session_state.messages.append({"role": "assistant", "content": reply})
\ No newline at end of file
+            st.session_state.messages.append({"role": "assistant", "content": reply})
