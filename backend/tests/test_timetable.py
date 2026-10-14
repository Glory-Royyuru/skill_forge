from __future__ import annotations

ENTRY = {
    "day_of_week": 0,
    "start_time": "09:00",
    "end_time": "09:50",
    "subject_id": "computer-networks",
    "faculty": "  Dr. K. Rao ",
    "room": "A-204",
}


def test_timetable_crud(make_student):
    client = make_student()
    r = client.post("/api/timetable", json=ENTRY)
    assert r.status_code == 201
    e = r.json()
    assert e["day_name"] == "Monday" and e["subject_name"] == "Computer Networks"
    assert e["faculty"] == "Dr. K. Rao" and e["source"] == "manual"

    later = {
        **ENTRY,
        "day_of_week": 0,
        "start_time": "11:00",
        "end_time": "11:50",
        "subject_id": "machine-learning",
    }
    earlier = {**ENTRY, "day_of_week": 0, "start_time": "08:00", "end_time": "08:50"}
    client.post("/api/timetable", json=later)
    client.post("/api/timetable", json=earlier)
    entries = client.get("/api/timetable").json()["entries"]
    assert [x["start_time"] for x in entries] == ["08:00", "09:00", "11:00"]

    upd = {**ENTRY, "day_of_week": 4, "room": "", "faculty": None}
    r = client.put(f"/api/timetable/{e['id']}", json=upd)
    assert r.status_code == 200 and r.json()["day_name"] == "Friday" and r.json()["room"] is None

    assert client.delete(f"/api/timetable/{e['id']}").status_code == 204
    assert len(client.get("/api/timetable").json()["entries"]) == 2
    assert client.delete(f"/api/timetable/{e['id']}").status_code == 404


def test_timetable_validation(make_student):
    client = make_student()
    assert client.post("/api/timetable", json={**ENTRY, "end_time": "08:00"}).status_code == 400
    assert client.post("/api/timetable", json={**ENTRY, "subject_id": "data-mining"}).status_code == 400
    assert client.post("/api/timetable", json={**ENTRY, "day_of_week": 7}).status_code == 422
    assert client.post("/api/timetable", json={**ENTRY, "start_time": "25:00"}).status_code == 422
    assert client.post("/api/timetable", json={**ENTRY, "room": "x" * 61}).status_code == 422
