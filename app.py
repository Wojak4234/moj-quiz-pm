nimport streamlit as st
import json
import random
import re
import os

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Quiz - Zarządzanie Projektami", page_icon="🎓", layout="centered")


# --- FUNKCJE BAZOWE ---
@st.cache_data
def load_questions(path="pytania.txt"):
    questions = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_q = None
        current_answers = []
        correct_idx = -1

        for line in lines:
            line_s = line.strip()
            line_s = re.sub(r'^[•\-\*]\s*', '', line_s)

            if not line_s or line_s.startswith("Lecimy") or line_s.startswith("Wszystkie") or line_s.startswith(
                    "Oto") or line_s.startswith("Zauważ") or line_s.startswith("Przedostatnia"):
                continue

            if re.match(r'^\d+\.', line_s):
                if current_q and current_answers:
                    questions.append({'q': current_q, 'answers': current_answers, 'correct': max(0, correct_idx)})
                current_q = line_s
                current_answers = []
                correct_idx = -1

            elif '[+]' in line_s or '[-]' in line_s:
                if '[+]' in line_s:
                    correct_idx = len(current_answers)
                ans_text = line_s.replace('[+]', '').replace('[-]', '').strip()
                current_answers.append(ans_text)

            elif current_q and not current_answers:
                current_q += " " + line_s
            elif current_q and current_answers:
                current_answers[-1] += " " + line_s

        if current_q and current_answers:
            questions.append({'q': current_q, 'answers': current_answers, 'correct': max(0, correct_idx)})

    except FileNotFoundError:
        st.error(f"Nie znaleziono pliku '{path}'. Upewnij się, że jest w tym samym folderze co skrypt.")

    return questions


def load_progress(file_path="postepy.json"):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_progress(progress, file_path="postepy.json"):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=4)


# --- INICJALIZACJA STANU APLIKACJI (SESSION STATE) ---
if 'questions' not in st.session_state:
    st.session_state.questions = load_questions()

if 'progress' not in st.session_state:
    progress = load_progress()
    for q in st.session_state.questions:
        if q['q'] not in progress:
            progress[q['q']] = {"streak": 0, "mastered": False, "seen": 0, "correct": 0}
    st.session_state.progress = progress
    save_progress(progress)

if 'round_active' not in st.session_state:
    st.session_state.round_active = False
    st.session_state.round_q_idx = 0
    st.session_state.round_score = 0
    st.session_state.current_round_qs = []
    st.session_state.answered = False
    st.session_state.current_options = []
    st.session_state.correct_option_idx = 0
    st.session_state.selected_option_idx = -1


# --- LOGIKA APLIKACJI ---
def start_round():
    unmastered = [q for q in st.session_state.questions if not st.session_state.progress[q['q']]['mastered']]
    if not unmastered:
        st.success("🎉 Gratulacje! Opanowałeś wszystkie pytania z bazy (3x z rzędu poprawnie). Jesteś gotowy!")
        return

    random.shuffle(unmastered)
    st.session_state.current_round_qs = unmastered[:20]
    st.session_state.round_q_idx = 0
    st.session_state.round_score = 0
    st.session_state.round_active = True
    st.session_state.answered = False
    prepare_question()


def prepare_question():
    if st.session_state.round_q_idx < len(st.session_state.current_round_qs):
        q_data = st.session_state.current_round_qs[st.session_state.round_q_idx]
        opts = list(enumerate(q_data['answers']))
        random.shuffle(opts)
        st.session_state.current_options = [opt[1] for opt in opts]

        # Znajdź nowy indeks poprawnej odpowiedzi po przetasowaniu
        for new_idx, (old_idx, text) in enumerate(opts):
            if old_idx == q_data['correct']:
                st.session_state.correct_option_idx = new_idx
    else:
        st.session_state.round_active = False


def handle_answer(selected_idx):
    st.session_state.answered = True
    st.session_state.selected_option_idx = selected_idx

    q_data = st.session_state.current_round_qs[st.session_state.round_q_idx]
    q_text = q_data['q']

    st.session_state.progress[q_text]['seen'] += 1

    if selected_idx == st.session_state.correct_option_idx:
        st.session_state.round_score += 1
        st.session_state.progress[q_text]['correct'] += 1
        st.session_state.progress[q_text]['streak'] += 1
        if st.session_state.progress[q_text]['streak'] >= 3:
            st.session_state.progress[q_text]['mastered'] = True
    else:
        st.session_state.progress[q_text]['streak'] = 0

    save_progress(st.session_state.progress)


