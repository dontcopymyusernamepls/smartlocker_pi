        # Include message if parcel has not been collected after threshold
        if locker_empty == "No" and placed_at_str:
            placed_time = datetime.fromisoformat(placed_at_str)
            duration = datetime.now() - placed_time

            # Change this to timedelta(days=3) for real deployment
            threshold = timedelta(seconds=30)

            if duration > threshold:
                response["message"] = "Parcel not collected for 3 days"

        return jsonify(response)
