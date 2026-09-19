import pytest
import uuid

@pytest.mark.asyncio
async def test_store_booking_and_favourites_flow(client):
    unique_email = f"store_tester_{uuid.uuid4().hex[:8]}@example.com"
    
    # 1. Signup & Login
    signup_payload = {
        "firstName": "Store",
        "lastName": "Tester",
        "email": unique_email,
        "password": "Password123!",
        "userType": "guest"
    }
    signup_res = await client.post("/api/signup", json=signup_payload)
    assert signup_res.status_code in [200, 201]

    login_res = await client.post("/api/login", json={"email": unique_email, "password": "Password123!"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get homes to pick a home
    homes_res = await client.get("/api/homes")
    assert homes_res.status_code == 200
    homes = homes_res.json()["registeredHomes"]
    if len(homes) == 0:
        pytest.skip("No homes in database to test bookings and favourites")

    target_home = homes[0]
    target_home_id = str(target_home.get("_id") or target_home.get("id"))

    # 3. Add to favourite
    fav_add_res = await client.post("/api/favourites", json={"id": target_home_id}, headers=headers)
    assert fav_add_res.status_code == 200
    fav_add_data = fav_add_res.json()
    assert fav_add_data["success"] is True
    assert "favourites" in fav_add_data
    assert target_home_id in fav_add_data["favourites"]

    # 4. Remove from favourite
    fav_rm_res = await client.post(f"/api/favourites/delete/{target_home_id}", headers=headers)
    assert fav_rm_res.status_code == 200
    fav_rm_data = fav_rm_res.json()
    assert fav_rm_data["success"] is True
    assert target_home_id not in fav_rm_data["favourites"]

    # 5. Create booking with omitted totalPrice (server auto-calculates diffDays * price)
    # Use randomized future dates to avoid conflicting with previous test runs
    import random
    start_year = random.randint(2030, 2040)
    check_in = f"{start_year}-05-10"
    check_out = f"{start_year}-05-13"

    booking_payload = {
        "homeId": target_home_id,
        "checkIn": check_in,
        "checkOut": check_out,
        "guests": 2
    }
    booking_res = await client.post("/api/bookings", json=booking_payload, headers=headers)
    assert booking_res.status_code == 200
    booking_data = booking_res.json()
    assert booking_data["success"] is True
    assert "booking" in booking_data
    created_booking_id = booking_data["booking"]["_id"]
    assert booking_data["booking"]["totalPrice"] == float(target_home["price"] * 3)

    # 6. Verify duplicate/overlapping booking on same dates returns 409 Conflict
    overlap_res = await client.post("/api/bookings", json=booking_payload, headers=headers)
    assert overlap_res.status_code == 409

    # 7. Verify date validation error (checkOut <= checkIn returns 422)
    bad_booking_payload = {
        "homeId": target_home_id,
        "checkIn": f"{start_year}-06-15",
        "checkOut": f"{start_year}-06-10",
        "guests": 1
    }
    bad_res = await client.post("/api/bookings", json=bad_booking_payload, headers=headers)
    assert bad_res.status_code == 422

    # Cleanup test booking
    await client.delete(f"/api/bookings/{created_booking_id}", headers=headers)
