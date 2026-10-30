# Viva guide: CineMatch

Simple explanations of the database design, the MongoDB features used, and likely questions.

## 1. The project in 30 seconds

"CineMatch is a movie recommendation app. A new user picks favourite genres and a few movies they like.
MongoDB stores 1,312 real IMDb movies, the users, and every rating. Recommendations are built with
MongoDB aggregation pipelines: content-based (match your genres, directors, actors) and collaborative
(people who liked the same movie as you also liked these). Every suggestion shows why it was picked."

**Demo order (5 minutes):**
1. Create a new account -> pick 3 genres -> pick 5 movies -> dashboard appears.
2. Point at the reasons under "Picked for you".
3. Log in as `demo` / `demo1234`: show "Because you liked Inception" (collaborative).
4. Open The Dark Knight: community rating bars, "People who liked this also liked", rate it, add to list.
5. Browse: search "Nolan" (text index), click Horror + IMDb 7.5+ (multikey index + range).
6. Insights: charts, then "Show the MongoDB pipelines".
7. Optional: MongoDB Compass at `mongodb://localhost:27019` to show the collections and indexes.

## 2. Collections (the schema)

### movies (1,312 documents, read-mostly)
```json
{
  "_id": "inception-2010",                       // readable string id: title + year
  "title": "Inception", "year": 2010,
  "genres": ["Action", "Adventure", "Sci-Fi"],   // array
  "director": "Christopher Nolan",
  "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Ellen Page", "Ken Watanabe"],
  "runtime": 148, "imdb_rating": 8.8, "imdb_votes": 1583625,
  "metascore": 74, "revenue_musd": 292.57,       // missing (null) for some classics
  "certificate": "PG-13",                        // only some movies have this field
  "description": "A thief, who steals corporate secrets ...",
  "poster": "https://upload.wikimedia.org/...", "wiki": "https://en.wikipedia.org/wiki/Inception"
}
```

### users
```json
{
  "_id": ObjectId("..."),
  "username": "poornesh",                         // unique index
  "display_name": "Poornesh",
  "password": { "salt": "9f2c...", "hash": "64 hex chars" },   // never the plain password
  "favourite_genres": ["Sci-Fi", "Thriller"],
  "my_list": [                                     // EMBEDDED array
    { "movie_id": "inception-2010", "added_at": ISODate("...") }
  ],
  "onboarded": true, "created_at": ISODate("...")
}
```

### ratings (one document per user per movie)
```json
{ "_id": ObjectId, "user_id": ObjectId("..."), "movie_id": "inception-2010", "stars": 5, "created_at": ISODate }
```

### sessions (logins)
```json
{ "_id": "random-token", "user_id": ObjectId, "created_at": ISODate, "expires_at": ISODate }
```

## 3. Key design decisions (most likely viva questions)

**Why is "my list" embedded in the user, but ratings are a separate collection?**
- My list is small, belongs only to one user, and is always shown with that user. One read of the user
  document gives the whole list. Adding and removing uses `$push` and `$pull`.
- Ratings are used *across users*: "everyone who liked Inception" needs to search all ratings by movie.
  If ratings were inside each user document, that query would have to open every user. As their own
  collection, a simple index on `movie_id` answers it. Ratings also grow without limit (16 MB document cap).
- Rule of thumb: *embed what is small and read together; reference what grows or is queried on its own.*

**Why does `movies` use a string `_id` like `inception-2010`?** `_id` can be any unique value. A readable
id is stable, works nicely in URLs (`/movie/inception-2010`) and makes the data easy to read in Compass.

**Why is the schema flexible here?** Some movies have `metascore`, `revenue_musd`, `imdb_votes` or
`certificate`, and the older classics do not. In MongoDB those fields are simply left out or null;
in SQL you would need nullable columns for everything. Genres and cast are arrays, which in SQL would
need two extra link tables (movie_genres, movie_cast).

**Why not store the average rating inside the movie?** It changes with every new rating. We compute it
on demand with an aggregation (`$group` + `$avg`). With millions of ratings you would cache it in the
movie document and update it with `$inc`; that is a trade-off you can mention.

## 4. Indexes

| Collection | Index | Type | Why |
|---|---|---|---|
| movies | `title, cast, director, description` (weights 10/4/4/1) | **text** | search box; title matches count most |
| movies | `{genres: 1, imdb_rating: -1}` | **multikey** compound | genre filter + sort by rating |
| movies | `{imdb_rating: -1, imdb_votes: -1}` | compound | "highest rated" / "most popular" |
| movies | `{year: -1}`, `{director: 1}` | single | year filter, same-director lookups |
| users | `{username: 1}` | **unique** | no two users with the same name (the 409 error comes from this) |
| ratings | `{user_id: 1, movie_id: 1}` | **unique** compound | one rating per user per movie; fast "my ratings" |
| ratings | `{movie_id: 1, stars: -1}` | compound | "who liked this movie" for collaborative filtering |
| ratings | `{created_at: -1}` | single | trending in the last 7 days |
| sessions | `{expires_at: 1}`, `expireAfterSeconds: 0` | **TTL** | MongoDB deletes expired logins by itself |

- **Multikey:** `genres` is an array, so the index has one entry per genre per movie. `{genres: "Horror"}`
  uses it directly.
- **Text index:** splits text into words, drops common words ("the", "a"), and matches word stems
  ("running" finds "run"). Results are ordered by `$meta: "textScore"`.
