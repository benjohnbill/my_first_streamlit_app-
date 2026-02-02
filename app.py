import math
from datetime import date
from typing import Dict, List, Tuple, Optional

import requests
import streamlit as st

# =========================
# Page
# =========================
st.set_page_config(page_title="🎬 나와 어울리는 영화는?", page_icon="🎬", layout="wide")
st.title("🎬 나와 어울리는 영화는?")
st.write("간단한 질문 5개로 당신의 영화 취향을 분석하고, TMDB에서 인기 영화를 추천해드려요! 🍿")

# =========================
# Sidebar: TMDB Settings
# =========================
with st.sidebar:
    st.header("TMDB 설정")
    tmdb_key = st.text_input("TMDB API Key", type="password", help="TMDB에서 발급받은 API Key를 입력하세요.")
    st.caption("키는 저장되지 않으며, 이 앱 실행 중에만 사용돼요.")

    st.divider()
    st.subheader("추천 옵션(고도화)")
    language = st.selectbox("표시 언어", ["ko-KR", "en-US"], index=0)
    region = st.selectbox("지역(Region)", ["KR", "US", "JP", "GB"], index=0)
    sort_by = st.selectbox(
        "정렬 기준",
        ["popularity.desc", "vote_average.desc", "primary_release_date.desc"],
        index=0,
        help="discover 정렬 옵션"
    )
    min_vote_count = st.slider(
        "최소 평가 수(vote_count.gte)",
        min_value=0,
        max_value=5000,
        value=200,
        step=50,
        help="평점 신뢰도를 위해 평가 수가 적은 영화는 제외할 수 있어요."
    )
    include_year_filter = st.checkbox("개봉 연도 범위 필터 사용", value=False)
    year_from, year_to = None, None
    if include_year_filter:
        current_year = date.today().year
        year_from, year_to = st.slider("개봉 연도 범위", 1970, current_year, (2000, current_year))
    poster_size_pref = st.selectbox("포스터 크기 선호", ["w342", "w500", "w780", "original"], index=1)

# =========================
# TMDB Constants
# =========================
TMDB_API_BASE = "https://api.themoviedb.org/3"

# 장르 ID (요구사항 + 표 반영)
GENRE_IDS = {
    "액션": 28,
    "모험": 12,
    "코미디": 35,
    "로맨스": 10749,
    "SF": 878,
    "판타지": 14,
    "드라마": 18,
    "애니메이션": 16,
}

# 결과(4종) -> TMDB 장르 조합
RESULT_TO_TMDB_GENRES = {
    "로맨스/드라마": [GENRE_IDS["로맨스"], GENRE_IDS["드라마"]],
    "액션/어드벤처": [GENRE_IDS["액션"], GENRE_IDS["모험"]],
    "SF/판타지": [GENRE_IDS["SF"], GENRE_IDS["판타지"]],
    "코미디": [GENRE_IDS["코미디"]],
}

# =========================
# Questions (사용자 제공 문구)
# =========================
questions: List[Tuple[str, List[str]]] = [
    ("1. 주말에 가장 하고 싶은 것은?",
     ["집에서 휴식", "친구와 놀기", "새로운 곳 탐험", "혼자 취미생활"]),
    ("2. 스트레스 받으면?",
     ["혼자 있기", "수다 떨기", "운동하기", "맛있는 거 먹기"]),
    ("3. 영화에서 중요한 것은?",
     ["감동 스토리", "시각적 영상미", "깊은 메시지", "웃는 재미"]),
    ("4. 여행 스타일?",
     ["계획적", "즉흥적", "액티비티", "힐링"]),
    ("5. 친구 사이에서 나는?",
     ["듣는 역할", "주도하기", "분위기 메이커", "필요할 때 나타남"]),
]

