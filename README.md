# CineMatch

**Personalised Movie Recommendation System using MongoDB**

New users pick their favourite genres, then pick movies they are interested in. CineMatch builds
their personal dashboard: their list, movies picked for them (with the reason why), "because you liked
X" suggestions from people with similar taste, trending movies, and a chart of their taste.

- **Frontend:** React (Vite) + Recharts
- **Backend:** Python FastAPI
- **Database:** MongoDB 7
- **Data:** 1,312 real movies (IMDb ratings, votes, directors, cast, plots; posters from Wikipedia)

> **Rename the project:** change `APP_NAME` and `APP_TAGLINE` in `.env`, then `docker compose up -d --build`.

## Run it (Windows, PowerShell, Docker Desktop open)

```powershell
cd cinematch
docker compose up --build
```
First run takes a few minutes. Then open **http://localhost:8090**.
Or run `.\run.ps1`, which does the same and opens the browser for you.

| What | Address |
|---|---|
| App | http://localhost:8090 |
| API docs | http://localhost:8010/docs |
| MongoDB Compass | `mongodb://localhost:27019` |

- **Demo account:** `demo` / `demo1234` (already has a list and ratings)
- Or click **Create account** to go through the genre and movie picking steps yourself.
- Stop: `Ctrl+C` or `docker compose down`. Delete all data and start fresh: `docker compose down -v`.
- Tests: `docker compose exec backend pytest` (17 tests, separate test database).

Posters load from Wikipedia, so you need internet for pictures. Without internet the app still works
and shows coloured title cards instead.

## Features

| Page | What it shows |
|---|---|
| Sign up / Log in | accounts with hashed passwords, sessions that expire on their own |
| Onboarding | step 1 pick genres, step 2 pick movies (search or popular in your genres) |
| Home (dashboard) | top pick, my list, picked for you, because you liked X, trending, best of your genre, your taste chart |
| Browse | text search (title, actor, director, plot), genre chips, year range, IMDb filter, sorting, pages |
| Movie page | details, add to list, rate 1 to 5 stars, community ratings, "people who liked this also liked", "more like this" |
| My list & ratings | remove from list, change ratings, edit favourite genres |
| Insights | charts made by aggregation pipelines, plus a button that shows the pipelines |

## How recommendations work (no machine learning)

1. **Picked for you (content-based):** each movie gets points: your genres (favourite = 3 points, plus 1
   for each liked movie in that genre), +4 if you liked the director, +2 per actor you liked (max 3), and a
   bonus for high IMDb rating. Movies you have seen are skipped. The reasons are shown on every card.
2. **Because you liked X (collaborative):** find users who rated X 4 or 5 stars, then count which other
   movies those users also liked. Most shared = top.
3. **Trending:** movies with the most ratings in the last 7 days.
4. **More like this:** shared genres, same director, shared actors.

The 60 demo users ("viewer01" to "viewer60") and their ratings are made up so these features have data
on day one. The movies are real.

## Data sources

`backend/data/movies.json` is built by `tools/build_dataset.py` from public copies of:
- *IMDB-Movie-Data.csv* (1,000 popular IMDb movies 2006 to 2016) and *imdb_1000.csv* (top-rated IMDb classics),
- Wikipedia movie data (github.com/prust/wikipedia-movie-data) for posters and summaries (CC BY-SA).

Netflix has no public data download, and IMDb's own download site was blocked from the build machine,
so these public copies of IMDb data were used. For a college (non-commercial) project only.

## Project structure

```
cinematch/
├── docker-compose.yml      mongo + backend + frontend
├── .env                    name, ports, settings
├── run.ps1                 Windows start script
├── tools/build_dataset.py  rebuilds the movie data file
├── backend/
│   ├── data/movies.json    1,312 movies, loaded on first start
│   ├── app/
│   │   ├── main.py         FastAPI app
│   │   ├── db.py           connection, indexes, first-run loading
│   │   ├── seed.py         demo users + ratings
│   │   ├── auth.py         password hashing, sessions
│   │   ├── recommend.py    all recommendation pipelines
│   │   └── routers/        auth, movies, me (list, ratings, dashboard), insights
│   └── tests/              17 pytest tests
├── frontend/src/
│   ├── api.js, auth.jsx    API calls, login state
│   ├── components/ui.jsx   movie card, rows, stars, chips
│   └── pages/              Login, Onboarding, Dashboard, Browse, MovieDetail, Profile, Insights
└── docs/VIVA_GUIDE.md      database design and concepts explained simply
```
