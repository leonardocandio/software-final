import pytest
import requests
from datetime import datetime, timedelta
import uuid

BASE_URL = "http://localhost:8000"

def get_unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"

def get_unique_name():
    return f"Test User {uuid.uuid4().hex[:8]}"

@pytest.fixture
def test_user():
    user_response = requests.post(f"{BASE_URL}/users/", params={
        "email": get_unique_email(),
        "name": get_unique_name()
    })
    assert user_response.status_code == 200
    return user_response.json()["user_id"]

@pytest.fixture
def test_concert():
    concert_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
    concert_response = requests.post(f"{BASE_URL}/concerts/", params={
        "name": f"Test Concert {uuid.uuid4().hex[:8]}",
        "date": concert_date,
        "venue": "Test Venue",
        "total_tickets": 100,
        "price": 50.0
    })
    assert concert_response.status_code == 200
    return concert_response.json()["concert_id"]

def test_create_and_reserve_ticket(test_user, test_concert):
    # Reserve a ticket
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": test_concert,
        "user_id": test_user
    })
    assert reserve_response.status_code == 200
    ticket_id = reserve_response.json()["ticket_id"]

    # Verify concert listing shows one less available ticket
    concerts_response = requests.get(f"{BASE_URL}/concerts/")
    assert concerts_response.status_code == 200
    concert = next(c for c in concerts_response.json() if c["id"] == test_concert)
    assert concert["available_tickets"] == 99

def test_purchase_and_use_ticket(test_user, test_concert):
    # Reserve a ticket
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": test_concert,
        "user_id": test_user
    })
    assert reserve_response.status_code == 200
    ticket_id = reserve_response.json()["ticket_id"]

    # Purchase the ticket
    purchase_response = requests.post(f"{BASE_URL}/tickets/purchase/{ticket_id}")
    assert purchase_response.status_code == 200
    assert purchase_response.json()["message"] == "Ticket purchased successfully"

    # Use the ticket
    use_response = requests.post(f"{BASE_URL}/tickets/{ticket_id}/use")
    assert use_response.status_code == 200
    assert use_response.json()["message"] == "Ticket marked as used"

def test_cancel_ticket(test_user, test_concert):
    # Reserve a ticket
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": test_concert,
        "user_id": test_user
    })
    ticket_id = reserve_response.json()["ticket_id"]

    # Get initial available tickets
    concerts_response = requests.get(f"{BASE_URL}/concerts/")
    concert = next(c for c in concerts_response.json() if c["id"] == test_concert)
    initial_tickets = concert["available_tickets"]

    # Cancel the ticket
    cancel_response = requests.post(f"{BASE_URL}/tickets/cancel/{ticket_id}")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["message"] == "Ticket cancelled successfully"

    # Verify available tickets increased
    concerts_response = requests.get(f"{BASE_URL}/concerts/")
    concert = next(c for c in concerts_response.json() if c["id"] == test_concert)
    assert concert["available_tickets"] == initial_tickets + 1

def test_error_cases(test_user, test_concert):
    # Test non-existent concert
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": 99999,
        "user_id": test_user
    })
    assert reserve_response.status_code == 404
    assert "Concert not found" in reserve_response.json()["detail"]

    # Test non-existent user
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": test_concert,
        "user_id": 99999
    })
    assert reserve_response.status_code == 404
    assert "User not found" in reserve_response.json()["detail"]

    # Test purchasing non-existent ticket
    purchase_response = requests.post(f"{BASE_URL}/tickets/purchase/99999")
    assert purchase_response.status_code == 404
    assert "Ticket not found" in purchase_response.json()["detail"]

def test_sold_out_concert():
    # Create a concert with only 1 ticket
    concert_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
    concert_response = requests.post(f"{BASE_URL}/concerts/", params={
        "name": f"Small Concert {uuid.uuid4().hex[:8]}",
        "date": concert_date,
        "venue": "Small Venue",
        "total_tickets": 1,
        "price": 50.0
    })
    concert_id = concert_response.json()["concert_id"]

    # Create two users
    user1_response = requests.post(f"{BASE_URL}/users/", params={
        "email": get_unique_email(),
        "name": get_unique_name()
    })
    user1_id = user1_response.json()["user_id"]

    user2_response = requests.post(f"{BASE_URL}/users/", params={
        "email": get_unique_email(),
        "name": get_unique_name()
    })
    user2_id = user2_response.json()["user_id"]

    # First user reserves the only ticket
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": concert_id,
        "user_id": user1_id
    })
    assert reserve_response.status_code == 200

    # Second user tries to reserve a ticket
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": concert_id,
        "user_id": user2_id
    })
    assert reserve_response.status_code == 400
    assert "No tickets available" in reserve_response.json()["detail"]

def test_ticket_lifecycle():
    # Create user and concert
    user_response = requests.post(f"{BASE_URL}/users/", params={
        "email": get_unique_email(),
        "name": get_unique_name()
    })
    user_id = user_response.json()["user_id"]

    concert_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
    concert_response = requests.post(f"{BASE_URL}/concerts/", params={
        "name": f"Lifecycle Concert {uuid.uuid4().hex[:8]}",
        "date": concert_date,
        "venue": "Test Venue",
        "total_tickets": 10,
        "price": 50.0
    })
    concert_id = concert_response.json()["concert_id"]

    # Reserve ticket
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": concert_id,
        "user_id": user_id
    })
    ticket_id = reserve_response.json()["ticket_id"]

    # Purchase the ticket
    purchase_response = requests.post(f"{BASE_URL}/tickets/purchase/{ticket_id}")
    assert purchase_response.status_code == 200

    # Cancel purchased ticket (this should now work)
    cancel_response = requests.post(f"{BASE_URL}/tickets/cancel/{ticket_id}")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["message"] == "Ticket cancelled successfully"

    # Verify the ticket can be reserved again
    reserve_response = requests.post(f"{BASE_URL}/tickets/reserve/", params={
        "concert_id": concert_id,
        "user_id": user_id
    })
    assert reserve_response.status_code == 200
    ticket_id = reserve_response.json()["ticket_id"]

    # Purchase and use ticket
    purchase_response = requests.post(f"{BASE_URL}/tickets/purchase/{ticket_id}")
    assert purchase_response.status_code == 200

    use_response = requests.post(f"{BASE_URL}/tickets/{ticket_id}/use")
    assert use_response.status_code == 200

    # Try to cancel used ticket (should fail)
    cancel_response = requests.post(f"{BASE_URL}/tickets/cancel/{ticket_id}")
    assert cancel_response.status_code == 400
    assert "Used tickets cannot be cancelled" in cancel_response.json()["detail"]

@pytest.fixture(autouse=True, scope="session")
def cleanup():
    yield  # This runs the tests
    # After all tests complete, we could add cleanup code here if needed
    # For example, we could delete all test users and concerts
    # However, since we're using Docker, the database gets cleaned up
    # when we tear down the containers