# =========================
# Answer -> Score Mapping (간단 규칙)
# =========================
ANSWER_TO_SCORE: Dict[str, Dict[str, int]] = {
    # Q1
    "집에서 휴식": {"로맨스/드라마": 2, "코미디": 1},
    "친구와 놀기": {"코미디": 2, "액션/어드벤처": 1},
    "새로운 곳 탐험": {"액션/어드벤처": 2, "SF/판타지": 1},
    "혼자 취미생활": {"SF/판타지": 2, "로맨스/드라마": 1},

    # Q2
    "혼자 있기": {"로맨스/드라마": 2, "SF/판타지": 1},
    "수다 떨기": {"코미디": 2, "로맨스/드라마": 1},
    "운동하기": {"액션/어드벤처": 2, "SF/판타지": 1},
    "맛있는 거 먹기": {"코미디": 2, "로맨스/드라마": 1},

    # Q3
    "감동 스토리": {"로맨스/드라마": 3},
    "시각적 영상미": {"SF/판타지": 2, "액션/어드벤처": 1},
    "깊은 메시지": {"SF/판타지": 2, "로맨스/드라마": 1},
    "웃는 재미": {"코미디": 3},

    # Q4
    "계획적": {"로맨스/드라마": 2, "SF/판타지": 1},
    "즉흥적": {"액션/어드벤처": 2, "코미디": 1},
    "액티비티": {"액션/어드벤처": 3},
    "힐링": {"로맨스/드라마": 2, "코미디": 1},

    # Q5
    "듣는 역할": {"로맨스/드라마": 2},
    "주도하기": {"액션/어드벤처": 2, "SF/판타지": 1},
    "분위기 메이커": {"코미디": 3},
    "필요할 때 나타남": {"SF/판타지": 2, "액션/어드벤처": 1},
}

RESULT_HINT = {
    "로맨스/드라마": "감정선과 관계의 변화, 여운이 남는 이야기",
    "액션/어드벤처": "속도감과 긴장감, 모험과 미션의 쾌감",
    "SF/판타지": "탄탄한 세계관과 상상력, 몰입감 있는 설정",
    "코미디": "가볍게 즐기는 웃음 포인트, 기분전환",
}

# =========================
# TMDB Helpers
# =========================
def tmdb_get(path: str, api_key: str, params: Optional[dict] = None) -> dict:
    """TMDB GET 요청 (공통)"""
    if params is None:
        params = {}
    params = {**params, "api_key": api_key}
    url = f"{TMDB_API_BASE}{path}"
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=60 * 60 * 24)  # 하루 캐시(문서에서도 configuration 캐시 권장)
def get_tmbd_configuration(api_key: str) -> dict:
    return tmdb_get("/configuration", api_key)

def build_poster_url(config: dict, poster_path: Optional[str], preferred_size: str) -> Optional[str]:
    if not poster_path:
        return None
    images = config.get("images", {})
    base = images.get("secure_base_url") or images.get("base_url")
    sizes = images.get("poster_sizes", []) or []
    if not base:
        # 안전장치(구버전 방식) - 그래도 최대한 configuration 우선
        base = "https://image.tmdb.org/t/p/"
        sizes = ["w500", "original"]

    size = preferred_size if preferred_size in sizes else (sizes[-1] if sizes else "w500")
    return f"{base}{size}{poster_path}"

def analyze_answers(answers: List[str]) -> Tuple[str, Dict[str, int], List[str]]:
    scores = {k: 0 for k in RESULT_TO_TMDB_GENRES.keys()}
    for a in answers:
        mapping = ANSWER_TO_SCORE.get(a, {})
        for bucket, pts in mapping.items():
            scores[bucket] += pts

    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_score = sorted_items[0][1]
    tied = [g for g, s in sorted_items if s == top_score]

    # 동점이면 3번(영화에서 중요한 것)을 우선 참고
    if len(tied) > 1:
        q3 = answers[2]
        q3_map = ANSWER_TO_SCORE.get(q3, {})
        q3_candidates = [g for g in tied if g in q3_map]
        if len(q3_candidates) == 1:
            final = q3_candidates[0]
        else:
            priority = ["로맨스/드라마", "액션/어드벤처", "SF/판타지", "코미디"]
            final = sorted(tied, key=lambda g: priority.index(g))[0]
    else:
        final = sorted_items[0][0]

    evidence = [a for a in answers if final in ANSWER_TO_SCORE.get(a, {})]
    return final, scores, evidence

