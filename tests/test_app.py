from copy import deepcopy

import src.app as app_module
from fastapi.testclient import TestClient


client = TestClient(app_module.app)


def _find_activity_with_open_spot(snapshot: dict) -> str:
    for activity_name, details in snapshot.items():
        if len(details["participants"]) < details["max_participants"]:
            return activity_name
    raise AssertionError("No activity with open spots found in test data")


def _find_activity_with_participant(snapshot: dict) -> tuple[str, str]:
    for activity_name, details in snapshot.items():
        if details["participants"]:
            return activity_name, details["participants"][0]
    raise AssertionError("No activity with participants found in test data")


def _find_email_not_in_activity(snapshot: dict, activity_name: str) -> str:
    participants = set(snapshot[activity_name]["participants"])
    candidate = "new.student@mergington.edu"
    if candidate not in participants:
        return candidate
    return "another.student@mergington.edu"


def _find_activity_with_participant_capacity(snapshot: dict) -> tuple[str, str]:
    for activity_name, details in snapshot.items():
        if details["participants"] and len(details["participants"]) < details["max_participants"]:
            return activity_name, details["participants"][0]
    raise AssertionError("No activity with participants and capacity found in test data")


def _find_activity_with_nonparticipant(snapshot: dict) -> tuple[str, str]:
    for activity_name, details in snapshot.items():
        candidate = "not.registered@mergington.edu"
        if candidate not in details["participants"]:
            return activity_name, candidate
    raise AssertionError("Could not find activity for nonparticipant test")


def _find_available_activity_name(snapshot: dict) -> str:
    return next(iter(snapshot.keys()))


import pytest


@pytest.fixture(autouse=True)
def restore_activities_state():
    original = deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original)


def test_root_redirects_to_static_index():
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_dict():
    response = client.get("/activities")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "Basketball Team" in payload


def test_signup_adds_participant_to_activity():
    snapshot = deepcopy(app_module.activities)
    activity_name = _find_activity_with_open_spot(snapshot)
    email = _find_email_not_in_activity(snapshot, activity_name)

    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    assert response.status_code == 200
    assert email in app_module.activities[activity_name]["participants"]


def test_signup_rejects_duplicate_registration():
    snapshot = deepcopy(app_module.activities)
    activity_name, email = _find_activity_with_participant_capacity(snapshot)

    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_unknown_activity_returns_404():
    response = client.post("/activities/Unknown%20Club/signup", params={"email": "student@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_removes_participant_from_activity():
    snapshot = deepcopy(app_module.activities)
    activity_name, email = _find_activity_with_participant(snapshot)

    response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

    assert response.status_code == 200
    assert email not in app_module.activities[activity_name]["participants"]


def test_unregister_nonparticipant_returns_404():
    snapshot = deepcopy(app_module.activities)
    activity_name, email = _find_activity_with_nonparticipant(snapshot)

    response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not signed up for this activity"


def test_unregister_unknown_activity_returns_404():
    snapshot = deepcopy(app_module.activities)
    activity_name = _find_available_activity_name(snapshot)
    sample_email = app_module.activities[activity_name]["participants"][0]

    response = client.delete("/activities/Unknown%20Club/signup", params={"email": sample_email})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"