- **TTL index:** `expireAfterSeconds: 0` on `expires_at` means "delete each document at the time stored in
  `expires_at`". Logging out deletes the session immediately.
- **Unique compound index + upsert:** rating a movie twice updates the same document instead of adding a
  second one (`update_one(..., upsert=True)`).

Check an index in the shell:
```js
db.movies.find({ genres: "Horror" }).sort({ imdb_rating: -1 }).explain("executionStats").queryPlanner.winningPlan
```

## 5. Aggregation pipelines (where the recommendations come from)

All in `backend/app/recommend.py` and `backend/app/routers/insights.py`.

### Collaborative: "People who liked X also liked" (a self-join)
```js
db.ratings.aggregate([
  { $match: { movie_id: "inception-2010", stars: { $gte: 4 } } },          // fans of Inception
  { $lookup: { from: "ratings", localField: "user_id", foreignField: "user_id",
               pipeline: [ { $match: { stars: { $gte: 4 } } } ], as: "their_likes" } },  // what else each fan liked
  { $unwind: "$their_likes" },
  { $match: { "their_likes.movie_id": { $ne: "inception-2010" } } },
  { $group: { _id: "$their_likes.movie_id", fans: { $sum: 1 }, avg_stars: { $avg: "$their_likes.stars" } } },
  { $sort: { fans: -1, avg_stars: -1 } },
  { $limit: 10 },
  { $lookup: { from: "movies", localField: "_id", foreignField: "_id", as: "movie" } }
])
```
In words: find everyone who liked Inception, list everything else they liked, and count how many of them
liked each movie.

### Content-based: "Picked for you"
`$match` (my genres, not seen) -> `$addFields` with `$setIntersection` (shared genres, shared actors),
`$in` (same director) and a computed `score` -> `$sort` -> `$limit`. The reasons on each card come from
those computed fields.

### Others
| Feature | Stages |
|---|---|
| Trending | `$match` last 7 days -> `$group` by movie (count, `$avg`) -> `$sort` -> `$lookup` movies |
| Your taste | `$match` my ratings -> `$lookup` movies -> `$unwind` genres -> `$group` by genre |
| Movies per genre | `$unwind` genres -> `$group` |
| IMDb rating spread | `$bucket` with boundaries 0, 5, 6, 7, 8, 9, 10 |
| Movies per decade | `$floor(year / 10) * 10` -> `$group` |
| Best directors | `$group` by director -> `$match` 3+ movies -> `$sort` by `$avg` rating |
| Ratings per day | `$dateTrunc` to day -> `$group` |
| Community rating bars | `$match` movie -> `$group` by stars |

## 6. Updates worth mentioning

| Action | MongoDB operation |
|---|---|
| Add to my list (no duplicates) | `update_one({_id, "my_list.movie_id": {$ne: id}}, {$push: {my_list: {$each: [item], $position: 0}}})` |
| Remove from list | `$pull: {my_list: {movie_id: id}}` |
| Rate / change rating | `update_one({user_id, movie_id}, {$set: {stars}}, upsert=True)` |
| Finish onboarding | `$set` genres + `$push` many movies with `$each` |
| Register | `insert_one`; duplicate username -> `DuplicateKeyError` -> HTTP 409 |

## 7. Likely questions

**Why MongoDB and not MySQL?** Movies have arrays (genres, cast) and optional fields; users have an
embedded list; the recommendation logic is aggregation-heavy. In MySQL you would need 6+ tables
(movies, genres, movie_genres, cast, movie_cast, users, user_list, ratings) and many joins.

**Is this machine learning?** No. It is rule-based scoring plus counting (item-to-item collaborative
filtering). It is explainable, needs no training, and gives the same result every time.

**What is the "cold start" problem and how do you handle it?** A new user has no ratings, so
collaborative filtering has nothing to work with. That is exactly why onboarding asks for genres and
movies first: content-based recommendations work immediately.

**How are passwords stored?** PBKDF2-SHA256 with a random salt and 120,000 iterations. Only the salt and
hash are stored.

**What happens when a session expires?** The TTL index deletes it, the next request gets HTTP 401, and the
app shows the login page.

**How would it scale?** Shard `ratings` by `user_id` or `movie_id`; cache average ratings and "also liked"
lists in the movie documents and refresh them periodically; use read replicas for browsing.

**Where does the data come from?** Public copies of IMDb datasets (ratings, votes, directors, cast) plus
Wikipedia (posters, summaries). Netflix has no public data download. The 60 demo users are synthetic so the
collaborative features have data from the start.

**How did you test it?** 17 pytest tests against a real MongoDB: sign-up/login/logout, duplicate usernames,
password hashing, TTL index, text search, filters, onboarding, no duplicates in the list, rating upsert,
recommendations skip watched movies, collaborative results. Run `docker compose exec backend pytest`.

## 8. Shell commands for the demo

```powershell
docker compose exec mongo mongosh cinematch
```
```js
db.movies.countDocuments()
db.movies.find({ genres: "Sci-Fi" }, { title: 1, imdb_rating: 1 }).sort({ imdb_rating: -1 }).limit(5)
db.movies.find({ $text: { $search: "Nolan" } }, { title: 1 })
db.users.findOne({ username: "demo" }, { password: 0 })
db.ratings.find({ movie_id: "inception-2010" }).count()
db.movies.getIndexes()
db.sessions.getIndexes()        // see expireAfterSeconds
```
