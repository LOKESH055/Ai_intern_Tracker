# 🎯 Internship Discovery Assistant

> An AI-powered internship finder that actually does the searching for you — pulls real listings, ranks them based on your profile, checks your resume, and pings your inbox the moment something new shows up.

---

## Why I Built This

Like most students, I was tired of the same routine — opening five tabs, typing the same search on LinkedIn, Indeed, and random job boards, scrolling through postings that had nothing to do with my skills, and still missing out on roles that got buried by the time I checked again.

I wanted one place that could do the boring part for me: search, filter, rank, and *tell me* when something worth applying to shows up — not the other way around.

So I built this. It's powered by IBM's watsonx.ai (running Meta's Llama 3.3 70B model), pulls live job data through RapidAPI's JSearch, and uses IBM Cloudant + Cloud Object Storage to keep everything — your profile, your search history, your saved jobs, your resume — right where you left it.

---

## ✨ What It Actually Does

- 🔍 **Real internship search** — pulls live listings from LinkedIn and Indeed via JSearch, not scraped or fake data
- 🧠 **AI-powered ranking** — scores every listing across factors like company reputation, learning potential, and how beginner-friendly the role is
- 📄 **Resume analysis** — upload your resume, get an ATS compatibility score, and see exactly which skills you're missing for a given role
- 💾 **Job tracking** — save listings you're interested in and track your application status from "saved" to "applied"
- 🔔 **Background monitoring** — set a query once, and the app checks for new postings every few hours in the background, even while you're not using it
- 📧 **Email alerts** — get notified the moment a new matching internship appears, with a direct apply link
- ✍️ **Auto-fill + cover letters** — generates a personalized cover letter and pre-filled application data for any saved job, using your actual profile and resume
- 🖼️ **OCR support** — can read resumes that are scanned images, not just clean text PDFs

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| Interface | Streamlit |
| AI / LLM | IBM watsonx.ai — Llama 3.3 70B |
| Job data | RapidAPI JSearch |
| Database | IBM Cloudant |
| File storage | IBM Cloud Object Storage |
| Background jobs | APScheduler |
| Email | Gmail SMTP |
| Language | Python |

---

## 🧩 How It's Structured

```
internship-discovery-assistant/
├── main.py                     # App entry point
├── app/
│   ├── components/             # Streamlit UI pieces (chat, profile, resume, tracked jobs)
│   ├── services/                # Core logic (watsonx calls, Cloudant, JSearch, monitoring)
│   └── utils/                   # Config and helper functions
├── .env.example                 # Template for environment variables
├── requirements.txt
└── README.md
```

The whole thing is built around a simple loop: **search → rank → save → track → apply**, with the monitoring and email pieces running quietly in the background so you don't have to think about it.

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/internship-discovery-assistant.git
cd internship-discovery-assistant
```

### 2. Set up a virtual environment

```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your environment variables

Copy `.env.example` to `.env` and fill in your own credentials:

```bash
cp .env.example .env
```

You'll need:
- An **IBM Cloud API key** and **watsonx project ID**
- A **RapidAPI key** for JSearch
- **IBM Cloud Object Storage** credentials (for resume uploads)
- **IBM Cloudant** credentials (for storing profiles, searches, and monitors)
- A **Gmail App Password** (for sending alert emails)

### 5. Run it

```bash
streamlit run main.py
```

---

## 💡 Things I Learned Building This

- **Streamlit reruns the entire script on every interaction** — which sounds simple until your background scheduler and session state keep disappearing. The fix was persisting monitor state to Cloudant instead of relying on memory.
- **Free-tier LLM limits are real.** watsonx.ai's Lite plan shares capacity across users, so I built in retry logic with backup models so the app doesn't just fail when the primary model is busy.
- **Prompt tuning matters more than I expected.** Getting the AI to give specific, useful ranking feedback instead of generic filler took a lot of iteration.
- **Never commit your `.env` file.** Learned this the practical way — always double-check `.gitignore` before your first push.

---

## 🔭 What's Next

- Multi-user support (right now it's built around a single profile)
- A dashboard view for application analytics
- Support for more job boards beyond LinkedIn/Indeed
- Smarter monitoring intervals based on how active a search term is

---

## ⚠️ A Note on the Free Tier

This project runs entirely on free-tier services (IBM watsonx.ai Lite, Cloudant Lite, RapidAPI free plan), so:
- Occasional short delays are possible during high-traffic periods on watsonx
- Job data will vary depending on when you search, since it's pulled live

---

## 📜 License

This project is open source under the MIT License — feel free to fork it, learn from it, or build on top of it.

---

## 🙋 About

Built by **Lokesh J** as a personal/academic project exploring applied AI and IBM Cloud services. Feedback and pull requests are welcome!