def next_question():
    st.session_state.answered = False
    st.session_state.round_q_idx += 1
    prepare_question()


def flag_question():
    q_data = st.session_state.current_round_qs[st.session_state.round_q_idx]
    correct_text = q_data['answers'][q_data['correct']]
    with open("trudne_pytania.txt", "a", encoding="utf-8") as f:
        f.write(f"{q_data['q']}\nPOPRAWNA ODP: {correct_text}\n\n")
    st.toast('🚩 Oflagowano i zapisano do pliku!')


# --- INTERFEJS UŻYTKOWNIKA (UI) ---
st.title("🎓 PM Quiz - Inteligentne Powtórki")

# Statystyki w pasku bocznym (Sidebar)
# Statystyki i wybór w pasku bocznym (Sidebar)
with st.sidebar:
    st.header("⚙️ Wybierz przedmiot")
    quiz_choice = st.selectbox("Baza pytań:", ["Zarządzanie Projektami", "Teledetekcja"])
    
    # Ustalenie pliku na podstawie wyboru
    file_to_load = "pytania.txt" if quiz_choice == "Zarządzanie Projektami" else "teledetekcja.txt"
    
    # Przeładowanie pytań, jeśli zmieniono przedmiot
    if 'current_subject' not in st.session_state or st.session_state.current_subject != quiz_choice:
        st.session_state.current_subject = quiz_choice
        st.session_state.questions = load_questions(file_to_load)
        st.session_state.round_active = False # Zatrzymanie rundy przy zmianie przedmiotu
        
        # Inicjalizacja postępów dla nowego pliku
        progress = load_progress()
        for q in st.session_state.questions:
            if q['q'] not in progress:
                progress[q['q']] = {"streak": 0, "mastered": False, "seen": 0, "correct": 0}
        st.session_state.progress = progress
        save_progress(progress)

    st.divider()
    st.header("📊 Twoje Statystyki")
    total = len(st.session_state.questions)
    if total > 0:
        mastered = sum(1 for q in st.session_state.questions if st.session_state.progress[q['q']]['mastered'])
        left = total - mastered
        total_seen = sum(st.session_state.progress[q['q']]['seen'] for q in st.session_state.questions)
        total_corr = sum(st.session_state.progress[q['q']]['correct'] for q in st.session_state.questions)
        acc = round((total_corr / total_seen * 100), 1) if total_seen > 0 else 0.0
        
        st.metric("Opanowane (3x z rzędu)", f"{mastered} / {total}")
        st.progress(mastered / total)
        st.metric("Pozostało do nauki", left)
        st.metric("Skuteczność", f"{acc}%")
    else:
        st.write("Brak załadowanych pytań. Sprawdź pliki TXT.")

# Widok główny
if not st.session_state.round_active:
    st.write(
        "Witaj w inteligentnym systemie nauki! Program zapamiętuje Twoje postępy. Pytanie uważa się za opanowane, gdy odpowiesz na nie bezbłędnie 3 razy z rzędu.")
    if st.button("🚀 Rozpocznij rundę (Max 20 pytań)", use_container_width=True):
        start_round()
        st.rerun()

else:
    q_total = len(st.session_state.current_round_qs)
    q_current = st.session_state.round_q_idx + 1

    st.caption(f"Runda: pytanie {q_current} z {q_total} | Wynik: {st.session_state.round_score}")
    st.progress(q_current / q_total)

    q_data = st.session_state.current_round_qs[st.session_state.round_q_idx]
    st.subheader(q_data['q'])

    if not st.session_state.answered:
        # Wyświetlanie przycisków wyboru
        for i, opt_text in enumerate(st.session_state.current_options):
            if st.button(opt_text, key=f"btn_{i}", use_container_width=True):
                handle_answer(i)
                st.rerun()

        st.divider()
        st.button("🚩 Oflaguj jako trudne (zapisz do TXT)", on_click=flag_question)

    else:
        # Wyświetlanie wyników po odpowiedzi
        for i, opt_text in enumerate(st.session_state.current_options):
            if i == st.session_state.correct_option_idx:
                st.success(f"✅ {opt_text}")
            elif i == st.session_state.selected_option_idx:
                st.error(f"❌ {opt_text}")
            else:
                st.info(opt_text)

        if st.session_state.selected_option_idx == st.session_state.correct_option_idx:
            st.write("Dobrze! Licznik dobrej passy dla tego pytania wzrósł.")
        else:
            st.write("Pudło. Passa dla tego pytania wyzerowana.")

        st.button("⏭️ Następne pytanie", on_click=next_question, type="primary", use_container_width=True)
