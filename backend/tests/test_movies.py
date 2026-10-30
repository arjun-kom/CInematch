def test_movies_loaded_with_real_data(db):
    assert db.movies.count_documents({}) > 1000
    m = db.movies.find_one({"_id": "inception-2010"})
    assert m["director"] == "Christopher Nolan" and "Sci-Fi" in m["genres"]


def test_genres_list(client):
    genres = {g["genre"] for g in client.get("/api/genres").json()}
    assert {"Drama", "Sci-Fi", "Comedy"} <= genres


def test_text_search_finds_by_director(client):
    titles = [m["title"] for m in client.get("/api/movies", params={"q": "Nolan"}).json()["items"]]
    assert "Inception" in titles


def test_filters(client):
    r = client.get("/api/movies", params=[("genre", "Horror"), ("min_rating", 7.5), ("year_from", 2000)]).json()
    assert r["total"] > 0
    assert all("Horror" in m["genres"] and m["imdb_rating"] >= 7.5 and m["year"] >= 2000 for m in r["items"])


def test_movie_detail(client, demo):
    d = client.get("/api/movies/the-dark-knight-2008", headers=demo).json()
    assert d["movie"]["title"] == "The Dark Knight"
    assert d["my_stars"] == 5 and d["in_my_list"] is True
    assert "Batman Begins" in [m["title"] for m in d["similar"]]
    assert d["fans_also_liked"] and all(m["fans"] >= 2 for m in d["fans_also_liked"])
    assert client.get("/api/movies/nope-1999", headers=demo).status_code == 404


def test_insights(client):
    d = client.get("/api/insights").json()
    assert d["counts"]["movies"] > 1000 and d["genres"] and d["top_directors"]