def normalize(x: float, xmin: float, xmax: float) -> float:
    if xmax <= xmin:
        return 0.0
    return (x - xmin) / (xmax - xmin)

def pick_diverse_top5(movies: List[dict]) -> List[dict]:
    """
    discover 결과에서 5개를 '다양하게' 선정:
    - popularity + vote_average + vote_count를 조합 점수로 계산
    - 너무 유사한(동일 연도/제목/포스터 없는) 것 편중 최소화
    """
    if not movies:
        return []

    pops = [m.get("popularity", 0) or 0 for m in movies]
    rates = [m.get("vote_average", 0) or 0 for m in movies]
    votes = [m.get("vote_count", 0) or 0 for m in movies]

    pop_min, pop_max = min(pops), max(pops)
    rate_min, rate_max = min(rates), max(rates)
    vote_min, vote_max = min(votes), max(votes)

    scored = []
    for m in movies:
        pop = m.get("popularity", 0) or 0
        rate = m.get("vote_average", 0) or 0
        vote = m.get("vote_count", 0) or 0

        s = (
            0.45 * normalize(pop, pop_min, pop_max)
            + 0.45 * normalize(rate, rate_min, rate_max)
            + 0.10 * normalize(math.log1p(vote), math.log1p(vote_min), math.log1p(vote_max))
        )
        scored.append((s, m))

    scored.sort(key=lambda x: x[0], reverse=True)

    picked = []
    used_years = set()
    used_titles = set()

    for _, m in scored:
        title = m.get("title") or m.get("name") or ""
        if not title or title in used_titles:
            continue

        release_date = m.get("release_date") or ""
        year = release_date[:4] if len(release_date) >= 4 else None

        # 다양성: 같은 연도 과다 방지(가능하면)
        if year and year in used_years and len(used_years) < 3:
            continue

        picked.append(m)
        used_titles.add(title)
        if year:
            used_years.add(year)

        if len(picked) >= 5:
            break

    # 만약 다양성 때문에 5개 미만이면 그냥 상위로 채움
    if len(picked) < 5:
        for _, m in scored:
            if m in picked:
                continue
            picked.append(m)
            if len(picked) >= 5:
                break

    return picked[:5]

@st.cache_data(ttl=600)
def discover_movies(
    api_key: str,
    genre_ids: List[int],
    language: str,
    region: str,
    sort_by: str,
    min_vote_count: int,
    year_from: Optional[int],
    year_to: Optional[int],
    pages: int = 2,
) -> List[dict]:
    """
    TMDB discover로 후보를 넓게 가져오기:
    - 장르 2개 조합은 OR(|)로 넓게 가져온 뒤, 앱에서 다양하게 5편 선정
    """
    # NOTE: TMDB discover에서 콤마는 AND, 파이프(|)는 OR로 자주 쓰임(여러 필터에서 동일 패턴).
    with_genres = "|".join(str(g) for g in genre_ids) if len(genre_ids) > 1 else str(genre_ids[0])

    results: List[dict] = []
    for page in range(1, pages + 1):
        params = {
            "with_genres": with_genres,
            "language": language,
            "region": region,
            "sort_by": sort_by,
            "include_adult": "false",
            "include_video": "false",
            "vote_count.gte": min_vote_count,
            "page": page,
        }
        if year_from is not None and year_to is not None:
            params["primary_release_date.gte"] = f"{year_from}-01-01"
            params["primary_release_date.lte"] = f"{year_to}-12-31"

        data = tmdb_get("/discover/movie", api_key, params=params)
        results.extend(data.get("results", []))

    return results

