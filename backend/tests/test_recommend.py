def test_onboarding_flow(client, new_user):
    headers, _ = new_user
    picks = ["inception-2010", "interstellar-2014", "the-martian-2015"]
    r = client.post("/api/me/onboarding", headers=headers, json={"genres": ["Sci-Fi", "Adventure"], "movie_ids": picks})
    assert r.status_code == 200 and r.json()["onboarded"] is True
    assert [m["id"] for m in client.get("/api/me/list", headers=headers).json()] == picks
    bad = client.post("/api/me/onboarding", headers=headers, json={"genres": ["Cooking"]})
    assert bad.status_code == 400


def test_dashboard_recommends_unseen_matching_movies(client, new_user):
    headers, _ = new_user
    picks = ["inception-2010", "interstellar-2014"]
    client.post("/api/me/onboarding", headers=headers, json={"genres": ["Sci-Fi"], "movie_ids": picks})
    d = client.get("/api/me/dashboard", headers=headers).json()
    recs = d["picked_for_you"]
    assert recs and all(m["id"] not in picks for m in recs)
    assert all(m["reasons"] for m in recs)
    assert any("Sci-Fi" in m["genres"] for m in recs)
    assert d["trending"]


def test_my_list_has_no_duplicates(client, new_user):
    headers, _ = new_user
    for _ in range(2):
        assert client.post("/api/me/list", headers=headers, json={"movie_id": "up-2009"}).status_code == 201
    assert [m["id"] for m in client.get("/api/me/list", headers=headers).json()] == ["up-2009"]
    client.delete("/api/me/list/up-2009", headers=headers)
    assert client.get("/api/me/list", headers=headers).json() == []


def test_rating_upsert(client, db, new_user):
    headers, name = new_user
    client.put("/api/me/ratings/up-2009", headers=headers, json={"stars": 3})
    client.put("/api/me/ratings/up-2009", headers=headers, json={"stars": 5})
    uid = db.users.find_one({"username": name})["_id"]
    assert db.ratings.count_documents({"user_id": uid}) == 1
    assert db.ratings.find_one({"user_id": uid})["stars"] == 5
    assert client.put("/api/me/ratings/up-2009", headers=headers, json={"stars": 9}).status_code == 422


def test_rated_movies_drop_out_of_recommendations(client, new_user):
    headers, _ = new_user
    client.post("/api/me/onboarding", headers=headers, json={"genres": ["Animation"], "movie_ids": []})
    first = client.get("/api/me/dashboard", headers=headers).json()["picked_for_you"][0]["id"]
    client.put(f"/api/me/ratings/{first}", headers=headers, json={"stars": 2})
    again = [m["id"] for m in client.get("/api/me/dashboard", headers=headers).json()["picked_for_you"]]
    assert first not in again


def test_because_you_liked_uses_other_users(client, demo):
    b = client.get("/api/me/dashboard", headers=demo).json()["because_you_liked"]
    assert b and b["seed"]["title"] and len(b["items"]) >= 3
    assert "people who liked this also liked it" in b["items"][0]["reasons"][0]