def render_movie_card(m: dict, poster_url: Optional[str], reason: str):
    title = m.get("title") or m.get("name") or "제목 정보 없음"
    rating = m.get("vote_average", 0) or 0
    vote_count = m.get("vote_count", 0) or 0
    overview = m.get("overview") or "줄거리 정보가 없어요."
    release_date = m.get("release_date") or ""

    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        if poster_url:
            st.image(poster_url, use_container_width=True)
        else:
            st.caption("포스터 없음")

    with col2:
        st.markdown(f"#### {title}")
        meta = []
        if release_date:
            meta.append(f"🗓️ {release_date}")
        meta.append(f"⭐ {rating:.1f} (투표 {vote_count:,}회)")
        st.write(" · ".join(meta))

        st.write(overview)

        st.markdown("**이 영화를 추천하는 이유**")
        st.write(f"- {reason}")

# =========================
# Main: Questionnaire
# =========================
st.subheader("질문에 답해 주세요 👇")
answers: List[Optional[str]] = []

for idx, (q, opts) in enumerate(questions, start=1):
    ans = st.radio(q, opts, index=None, key=f"q{idx}")
    answers.append(ans)
    st.divider()

# =========================
# Result Button
# =========================
if st.button("결과 보기"):
    if not tmdb_key:
        st.warning("사이드바에 TMDB API Key를 입력해 주세요!")
        st.stop()

    if any(a is None for a in answers):
        st.warning("모든 질문에 답한 뒤 결과를 확인해 주세요!")
        st.stop()

    with st.spinner("분석 중..."):
        # 1) 분석
        result_bucket, score_map, evidence_answers = analyze_answers([a for a in answers if a is not None])
        genre_ids = RESULT_TO_TMDB_GENRES[result_bucket]

        # 2) configuration(이미지) 로딩
        try:
            config = get_tmbd_configuration(tmdb_key)
        except requests.HTTPError:
            st.error("TMDB 요청에 실패했어요. API Key가 올바른지 확인해 주세요.")
            st.stop()

        # 3) discover로 후보 넓게 가져오기
        try:
            candidates = discover_movies(
                api_key=tmdb_key,
                genre_ids=genre_ids,
                language=language,
                region=region,
                sort_by=sort_by,
                min_vote_count=min_vote_count,
                year_from=year_from,
                year_to=year_to,
                pages=2,
            )
        except Exception as e:
            st.error("영화 데이터를 가져오는 중 오류가 발생했어요.")
            st.exception(e)
            st.stop()

        if not candidates:
            st.warning("조건에 맞는 영화를 찾지 못했어요. (필터를 완화해 보세요: 최소 평가 수↓, 연도 필터 해제)")
            st.stop()

        # 4) 후보에서 다양하게 5개 선정
        picked = pick_diverse_top5(candidates)

    # 결과 표시
    st.success(f"당신의 추천 장르는 **{result_bucket}** 🎥")
    st.caption(f"당신에게 잘 맞는 포인트: {RESULT_HINT[result_bucket]}")

    # (선택) 점수 디버그
    with st.expander("내 점수 보기(참고용)"):
        st.write(score_map)

    # 추천 이유 문장 만들기
    evidence_part = ""
    if evidence_answers:
        evidence_part = f"당신은 **{', '.join(evidence_answers[:2])}** 같은 선택을 했고, "
    reason_base = f"{evidence_part}이런 성향은 **{RESULT_HINT[result_bucket]}** 쪽 영화와 잘 맞아요."

    st.write("### 추천 영화 5편")

    for m in picked:
        poster_url = build_poster_url(config, m.get("poster_path"), poster_size_pref)

        # 영화별 이유(조금씩 변화)
        title = m.get("title") or m.get("name") or "이 영화"
        per_movie_reason = (
            f"{reason_base} 그래서 **{title}** 같이 분위기가 비슷한 작품을 추천해요."
        )

        render_movie_card(m, poster_url, per_movie_reason)
        st.divider()
